"""
Utilidades compartidas para todos los microservicios de ChinaWok
"""

# Importar los principales módulos para facilitar su uso
from .logger import get_logger
from .json_encoder import json_dumps, DecimalEncoder
from .dynamodb_client import get_dynamodb_resource, get_table_data
from .s3_client import upload_to_s3, download_from_s3
from .athena_client import AthenaQueryExecutor

__all__ = [
    'get_logger',
    'json_dumps',
    'DecimalEncoder',
    'get_dynamodb_resource',
    'get_table_data',
    'upload_to_s3',
    'download_from_s3',
    'AthenaQueryExecutor',
]
