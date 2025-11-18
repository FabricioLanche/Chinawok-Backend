import json
import boto3
from ingesta.utils.logger import get_logger

logger = get_logger(__name__)

s3 = boto3.client('s3')

def upload_to_s3(bucket, key, data):
    """
    Sube datos JSON a S3 en formato JSON Lines (JSONL)
    Cada objeto se guarda en una línea separada para mejor compatibilidad con Glue/Athena
    
    Args:
        bucket (str): Nombre del bucket S3
        key (str): Key del objeto en S3
        data (list): Lista de objetos a subir
    """
    try:
        # Convertir a JSON Lines (cada objeto en una línea)
        jsonl_data = '\n'.join([json.dumps(item, ensure_ascii=False) for item in data])
        
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=jsonl_data.encode('utf-8'),
            ContentType='application/json',
            ServerSideEncryption='AES256'
        )
        
        logger.info(f'Archivo subido exitosamente a s3://{bucket}/{key}')
        
    except Exception as e:
        logger.error(f'Error subiendo a S3: {str(e)}')
        raise
