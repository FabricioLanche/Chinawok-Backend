import json
import boto3
import os
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

# Schema de validación (sin requerir todas las propiedades para update parcial)
# Permite actualizar producto_nombre, combo_id o ambos para cambiar los elementos ligados a la oferta
OFERTA_UPDATE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "OfertasUpdate",
    "type": "object",
    "properties": {
        "producto_nombre": {"type": "string"},
        "combo_id": {"type": "string"},
        "fecha_inicio": {"type": "string", "format": "date-time"},
        "fecha_limite": {"type": "string", "format": "date-time"},
        "porcentaje_descuento": {"type": "number", "minimum": 0, "maximum": 100}
    },
    "additionalProperties": False,
    "minProperties": 1
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
    Lambda handler para actualizar una oferta en DynamoDB
    """
    try:
        # Parsear el body del evento
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        # Obtener las keys
        local_id = body.get('local_id')
        oferta_id = body.get('oferta_id')
        
        if not local_id or not oferta_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Se requieren local_id y oferta_id'
                })
            }
        
        # Crear una copia sin las keys para validar solo los campos actualizables
        update_data = {k: v for k, v in body.items() if k not in ['local_id', 'oferta_id']}
        
        if not update_data:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'No se proporcionaron campos para actualizar'
                })
            }
        
        # Validar schema
        validate(instance=update_data, schema=OFERTA_UPDATE_SCHEMA)
        
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
        
        # Verificar que el producto existe si se especificó en la actualización
        if 'producto_nombre' in update_data:
            exito, error_msg = verificar_producto_existe(local_id, update_data['producto_nombre'])
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
        
        # Verificar que el combo existe si se especificó en la actualización
        if 'combo_id' in update_data:
            exito, error_msg = verificar_combo_existe(local_id, update_data['combo_id'])
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
        
        # Construir expresión de actualización
        # Si se proporciona producto_nombre o combo_id, se pueden actualizar
        # Nota: DynamoDB permite tener ambos campos, aunque la lógica de negocio 
        # indica que debería ser uno u otro
        update_expression = "SET " + ", ".join([f"#{k} = :{k}" for k in update_data.keys()])
        expression_attribute_names = {f"#{k}": k for k in update_data.keys()}
        expression_attribute_values = {f":{k}": v for k, v in update_data.items()}
        
        # Actualizar en DynamoDB
        response = table.update_item(
            Key={
                'local_id': local_id,
                'oferta_id': oferta_id
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW"
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Oferta actualizada exitosamente',
                'data': response['Attributes']
            }, default=str)
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
