import json
import boto3
import os
from utils.logger import get_logger

logger = get_logger(__name__)
glue = boto3.client('glue')

CRAWLER_NAME = os.environ.get('GLUE_CRAWLER_NAME', 'chinawok-analytics-crawler')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'chinawok-data')
S3_INGESTION_PREFIX = os.environ.get('S3_INGESTION_PREFIX', 'data-ingestion')
ATHENA_DATABASE = os.environ.get('ATHENA_DATABASE', 'chinawok_analytics')
AWS_ACCOUNT_ID = os.environ.get('AWS_ACCOUNT_ID')

def create_crawler():
    """Crea el crawler de Glue si no existe"""
    # Construir ARN del LabRole con el Account ID
    glue_role_arn = f"arn:aws:iam::{AWS_ACCOUNT_ID}:role/LabRole"
    s3_target_path = f"s3://{S3_BUCKET_NAME}/{S3_INGESTION_PREFIX}/"
    
    logger.info(f'Creando crawler: {CRAWLER_NAME}')
    logger.info(f'Rol IAM: {glue_role_arn}')
    logger.info(f'Path S3: {s3_target_path}')
    logger.info(f'Database: {ATHENA_DATABASE}')
    
    try:
        glue.create_crawler(
            Name=CRAWLER_NAME,
            Role=glue_role_arn,
            DatabaseName=ATHENA_DATABASE,
            Targets={
                'S3Targets': [
                    {
                        'Path': s3_target_path,
                        'Exclusions': []
                    }
                ]
            },
            Description='Crawler automático para datos ingeridos desde DynamoDB',
            SchemaChangePolicy={
                'UpdateBehavior': 'UPDATE_IN_DATABASE',
                'DeleteBehavior': 'DEPRECATE_IN_DATABASE'
            },
            RecrawlPolicy={
                'RecrawlBehavior': 'CRAWL_EVERYTHING'
            },
            Configuration=json.dumps({
                'Version': 1.0,
                'CrawlerOutput': {
                    'Partitions': {'AddOrUpdateBehavior': 'InheritFromTable'}
                }
            })
        )
        
        logger.info(f'✅ Crawler {CRAWLER_NAME} creado exitosamente')
        return True
        
    except Exception as e:
        logger.error(f'Error creando crawler: {str(e)}')
        raise

def handler(event, context):
    """
    Lambda que ejecuta el crawler de AWS Glue
    Lo crea automáticamente si no existe
    """
    try:
        logger.info(f'Iniciando ejecución del crawler: {CRAWLER_NAME}')
        
        # Verificar si el crawler existe
        try:
            crawler_info = glue.get_crawler(Name=CRAWLER_NAME)
            logger.info(f'Crawler encontrado: {CRAWLER_NAME}')
        except glue.exceptions.EntityNotFoundException:
            logger.info(f'Crawler no existe, creándolo: {CRAWLER_NAME}')
            create_crawler()
        
        # Verificar estado del crawler antes de iniciar
        crawler_details = glue.get_crawler(Name=CRAWLER_NAME)
        crawler_state = crawler_details['Crawler']['State']
        
        if crawler_state == 'RUNNING':
            logger.warning('Crawler ya está en ejecución')
            return {
                'statusCode': 200,
                'message': 'Crawler ya está en ejecución',
                'crawler_name': CRAWLER_NAME,
                'state': 'ALREADY_RUNNING'
            }
        
        # Iniciar el crawler
        response = glue.start_crawler(Name=CRAWLER_NAME)
        
        logger.info(f'Crawler iniciado exitosamente: {CRAWLER_NAME}')
        
        return {
            'statusCode': 200,
            'message': 'Crawler iniciado exitosamente',
            'crawler_name': CRAWLER_NAME,
            'state': 'STARTED'
        }
        
    except Exception as e:
        logger.error(f'Error ejecutando crawler: {str(e)}', exc_info=True)
        raise
