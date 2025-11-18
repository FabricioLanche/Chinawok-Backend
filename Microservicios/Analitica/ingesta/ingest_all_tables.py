import json
import os
from datetime import datetime
from ingesta.utils.dynamodb_client import get_table_data
from ingesta.utils.s3_client import upload_to_s3
from ingesta.utils.logger import get_logger

logger = get_logger(__name__)

TABLES = {
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
    Handler para ingestar todas las tablas de DynamoDB a S3
    """
    results = []
    errors = []
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    bucket = os.environ['S3_BUCKET_NAME']
    
    logger.info(f'Iniciando ingesta de {len(TABLES)} tablas')
    
    for table_key, dynamodb_table in TABLES.items():
        try:
            logger.info(f'Procesando tabla: {dynamodb_table}')
            
            # Obtener datos de DynamoDB
            items = get_table_data(dynamodb_table)
            logger.info(f'Obtenidos {len(items)} items de {dynamodb_table}')
            
            # Preparar ruta S3
            s3_key = f'ingesta/{table_key}/{timestamp}.json'
            
            # Subir datos directamente a S3 (sin wrapper)
            upload_to_s3(bucket, s3_key, items)
            
            results.append({
                'table': table_key,
                'dynamodb_table': dynamodb_table,
                'records': len(items),
                's3_location': f's3://{bucket}/{s3_key}',
                'status': 'success'
            })
            
            logger.info(f'Tabla {table_key} procesada exitosamente')
            
        except Exception as e:
            error_msg = f'Error procesando {table_key}: {str(e)}'
            logger.error(error_msg, exc_info=True)
            errors.append({
                'table': table_key,
                'error': str(e),
                'status': 'failed'
            })
    
    # Preparar respuesta
    response_body = {
        'message': 'Proceso de ingesta completado',
        'timestamp': timestamp,
        'total_tables': len(TABLES),
        'successful': len(results),
        'failed': len(errors),
        'results': results
    }
    
    if errors:
        response_body['errors'] = errors
    
    status_code = 200 if not errors else 207
    
    logger.info(f'Ingesta completada: {len(results)} exitosas, {len(errors)} fallidas')
    
    return {
        'statusCode': status_code,
        'body': json.dumps(response_body)
    }
