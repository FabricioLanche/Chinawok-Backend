import json
import boto3
import os

# Cliente DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_PEDIDOS', 'ChinaWok-Pedidos')
table = dynamodb.Table(table_name)


def handler(event, context):
    """
    Lambda handler para eliminar un pedido de DynamoDB
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
        pedido_id = params.get('pedido_id') or path_params.get('pedido_id') or body.get('pedido_id')
        
        if not local_id or not pedido_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Se requieren local_id y pedido_id'
                })
            }
        
        # Verificar que el pedido existe antes de eliminar
        response = table.get_item(
            Key={
                'local_id': local_id,
                'pedido_id': pedido_id
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
                    'error': 'Pedido no encontrado'
                })
            }
        
        # Eliminar el pedido
        table.delete_item(
            Key={
                'local_id': local_id,
                'pedido_id': pedido_id
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Pedido eliminado exitosamente',
                'data': {
                    'local_id': local_id,
                    'pedido_id': pedido_id
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
