import json
import boto3
import os
import time
from utils.logger import get_logger

logger = get_logger(__name__)
glue = boto3.client('glue')

CRAWLER_NAME = os.environ.get('GLUE_CRAWLER_NAME', 'chinawok-analytics-crawler')

def handler(event, context):
    """
    Lambda que ejecuta el crawler de AWS Glue para crear/actualizar
    las tablas en el Data Catalog
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
            time.sleep(3)  # Esperar un poco después de crear
        
        # Verificar estado del crawler antes de iniciar
        crawler_state = glue.get_crawler(Name=CRAWLER_NAME)['Crawler']['State']
        
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


def create_crawler():
    """
    Crea el crawler de Glue si no existe
    """
    database_name = os.environ.get('ATHENA_DATABASE', 'chinawok_analytics')
    s3_path = os.environ.get('S3_BUCKET_NAME', 'chinawok-data/data-ingestion')
    role_arn = f"arn:aws:iam::{os.environ.get('AWS_ACCOUNT_ID')}:role/LabRole"
    
    # Construir la ruta S3 completa
    if not s3_path.startswith('s3://'):
        s3_path = f's3://{s3_path}/'
    
    try:
        glue.create_crawler(
            Name=CRAWLER_NAME,
            Role=role_arn,
            DatabaseName=database_name,
            Description='Crawler para analítica de ChinaWok - Crea tablas automáticamente desde datos en S3',
            Targets={
                'S3Targets': [
                    {
                        'Path': s3_path,
                        'Exclusions': []
                    }
                ]
            },
            SchemaChangePolicy={
                'UpdateBehavior': 'UPDATE_IN_DATABASE',
                'DeleteBehavior': 'LOG'
            },
            RecrawlPolicy={
                'RecrawlBehavior': 'CRAWL_EVERYTHING'
            },
            LineageConfiguration={
                'CrawlerLineageSettings': 'DISABLE'
            }
        )
        
        logger.info(f'Crawler creado exitosamente: {CRAWLER_NAME}')
        
    except glue.exceptions.AlreadyExistsException:
        logger.info(f'Crawler ya existe: {CRAWLER_NAME}')
    except Exception as e:
        logger.error(f'Error creando crawler: {str(e)}', exc_info=True)
        raise
