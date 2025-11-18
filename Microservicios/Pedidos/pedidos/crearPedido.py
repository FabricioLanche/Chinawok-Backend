import json
import boto3
import os
import uuid
from datetime import datetime, timedelta
from jsonschema import validate, ValidationError
from botocore.exceptions import ClientError
from decimal import Decimal

# Cliente DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_PEDIDOS', 'ChinaWok-Pedidos')
table = dynamodb.Table(table_name)

# Tabla de productos
productos_table_name = os.environ.get('TABLE_PRODUCTOS', 'ChinaWok-Productos')
productos_table = dynamodb.Table(productos_table_name)

# Tabla de combos
combos_table_name = os.environ.get('TABLE_COMBOS', 'ChinaWok-Combos')
combos_table = dynamodb.Table(combos_table_name)

# Tabla de locales
locales_table_name = os.environ.get('TABLE_LOCALES', 'ChinaWok-Locales')
locales_table = dynamodb.Table(locales_table_name)

# Tabla de usuarios
usuarios_table_name = os.environ.get('TABLE_USUARIOS', 'ChinaWok-Usuarios')
usuarios_table = dynamodb.Table(usuarios_table_name)

# Agregar cliente de EventBridge
eventbridge = boto3.client('events')
EVENT_BUS_NAME = os.environ.get('EVENT_BUS_NAME', 'chinawok-pedidos-events')

# Schema de validación (sin estado ni historial_estados en el request)
PEDIDO_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Pedidos",
    "type": "object",
    "properties": {
        "local_id": {"type": "string"},
        "usuario_correo": {"type": "string", "format": "email"},
        "productos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string"},
                    "cantidad": {"type": "integer", "minimum": 1}
                },
                "required": ["nombre", "cantidad"],
                "additionalProperties": False
            },
            "minItems": 1
        },
        "combos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "combo_id": {"type": "string"},
                    "cantidad": {"type": "integer", "minimum": 1}
                },
                "required": ["combo_id", "cantidad"],
                "additionalProperties": False
            },
            "minItems": 1
        },
        "costo": {"type": "number", "minimum": 0},
        "direccion": {"type": "string"},
        "fecha_entrega_aproximada": {
            "type": ["string", "null"],
            "format": "date-time"
        }
    },
    "required": [
        "local_id",
        "usuario_correo",
        "direccion",
        "costo"
    ],
    "anyOf": [
        {"required": ["productos"]},
        {"required": ["combos"]}
    ],
    "additionalProperties": False
}


def verificar_local_existe(local_id):
    """
    Verifica que el local exista
    Returns: (bool, str) - (éxito, mensaje de error)
    """
    try:
        response = locales_table.get_item(
            Key={'local_id': local_id}
        )
        
        if 'Item' not in response:
            return False, f"El local '{local_id}' no existe"
        
        return True, None
        
    except ClientError as e:
        return False, f"Error al verificar local: {str(e)}"


def verificar_usuario_info_bancaria(usuario_correo):
    """
    Verifica que el usuario exista y tenga información bancaria completa
    Returns: (bool, str) - (éxito, mensaje de error)
    """
    try:
        response = usuarios_table.get_item(
            Key={'correo': usuario_correo}
        )
        
        if 'Item' not in response:
            return False, f"El usuario '{usuario_correo}' no existe"
        
        usuario = response['Item']
        info_bancaria = usuario.get('informacion_bancaria')
        
        if not info_bancaria:
            return False, f"El usuario '{usuario_correo}' no tiene información bancaria registrada"
        
        # Verificar que todos los campos requeridos estén presentes y no sean None/vacíos
        campos_requeridos = ['numero_tarjeta', 'cvv', 'fecha_vencimiento', 'direccion_delivery']
        for campo in campos_requeridos:
            if not info_bancaria.get(campo):
                return False, f"El usuario '{usuario_correo}' tiene información bancaria incompleta (falta: {campo})"
        
        return True, None
        
    except ClientError as e:
        return False, f"Error al verificar usuario: {str(e)}"


def verificar_productos_stock(local_id, productos):
    """
    Verifica que los productos existan en el local y tengan stock suficiente
    Returns: (bool, str) - (éxito, mensaje de error)
    """
    for producto in productos:
        nombre = producto['nombre']
        cantidad = producto['cantidad']
        
        try:
            # Obtener producto de DynamoDB
            response = productos_table.get_item(
                Key={
                    'local_id': local_id,
                    'nombre': nombre
                }
            )
            
            if 'Item' not in response:
                return False, f"El producto '{nombre}' no existe en el local {local_id}"
            
            producto_db = response['Item']
            stock_disponible = producto_db.get('stock', 0)
            
            if stock_disponible < cantidad:
                return False, f"Stock insuficiente para '{nombre}'. Disponible: {stock_disponible}, Solicitado: {cantidad}"
                
        except ClientError as e:
            return False, f"Error al verificar producto '{nombre}': {str(e)}"
    
    return True, None


def verificar_combos(local_id, combos):
    """
    Verifica que los combos existan
    Returns: (bool, str) - (éxito, mensaje de error)
    """
    for combo in combos:
        combo_id = combo['combo_id']
        
        try:
            # Obtener combo de DynamoDB
            response = combos_table.get_item(
                Key={
                    'local_id': local_id,
                    'combo_id': combo_id
                }
            )
            
            if 'Item' not in response:
                return False, f"El combo '{combo_id}' no existe en el local {local_id}"
                
        except ClientError as e:
            return False, f"Error al verificar combo '{combo_id}': {str(e)}"
    
    return True, None


def convertir_floats_a_decimal(obj):
    """
    Convierte recursivamente todos los floats a Decimal para DynamoDB
    """
    if isinstance(obj, list):
        return [convertir_floats_a_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convertir_floats_a_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj


def convertir_decimal_a_float(obj):
    """
    Convierte recursivamente todos los Decimal a float para serialización JSON
    """
    if isinstance(obj, list):
        return [convertir_decimal_a_float(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convertir_decimal_a_float(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj


def handler(event, context):
    """
    Lambda handler para crear un pedido en DynamoDB
    """
    try:
        # Parsear el body del evento
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        # Validar schema (sin pedido_id, estado ni historial_estados)
        validate(instance=body, schema=PEDIDO_SCHEMA)
        
        # Generar pedido_id automáticamente
        body['pedido_id'] = str(uuid.uuid4())
        
        # Inicializar timestamps y estado automáticamente
        hora_inicio = datetime.utcnow()
        # Estimamos 2-3 segundos para procesamiento (validaciones + EventBridge)
        hora_fin = hora_inicio + timedelta(seconds=2.5)
        
        body['estado'] = 'procesando'
        body['historial_estados'] = [
            {
                'estado': 'procesando',
                'hora_inicio': hora_inicio.isoformat() + 'Z',
                'hora_fin': hora_fin.isoformat() + 'Z',
                'activo': True,
                'empleado': None
            }
        ]
        
        # Validar que tenga productos o combos
        if 'productos' not in body and 'combos' not in body:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Debe especificar al menos productos o combos'
                })
            }
        
        local_id = body.get('local_id')
        usuario_correo = body.get('usuario_correo')
        
        # Verificar que el local existe
        exito, error_msg = verificar_local_existe(local_id)
        if not exito:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Error de validación de local',
                    'message': error_msg
                })
            }
        
        # Verificar que el usuario existe y tiene información bancaria
        exito, error_msg = verificar_usuario_info_bancaria(usuario_correo)
        if not exito:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Error de validación de usuario',
                    'message': error_msg
                })
            }
        
        # Verificar productos si existen
        if 'productos' in body and body['productos']:
            exito, error_msg = verificar_productos_stock(local_id, body['productos'])
            if not exito:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Error de validación de productos',
                        'message': error_msg
                    })
                }
        
        # Verificar combos si existen
        if 'combos' in body and body['combos']:
            exito, error_msg = verificar_combos(local_id, body['combos'])
            if not exito:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Error de validación de combos',
                        'message': error_msg
                    })
                }
        
        # Convertir floats a Decimal para DynamoDB
        body = convertir_floats_a_decimal(body)
        
        # Insertar en DynamoDB
        table.put_item(Item=body)
        
        # Después de crear exitosamente el pedido en DynamoDB
        # Publicar evento a EventBridge
        try:
            # Convertir Decimal a float para serialización JSON
            body_para_evento = convertir_decimal_a_float(body)
            
            event_response = eventbridge.put_events(
                Entries=[
                    {
                        'Source': 'chinawok.pedidos',
                        'DetailType': 'PedidoCreado',
                        'Detail': json.dumps(body_para_evento),  # Los datos del pedido creado
                        'EventBusName': EVENT_BUS_NAME
                    }
                ]
            )
            print(f"Evento publicado a EventBridge: {event_response}")
        except Exception as eb_error:
            print(f"Error publicando evento a EventBridge: {str(eb_error)}")
            # No fallar la creación del pedido si EventBridge falla
        
        # Convertir Decimal a float para la respuesta JSON
        body_respuesta = convertir_decimal_a_float(body)
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Pedido creado exitosamente',
                'data': body_respuesta
            })
        }
        
    except ValidationError as e:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Error de validación',
                'message': str(e.message)
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': 'Error interno del servidor',
                'message': str(e)
            })
        }
