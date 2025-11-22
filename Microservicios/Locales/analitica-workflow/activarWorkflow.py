import json
import boto3
import os
from datetime import datetime

stepfunctions = boto3.client('stepfunctions')

STEP_FUNCTION_ARN = os.environ.get('STEP_FUNCTION_ANALITICA_ARN')

def handler(event, context):
    """
    Lambda que activa el workflow de analítica mediante Step Functions
    Puede ser invocado manualmente o mediante EventBridge programado
    """
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
    
    try:
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        
        # Payload para el Step Function
        input_data = {
            'timestamp': timestamp,
            'trigger': event.get('trigger', 'manual'),
            'message': 'Iniciando workflow de analítica'
        }
        
        # Iniciar ejecución del Step Function
        response = stepfunctions.start_execution(
            stateMachineArn=STEP_FUNCTION_ARN,
            name=f'analitica-workflow-{timestamp}',
            input=json.dumps(input_data)
        )
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'message': 'Workflow de analítica iniciado exitosamente',
                'executionArn': response['executionArn'],
                'startDate': response['startDate'].isoformat()
            })
        }
        
    except Exception as e:
        print(f'Error iniciando workflow: {str(e)}')
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Error iniciando workflow de analítica',
                'details': str(e)
            })
        }