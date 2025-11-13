import boto3, json, os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_EMPLEADOS'])

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    try:
        local_id = event['pathParameters']['local_id']
        dni = event['pathParameters']['dni']

        response = table.get_item(Key={'local_id': local_id, 'dni': dni})

        if 'Item' not in response:
            return {'statusCode': 404, 'body': json.dumps({'error': 'Empleado no encontrado'})}

        return {'statusCode': 200, 'body': json.dumps(response['Item'], cls=DecimalEncoder)}

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Error interno: {str(e)}'})
        }
