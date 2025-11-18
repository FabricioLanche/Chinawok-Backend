import boto3, json, os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_RESENAS'])

def lambda_handler(event, context):
    local_id = event['pathParameters']['local_id']
    resena_id = event['pathParameters']['resena_id']

    try:
        table.delete_item(Key={'local_id': local_id, 'resena_id': resena_id})
        return {'statusCode': 200, 'body': json.dumps({'message': 'Reseña eliminada'})}
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': f"Error al eliminar reseña: {str(e)}"})}
