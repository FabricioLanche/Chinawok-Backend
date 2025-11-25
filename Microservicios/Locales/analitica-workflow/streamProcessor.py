import json
import os
import boto3
from decimal import Decimal
from datetime import datetime
from utils.logger import get_logger
from utils.dynamodb_client import get_table_data
from utils.s3_client import upload_to_s3

logger = get_logger(__name__)

s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Mapeo de ARN de tabla a nombre de tabla y clave S3
TABLE_MAPPING = {
    'ChinaWok-Locales': 'locales',
    'ChinaWok-Usuarios': 'usuarios',
    'ChinaWok-Productos': 'productos',
    'ChinaWok-Empleados': 'empleados',
    'ChinaWok-Combos': 'combos',
    'ChinaWok-Pedidos': 'pedidos',
    'ChinaWok-Ofertas': 'ofertas',
    'ChinaWok-Resenas': 'resenas',
}

S3_BUCKET = os.environ.get('S3_BUCKET_NAME')
S3_PREFIX = os.environ.get('S3_INGESTION_PREFIX', 'data-ingestion')


def extract_table_name_from_arn(event_source_arn):
    """
    Extrae el nombre de la tabla del ARN del stream
    ARN format: arn:aws:dynamodb:region:account-id:table/TABLE_NAME/stream/timestamp
    """
    try:
        parts = event_source_arn.split('/')
        table_name = parts[1]
        return table_name
    except Exception as e:
        logger.error(f'Error extrayendo nombre de tabla del ARN: {str(e)}')
        return None


def get_table_key(table_name):
    """
    Obtiene la clave S3 correspondiente al nombre de la tabla
    """
    return TABLE_MAPPING.get(table_name)


def handler(event, context):
    """
    Procesa eventos de DynamoDB Streams de múltiples tablas
    Cuando detecta cambios, actualiza el archivo JSONL completo en S3
    
    Estrategia: FULL REFRESH (recarga completa de la tabla)
    - Es más simple y confiable que el incremental
    - Garantiza consistencia total con DynamoDB
    - Eficiente para tablas de tamaño moderado (<100k registros)
    """
    try:
        # El evento puede contener múltiples records de múltiples tablas
        processed_tables = set()
        
        logger.info(f'📥 Recibidos {len(event["Records"])} eventos de DynamoDB Streams')
        
        # Identificar qué tablas fueron modificadas
        for record in event['Records']:
            event_source_arn = record['eventSourceARN']
            table_name = extract_table_name_from_arn(event_source_arn)
            
            if table_name:
                processed_tables.add(table_name)
                event_name = record['eventName']  # INSERT, MODIFY, REMOVE
                logger.info(f'📝 Detectado cambio en tabla: {table_name} (Evento: {event_name})')
        
        # Para cada tabla modificada, hacer un FULL REFRESH
        results = []
        for table_name in processed_tables:
            try:
                table_key = get_table_key(table_name)
                
                if not table_key:
                    logger.warning(f'⚠️  Tabla no mapeada: {table_name}')
                    continue
                
                logger.info(f'🔄 Iniciando FULL REFRESH para tabla: {table_name}')
                
                # 1. Obtener TODOS los datos actuales de DynamoDB
                items = get_table_data(table_name)
                logger.info(f'✅ Obtenidos {len(items)} registros de {table_name}')
                
                # 2. Subir a S3 (sobrescribe el archivo existente)
                s3_key = f'{S3_PREFIX}/{table_key}/data.jsonl'
                s3_uri = upload_to_s3(S3_BUCKET, s3_key, items)
                
                result = {
                    'table': table_name,
                    'table_key': table_key,
                    'records': len(items),
                    's3_location': s3_uri,
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'status': 'success'
                }
                
                results.append(result)
                logger.info(f'✅ FULL REFRESH completado: {table_name} → {s3_uri}')
                
            except Exception as e:
                logger.error(f'❌ Error procesando tabla {table_name}: {str(e)}', exc_info=True)
                results.append({
                    'table': table_name,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Resumen final
        success_count = len([r for r in results if r['status'] == 'success'])
        failed_count = len([r for r in results if r['status'] == 'failed'])
        
        logger.info(f'📊 Procesamiento completado: {success_count} exitosos, {failed_count} fallidos')
        
        return {
            'statusCode': 200,
            'processed_tables': len(processed_tables),
            'successful': success_count,
            'failed': failed_count,
            'results': results
        }
        
    except Exception as e:
        logger.error(f'❌ Error crítico en stream processor: {str(e)}', exc_info=True)
        raise