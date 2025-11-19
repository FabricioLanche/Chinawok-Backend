import json
import os
from datetime import datetime
from utils.dynamodb_client import get_table_data
from utils.s3_client import upload_to_s3
from utils.logger import get_logger

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
    Usa nombres de archivo FIJOS que se sobreescriben en cada ejecución
    """
    results = []
    errors = []
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    
    # Obtener bucket y prefijo de variables de entorno
    bucket = os.environ.get('S3_BUCKET_NAME', 'chinawok-data')
    ingestion_prefix = os.environ.get('S3_INGESTION_PREFIX', 'data-ingestion')
    
    logger.info(f'🚀 Iniciando ingesta de {len(TABLES)} tablas - Timestamp: {timestamp}')
    logger.info(f'📦 Bucket: {bucket}, Prefijo: {ingestion_prefix}, Formato: JSONL')
    logger.info(f'♻️  Modo: SOBREESCRITURA (un solo archivo por tabla)')
    
    for table_key, dynamodb_table in TABLES.items():
        try:
            logger.info(f'📋 Procesando tabla: {dynamodb_table}')
            
            # Obtener datos de DynamoDB
            items = get_table_data(dynamodb_table)
            logger.info(f'✅ Obtenidos {len(items)} items de {dynamodb_table}')
            
            # CAMBIO IMPORTANTE: Usar nombre de archivo FIJO sin timestamp
            # Esto hace que siempre se sobreescriba el archivo anterior
            s3_key = f'{ingestion_prefix}/{table_key}/data.jsonl'
            
            # Subir datos a S3 en formato JSONL (sobreescribe archivo existente)
            s3_uri = upload_to_s3(bucket, s3_key, items)
            
            result = {
                'table': table_key,
                'dynamodb_table': dynamodb_table,
                'records': len(items),
                's3_location': s3_uri,
                'format': 'jsonl',
                'status': 'success',
                'overwritten': True  # Indica que se sobreescribió
            }
            
            results.append(result)
            logger.info(f'✅ Tabla {table_key} procesada: {len(items)} registros → {s3_key}')
            
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
        'mode': 'overwrite',
        'results': results
    }
    
    if errors:
        response_body['errors'] = errors
        logger.error(f'❌ Ingesta completada con errores: {len(errors)} tablas fallidas')
    else:
        logger.info(f'✅ Ingesta completada exitosamente: {len(results)} tablas procesadas')
        logger.info(f'♻️  Todos los archivos fueron sobreescritos con datos actualizados')
    
    status_code = 200 if not errors else 207
    
    return {
        'statusCode': status_code,
        'body': json.dumps(response_body)
    }
