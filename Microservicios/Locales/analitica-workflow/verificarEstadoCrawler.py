import json
import boto3
import os
from utils.logger import get_logger

logger = get_logger(__name__)
glue = boto3.client('glue')

CRAWLER_NAME = os.environ.get('GLUE_CRAWLER_NAME', 'chinawok-analytics-crawler')

def handler(event, context):
    """
    Lambda que verifica el estado del crawler de Glue
    Retorna el estado actual para que Step Functions decida si continuar esperando
    """
    try:
        logger.info(f'Verificando estado del crawler: {CRAWLER_NAME}')
        
        # Obtener estado del crawler
        response = glue.get_crawler(Name=CRAWLER_NAME)
        crawler = response['Crawler']
        
        state = crawler['State']
        last_crawl = crawler.get('LastCrawl', {})
        
        logger.info(f'Estado del crawler: {state}')
        
        # Estados posibles: READY, RUNNING, STOPPING
        if state == 'READY':
            # Crawler completado
            status = last_crawl.get('Status', 'UNKNOWN')
            
            if status == 'SUCCEEDED':
                logger.info('Crawler completado exitosamente')
                return {
                    'crawler_status': 'COMPLETED',
                    'crawler_state': state,
                    'tables_created': last_crawl.get('TablesCreated', 0),
                    'tables_updated': last_crawl.get('TablesUpdated', 0),
                    'continue_waiting': False
                }
            elif status == 'FAILED':
                error_message = last_crawl.get('ErrorMessage', 'Error desconocido')
                logger.error(f'Crawler falló: {error_message}')
                return {
                    'crawler_status': 'FAILED',
                    'crawler_state': state,
                    'error_message': error_message,
                    'continue_waiting': False
                }
            else:
                logger.warning(f'Crawler en estado READY pero con status: {status}')
                return {
                    'crawler_status': status,
                    'crawler_state': state,
                    'continue_waiting': False
                }
        
        elif state == 'RUNNING':
            # Crawler aún ejecutándose
            logger.info('Crawler aún en ejecución, continuar esperando')
            return {
                'crawler_status': 'RUNNING',
                'crawler_state': state,
                'continue_waiting': True
            }
        
        elif state == 'STOPPING':
            # Crawler deteniéndose
            logger.info('Crawler deteniéndose, continuar esperando')
            return {
                'crawler_status': 'STOPPING',
                'crawler_state': state,
                'continue_waiting': True
            }
        
        else:
            # Estado desconocido
            logger.warning(f'Estado desconocido del crawler: {state}')
            return {
                'crawler_status': 'UNKNOWN',
                'crawler_state': state,
                'continue_waiting': False
            }
        
    except glue.exceptions.EntityNotFoundException:
        logger.error(f'Crawler no encontrado: {CRAWLER_NAME}')
        return {
            'crawler_status': 'NOT_FOUND',
            'error_message': f'Crawler {CRAWLER_NAME} no existe',
            'continue_waiting': False
        }
    
    except Exception as e:
        logger.error(f'Error verificando estado del crawler: {str(e)}', exc_info=True)
        raise
