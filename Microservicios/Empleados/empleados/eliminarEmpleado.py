import boto3, json, os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_EMPLEADOS'])

def lambda_handler(event, context):
    # Headers CORS
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }
    
    # Manejar preflight request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': 'CORS preflight successful'})
        }
    
    local_id = event['pathParameters']['local_id']
    dni = event['pathParameters']['dni']
    
    table.delete_item(Key={'local_id': local_id, 'dni': dni})
    
    return {
        'statusCode': 200,
        'headers': headers,
        'body': json.dumps({'message': 'Empleado eliminado'})
    }