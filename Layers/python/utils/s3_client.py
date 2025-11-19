"""
Cliente de S3 para operaciones comunes
"""
import boto3
import json
from typing import List, Dict, Any
from decimal import Decimal


def get_s3_client():
    """
    Retorna un cliente de S3
    """
    return boto3.client('s3')


def convert_decimal_to_serializable(obj):
    """
    Convierte Decimal a float para que sea serializable en JSON
    """
    if isinstance(obj, list):
        return [convert_decimal_to_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimal_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        # Convertir Decimal a int si es entero, sino a float
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj


def upload_to_s3(bucket: str, key: str, data: List[Dict[str, Any]]) -> str:
    """
    Sube datos a S3 en formato JSON
    
    Args:
        bucket (str): Nombre del bucket S3 (SIN s3:// ni barras, ej: 'chinawok-data')
        key (str): Ruta completa del objeto en S3 (ej: 'data-ingestion/locales/20241119.json')
        data (List[Dict]): Datos a subir (lista de diccionarios)
        
    Returns:
        str: URI completa del archivo subido (s3://bucket/key)
        
    Raises:
        Exception: Si hay error al subir a S3
    """
    s3_client = get_s3_client()
    
    # Convertir Decimal a tipos serializables
    serializable_data = convert_decimal_to_serializable(data)
    
    # Convertir a JSON
    json_data = json.dumps(serializable_data, indent=2, default=str)
    
    # Subir a S3
    try:
        s3_client.put_object(
            Bucket=bucket,  # ← Debe ser solo el nombre (sin barras)
            Key=key,        # ← Puede tener barras (es el path)
            Body=json_data.encode('utf-8'),
            ContentType='application/json'
        )
        
        return f's3://{bucket}/{key}'
        
    except Exception as e:
        raise Exception(f'Error subiendo archivo a S3: {str(e)}')


def download_from_s3(bucket: str, key: str) -> Dict[str, Any]:
    """
    Descarga y parsea un archivo JSON desde S3
    
    Args:
        bucket (str): Nombre del bucket S3
        key (str): Ruta del objeto en S3
        
    Returns:
        Dict: Datos parseados desde JSON
    """
    s3_client = get_s3_client()
    
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        return json.loads(content)
        
    except Exception as e:
        raise Exception(f'Error descargando archivo de S3: {str(e)}')
