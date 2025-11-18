import json
import os
from datetime import datetime
from ingesta.utils.dynamodb_client import get_table_data
from ingesta.utils.s3_client import upload_to_s3
from ingesta.utils.logger import get_logger

logger = get_logger(__name__)

VALID_TABLES = {
    'locales': os.environ['TABLE_LOCALES'],
    'usuarios': os.environ['TABLE_USUARIOS'],
    'productos': os.environ['TABLE_PRODUCTOS'],
    'empleados': os.environ['TABLE_EMPLEADOS'],
    'combos': os.environ['TABLE_COMBOS'],
    'pedidos': os.environ['TABLE_PEDIDOS'],
    'ofertas': os.environ['TABLE_OFERTAS'],
    'resenas': os.environ['TABLE_RESENAS'],
}

def handler(event, context):
    """
    Handler para ingestar datos de una tabla específica de DynamoDB a S3
    """
    try:
        # Obtener nombre de tabla del path parameter
        table_name = event.get('pathParameters', {}).get('tableName')
        
        if not table_name or table_name not in VALID_TABLES:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Nombre de tabla inválido. Tablas válidas: {list(VALID_TABLES.keys())}'
                })
            }
        
        dynamodb_table = VALID_TABLES[table_name]
        logger.info(f'Iniciando ingesta de tabla: {dynamodb_table}')
        
        # Obtener datos de DynamoDB
        items = get_table_data(dynamodb_table)
        logger.info(f'Obtenidos {len(items)} items de {dynamodb_table}')
        
        # Preparar ruta S3
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        s3_key = f'ingesta/{table_name}/{timestamp}.json'
        
        # Subir datos directamente a S3 (sin wrapper)
        bucket = os.environ['S3_BUCKET_NAME']
        upload_to_s3(bucket, s3_key, items)
        
        logger.info(f'Datos subidos exitosamente a s3://{bucket}/{s3_key}')
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Ingesta completada exitosamente',
                'table': table_name,
                'dynamodb_table': dynamodb_table,
                'records': len(items),
                's3_location': f's3://{bucket}/{s3_key}'
            })
        }
        
    except Exception as e:
        logger.error(f'Error en ingesta: {str(e)}', exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Error durante la ingesta',
                'details': str(e)
            })
        }
