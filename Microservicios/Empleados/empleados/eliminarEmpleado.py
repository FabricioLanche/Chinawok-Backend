import boto3, json, os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_EMPLEADOS'])

def lambda_handler(event, context):
    local_id = event['pathParameters']['local_id']
    dni = event['pathParameters']['dni']

    table.delete_item(Key={'local_id': local_id, 'dni': dni})
    return {'statusCode': 200, 'body': json.dumps({'message': 'Empleado eliminado'})}
