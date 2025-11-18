import json
import boto3
import os
from decimal import Decimal
from jsonschema import validate, ValidationError

# Cliente DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_PRODUCTOS', 'ChinaWok-Productos')
table = dynamodb.Table(table_name)

# Schema de validación (sin requerir todas las propiedades para update parcial)
PRODUCTO_UPDATE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "ProductosUpdate",
    "type": "object",
    "properties": {
        "precio": {"type": "number", "minimum": 0},
        "descripcion": {"type": "string"},
        "categoria": {
            "type": "string",
            "enum": [
                "Arroces",
                "Tallarines",
                "Pollo al wok",
                "Carne de res",
                "Cerdo",
                "Mariscos",
                "Entradas",
                "Guarniciones",
                "Sopas",
                "Combos",
                "Bebidas",
                "Postres"
            ]
        },
        "stock": {"type": "integer", "minimum": 0}
    },
    "additionalProperties": False,
    "minProperties": 1
}


def convertir_floats_a_decimal(obj):
    """
    Convierte floats a Decimal para compatibilidad con DynamoDB
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convertir_floats_a_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convertir_floats_a_decimal(item) for item in obj]
    return obj


def handler(event, context):
    """
    Lambda handler para actualizar un producto en DynamoDB
    """
    try:
        # Parsear el body del evento
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        # Obtener las keys
        local_id = body.get('local_id')
        nombre = body.get('nombre')
        
        if not local_id or not nombre:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Se requieren local_id y nombre'
                })
            }
        
        # Crear una copia sin las keys para validar solo los campos actualizables
        update_data = {k: v for k, v in body.items() if k not in ['local_id', 'nombre']}
        
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
        validate(instance=update_data, schema=PRODUCTO_UPDATE_SCHEMA)
        
        # Verificar que el producto existe antes de actualizar
        existing_product = table.get_item(
            Key={
                'local_id': local_id,
                'nombre': nombre
            }
        )
        
        if 'Item' not in existing_product:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Producto no encontrado',
                    'message': f"El producto '{nombre}' no existe en el local {local_id}"
                })
            }
        
        # Convertir floats a Decimal para DynamoDB
        update_data_decimal = convertir_floats_a_decimal(update_data)
        
        # Construir expresión de actualización
        update_expression = "SET " + ", ".join([f"#{k} = :{k}" for k in update_data_decimal.keys()])
        expression_attribute_names = {f"#{k}": k for k in update_data_decimal.keys()}
        expression_attribute_values = {f":{k}": v for k, v in update_data_decimal.items()}
        
        # Actualizar en DynamoDB
        response = table.update_item(
            Key={
                'local_id': local_id,
                'nombre': nombre
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
                'message': 'Producto actualizado exitosamente',
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
