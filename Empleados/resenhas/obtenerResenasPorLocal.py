import boto3, json, os
from boto3.dynamodb.conditions import Key
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
tabla_resenas = dynamodb.Table(os.environ['TABLE_RESENAS'])

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    local_id = event['pathParameters']['local_id']
    
    try:
        # Consultar todas las reseñas por local_id (partition key)
        response = tabla_resenas.query(
            KeyConditionExpression=Key('local_id').eq(local_id)
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'local_id': local_id,
                'total_resenas': len(response['Items']),
                'resenas': response['Items']
            }, cls=DecimalEncoder)
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f"Error al consultar reseñas: {str(e)}"})
        }
