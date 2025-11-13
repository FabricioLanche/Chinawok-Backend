import json
import boto3
import os

# Cliente DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_COMBOS', 'ChinaWok-Combos')
table = dynamodb.Table(table_name)


def handler(event, context):
    """
    Lambda handler para eliminar un combo de DynamoDB
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
        combo_id = params.get('combo_id') or path_params.get('combo_id') or body.get('combo_id')
        
        if not local_id or not combo_id:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Se requieren local_id y combo_id'
                })
            }
        
        # Verificar que el combo existe antes de eliminar
        response = table.get_item(
            Key={
                'local_id': local_id,
                'combo_id': combo_id
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
                    'error': 'Combo no encontrado'
                })
            }
        
        # Eliminar el combo
        table.delete_item(
            Key={
                'local_id': local_id,
                'combo_id': combo_id
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Combo eliminado exitosamente',
                'data': {
                    'local_id': local_id,
                    'combo_id': combo_id
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
