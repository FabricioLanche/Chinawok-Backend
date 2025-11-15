import boto3, json, os
from boto3.dynamodb.conditions import Key
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
        # Verificar que pathParameters existe
        if 'pathParameters' not in event or event['pathParameters'] is None:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Parámetros de ruta faltantes'})
            }

        local_id = event['pathParameters']['local_id']

        response = table.query(
            KeyConditionExpression=Key('local_id').eq(local_id)
        )

        return {'statusCode': 200, 'body': json.dumps(response['Items'], cls=DecimalEncoder)}

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
