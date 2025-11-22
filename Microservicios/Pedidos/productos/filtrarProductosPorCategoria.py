import json
import boto3
import os
from boto3.dynamodb.conditions import Key, Attr

# Cliente DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_PRODUCTOS', 'ChinaWok-Productos')
table = dynamodb.Table(table_name)

def handler(event, context):
    """
    Lambda handler para filtrar productos por categoría en DynamoDB
    """
    try:
        # Obtener parámetros de query
        params = event.get('queryStringParameters') or {}
        
        local_id = params.get('local_id')
        categoria = params.get('categoria')
        
        if not local_id or not categoria:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Parámetros requeridos: local_id y categoria'
                })
            }
        
        # Escanear la tabla con un filtro por local_id y categoria
        response = table.scan(
            FilterExpression=Attr('local_id').eq(local_id) & Attr('categoria').eq(categoria)
        )
        
        if not response.get('Items'):
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'No se encontraron productos para la categoría especificada'
                })
            }
            
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'data': response['Items'],
                'count': len(response['Items'])
            }, default=str)
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
