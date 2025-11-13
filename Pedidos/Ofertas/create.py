import json
import boto3
import os
import uuid
from jsonschema import validate, ValidationError
from botocore.exceptions import ClientError

# Cliente DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_OFERTAS', 'ChinaWok-Ofertas')
table = dynamodb.Table(table_name)

# Tabla de locales
locales_table_name = os.environ.get('TABLE_LOCALES', 'ChinaWok-Locales')
locales_table = dynamodb.Table(locales_table_name)

# Tabla de productos
productos_table_name = os.environ.get('TABLE_PRODUCTOS', 'ChinaWok-Productos')
productos_table = dynamodb.Table(productos_table_name)

# Tabla de combos
combos_table_name = os.environ.get('TABLE_COMBOS', 'ChinaWok-Combos')
combos_table = dynamodb.Table(combos_table_name)

# Schema de validación (sin oferta_id ya que se genera automáticamente)
OFERTA_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Ofertas",
    "type": "object",
    "properties": {
        "local_id": {"type": "string"},
        "producto_nombre": {"type": "string"},
        "combo_id": {"type": "string"},
        "fecha_inicio": {"type": "string", "format": "date-time"},
        "fecha_limite": {"type": "string", "format": "date-time"},
        "porcentaje_descuento": {"type": "number", "minimum": 0, "maximum": 100}
    },
    "required": ["local_id", "porcentaje_descuento", "fecha_inicio", "fecha_limite"],
    "additionalProperties": False,
    "anyOf": [
        {"required": ["producto_nombre"]},
        {"required": ["combo_id"]}
    ]
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


def verificar_producto_existe(local_id, producto_nombre):
    """
    Verifica que el producto exista en el local especificado
    Returns: (bool, str) - (éxito, mensaje de error)
    """
    try:
        response = productos_table.get_item(
            Key={
                'local_id': local_id,
                'nombre': producto_nombre
            }
        )
        
        if 'Item' not in response:
            return False, f"El producto '{producto_nombre}' no existe en el local {local_id}"
        
        return True, None
        
    except ClientError as e:
        return False, f"Error al verificar producto: {str(e)}"


def verificar_combo_existe(local_id, combo_id):
    """
    Verifica que el combo exista en el local especificado
    Returns: (bool, str) - (éxito, mensaje de error)
    """
    try:
        response = combos_table.get_item(
            Key={
                'local_id': local_id,
                'combo_id': combo_id
            }
        )
        
        if 'Item' not in response:
            return False, f"El combo '{combo_id}' no existe en el local {local_id}"
        
        return True, None
        
    except ClientError as e:
        return False, f"Error al verificar combo: {str(e)}"


def handler(event, context):
    """
    Lambda handler para crear una oferta en DynamoDB
    """
    try:
        # Parsear el body del evento
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        # Validar schema
        validate(instance=body, schema=OFERTA_SCHEMA)
        
        # Validar que tenga producto_nombre o combo_id
        if 'producto_nombre' not in body and 'combo_id' not in body:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Debe especificar producto_nombre o combo_id'
                })
            }
        
        local_id = body.get('local_id')
        
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
        
        # Verificar que el producto existe si se especificó
        if 'producto_nombre' in body:
            exito, error_msg = verificar_producto_existe(local_id, body['producto_nombre'])
            if not exito:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Error de validación de producto',
                        'message': error_msg
                    })
                }
        
        # Verificar que el combo existe si se especificó
        if 'combo_id' in body:
            exito, error_msg = verificar_combo_existe(local_id, body['combo_id'])
            if not exito:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Error de validación de combo',
                        'message': error_msg
                    })
                }
        
        # Generar oferta_id automáticamente con UUID
        oferta_id = str(uuid.uuid4())
        body['oferta_id'] = oferta_id
        
        # Insertar en DynamoDB
        table.put_item(Item=body)
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Oferta creada exitosamente',
                'data': body
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
