import json
import boto3
import os
import uuid
from decimal import Decimal
from jsonschema import validate, ValidationError

# Cliente DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_COMBOS', 'ChinaWok-Combos')
table = dynamodb.Table(table_name)

# Schema de validación
COMBO_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Combos",
    "type": "object",
    "properties": {
        "local_id": {"type": "string"},
        "nombre": {"type": "string"},
        "productos_nombres": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1
        },
        "descripcion": {"type": "string"}
    },
    "required": ["local_id", "nombre", "productos_nombres"],
    "additionalProperties": False
}


def handler(event, context):
    """
    Lambda handler para crear un combo en DynamoDB
    """
    try:
        # Parsear el body del evento
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        # Validar schema
        validate(instance=body, schema=COMBO_SCHEMA)
        
        # Generar combo_id único usando UUID
        body['combo_id'] = str(uuid.uuid4())
        
        # Insertar en DynamoDB
        table.put_item(Item=body)
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Combo creado exitosamente',
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
