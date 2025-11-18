import json
import boto3
import os

# Cliente DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_PRODUCTOS', 'ChinaWok-Productos')
table = dynamodb.Table(table_name)


def handler(event, context):
    """
    Lambda handler para eliminar un producto de DynamoDB
    """
    try:
        # Obtener parámetros
        params = event.get('queryStringParameters') or {}
        path_params = event.get('pathParameters') or {}
        
        # Intentar obtener de body si no está en params
        body = {}
        if event.get('body'):
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            else:
                body = event['body']
        
        local_id = params.get('local_id') or path_params.get('local_id') or body.get('local_id')
        nombre = params.get('nombre') or path_params.get('nombre') or body.get('nombre')
        
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
        
        # Verificar que el producto existe antes de eliminar
        response = table.get_item(
            Key={
                'local_id': local_id,
                'nombre': nombre
            }
        )
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Producto no encontrado'
                })
            }
        
        # Eliminar el producto
        table.delete_item(
            Key={
                'local_id': local_id,
                'nombre': nombre
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Producto eliminado exitosamente',
                'data': {
                    'local_id': local_id,
                    'nombre': nombre
                }
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
