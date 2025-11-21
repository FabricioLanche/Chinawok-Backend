import json
import boto3
import os
from decimal import Decimal
from botocore.exceptions import ClientError

# Cliente DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_PRODUCTOS', 'ChinaWok-Productos')
table = dynamodb.Table(table_name)

# Categorías válidas
CATEGORIAS_VALIDAS = [
    "Arroces", "Tallarines", "Pollo al wok", "Carne de res", "Cerdo",
    "Mariscos", "Entradas", "Guarniciones", "Sopas", "Combos", "Bebidas", "Postres"
]


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
    Lambda handler para crear un producto en DynamoDB
    """
    try:
        # Parsear el body del evento
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        # Validación manual de campos requeridos
        campos_requeridos = ['local_id', 'nombre', 'precio', 'categoria', 'stock']
        for campo in campos_requeridos:
            if campo not in body:
                return {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                    'body': json.dumps({'error': f'Campo requerido faltante: {campo}'})
                }
        
        # Validar nombre no vacío
        if not body['nombre'].strip():
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'nombre no puede estar vacío'})
            }
        
        # Validar precio
        if not isinstance(body['precio'], (int, float)) or body['precio'] < 0:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'precio debe ser un número positivo'})
            }
        
        # Validar categoría
        if body['categoria'] not in CATEGORIAS_VALIDAS:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': f'categoria debe ser una de: {", ".join(CATEGORIAS_VALIDAS)}'})
            }
        
        # Validar stock
        if not isinstance(body['stock'], int) or body['stock'] < 0:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'error': 'stock debe ser un entero positivo'})
            }
        
        local_id = body.get('local_id')
        nombre = body.get('nombre')
        
        # Verificar que no exista un producto con el mismo nombre en este local
        try:
            response = table.get_item(
                Key={
                    'local_id': local_id,
                    'nombre': nombre
                }
            )
            
            if 'Item' in response:
                return {
                    'statusCode': 400,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Producto duplicado',
                        'message': f"Ya existe un producto con el nombre '{nombre}' en el local {local_id}"
                    })
                }
        except ClientError as e:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Error al verificar producto existente',
                    'message': str(e)
                })
            }
        
        # Convertir floats a Decimal para DynamoDB
        body_decimal = convertir_floats_a_decimal(body)
        
        # Insertar en DynamoDB
        table.put_item(Item=body_decimal)
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Producto creado exitosamente',
                'data': body
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': 'Error interno del servidor', 'message': str(e)})
        }
