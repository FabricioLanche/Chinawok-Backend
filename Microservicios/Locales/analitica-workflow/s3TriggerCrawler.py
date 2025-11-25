import json
import boto3
import os
from datetime import datetime, timedelta
from utils.logger import get_logger

logger = get_logger(__name__)
glue = boto3.client('glue')
dynamodb = boto3.resource('dynamodb')

CRAWLER_NAME = os.environ.get('GLUE_CRAWLER_NAME', 'chinawok-analytics-crawler')
ATHENA_DATABASE = os.environ.get('ATHENA_DATABASE', 'chinawok_analytics')

# Lista de tablas esperadas
EXPECTED_TABLES = [
    'locales', 'usuarios', 'productos', 'empleados',
    'combos', 'pedidos', 'ofertas', 'resenas'
]

COOLDOWN_MINUTES = 5  # Tiempo mínimo entre ejecuciones del crawler

# Tabla para control de cooldown (usamos una tabla existente con un item especial)
CONTROL_TABLE = os.environ.get('TABLE_LOCALES')  # Reutilizamos tabla Locales
CONTROL_ITEM_ID = '_CRAWLER_CONTROL_'


def get_last_crawler_execution():
    """
    Obtiene el timestamp de la última ejecución del crawler desde DynamoDB
    """
    try:
        table = dynamodb.Table(CONTROL_TABLE)
        response = table.get_item(
            Key={'local_id': CONTROL_ITEM_ID}
        )
        
        if 'Item' in response:
            last_execution = response['Item'].get('last_crawler_execution')
            if last_execution:
                return datetime.fromisoformat(last_execution.replace('Z', '+00:00'))
        
        return None
        
    except Exception as e:
        logger.error(f'Error obteniendo última ejecución: {str(e)}')
        return None

def check_table_exists(table_name):
    """Verifica si la tabla ya existe en Glue Data Catalog"""
    try:
        glue.get_table(
            DatabaseName=ATHENA_DATABASE,
            Name=table_name
        )
        return True
    except glue.exceptions.EntityNotFoundException:
        return False
    except Exception as e:
        logger.error(f'Error verificando tabla {table_name}: {str(e)}')
        return False

def update_last_crawler_execution():
    """
    Actualiza el timestamp de la última ejecución del crawler
    """
    try:
        table = dynamodb.Table(CONTROL_TABLE)
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        table.put_item(
            Item={
                'local_id': CONTROL_ITEM_ID,
                'last_crawler_execution': timestamp,
                'updated_at': timestamp
            }
        )
        
        logger.info(f'✅ Timestamp actualizado: {timestamp}')
        
    except Exception as e:
        logger.error(f'Error actualizando timestamp: {str(e)}')


def should_execute_crawler():
    """
    Verifica si ha pasado suficiente tiempo desde la última ejecución (cooldown)
    """
    last_execution = get_last_crawler_execution()
    
    if not last_execution:
        logger.info('Primera ejecución del crawler')
        return True
    
    time_since_last = datetime.utcnow() - last_execution.replace(tzinfo=None)
    cooldown_delta = timedelta(minutes=COOLDOWN_MINUTES)
    
    if time_since_last < cooldown_delta:
        remaining = cooldown_delta - time_since_last
        logger.info(f'⏳ Cooldown activo. Faltan {remaining.seconds}s para poder ejecutar crawler')
        return False
    
    logger.info(f'✅ Cooldown expirado. Última ejecución: {time_since_last} atrás')
    return True

def handler(event, context):
    """
    Lambda disparado por eventos S3 cuando se actualiza un archivo .jsonl
    
    LÓGICA INTELIGENTE:
    - Solo ejecuta el crawler si alguna tabla NO existe en Glue
    - Una vez que todas las tablas existen, deja que Athena lea los archivos actualizados
    - Athena es schema-on-read, no necesita crawler después de la primera vez
    """
    try:
        # Extraer información del evento S3
        s3_events = []
        for record in event.get('Records', []):
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            event_name = record['eventName']
            
            s3_events.append({
                'bucket': bucket,
                'key': key,
                'event': event_name
            })
            
            logger.info(f'📦 S3 Event: {event_name} → s3://{bucket}/{key}')
        
        # Verificar qué tablas faltan en Glue
        missing_tables = []
        for table in EXPECTED_TABLES:
            if not check_table_exists(table):
                missing_tables.append(table)
        
        # Si todas las tablas existen, no ejecutar crawler
        if not missing_tables:
            logger.info('✅ Todas las tablas ya existen en Glue Data Catalog')
            logger.info('📊 Athena detectará automáticamente los datos actualizados')
            
            return {
                'statusCode': 200,
                'message': 'No crawler needed - all tables exist',
                'action': 'skipped',
                'reason': 'schemas_already_created',
                's3_events': s3_events
            }
        
        # Hay tablas faltantes, ejecutar crawler
        logger.info(f'🆕 Tablas faltantes detectadas: {missing_tables}')
        logger.info(f'🚀 Ejecutando Crawler para crear schemas...')
        
        # Verificar cooldown antes de ejecutar
        if not should_execute_crawler():
            logger.info('🚫 Crawler no ejecutado debido al cooldown')
            return {
                'statusCode': 200,
                'message': 'Crawler skipped due to cooldown',
                'cooldown_minutes': COOLDOWN_MINUTES,
                'missing_tables': missing_tables,
                's3_events': s3_events
            }
        
        # Verificar estado del crawler
        try:
            crawler_info = glue.get_crawler(Name=CRAWLER_NAME)
            crawler_state = crawler_info['Crawler']['State']
            
            if crawler_state == 'RUNNING':
                logger.warning('⚠️  Crawler ya está en ejecución')
                return {
                    'statusCode': 200,
                    'message': 'Crawler already running',
                    'crawler_name': CRAWLER_NAME,
                    'state': 'ALREADY_RUNNING'
                }
            
        except glue.exceptions.EntityNotFoundException:
            logger.error(f'❌ Crawler no encontrado: {CRAWLER_NAME}')
            return {
                'statusCode': 404,
                'message': f'Crawler {CRAWLER_NAME} not found'
            }
        
        # Iniciar el crawler
        glue.start_crawler(Name=CRAWLER_NAME)
        logger.info(f'✅ Crawler iniciado para crear {len(missing_tables)} tablas: {CRAWLER_NAME}')
        
        # Actualizar timestamp de última ejecución
        update_last_crawler_execution()
        
        return {
            'statusCode': 200,
            'message': 'Crawler started successfully',
            'crawler_name': CRAWLER_NAME,
            'triggered_by': 's3_event',
            'missing_tables': missing_tables,
            's3_events': s3_events,
            'cooldown_minutes': COOLDOWN_MINUTES
        }
        
    except Exception as e:
        logger.error(f'❌ Error en s3TriggerCrawler: {str(e)}', exc_info=True)
        raise