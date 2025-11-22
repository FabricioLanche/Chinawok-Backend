"""
Utilidades compartidas para todos los microservicios de ChinaWok
"""

# Importar los principales módulos para facilitar su uso
from .logger import get_logger
from .json_encoder import json_dumps, DecimalEncoder
from .dynamodb_client import get_dynamodb_resource, get_table_data
from .s3_client import upload_to_s3, list_s3_files, delete_old_versions
from .athena_client import AthenaQueryExecutor
from .jwt_utils import generar_token, validar_token, verificar_rol
from .authentication_utils import (
    obtener_usuario_autenticado,
    verificar_local_gerente,
    verificar_rol_solicitado,
    obtener_local_del_gerente,
    es_mismo_usuario,
    validar_acceso_usuario,
    validar_acceso_local,
    require_roles
)

# Helper para headers CORS
def get_cors_headers():
    """Retorna headers CORS estándar para todas las respuestas"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

__all__ = [
    # Logger
    'get_logger',
    # JSON
    'json_dumps',
    'DecimalEncoder',
    # DynamoDB
    'get_dynamodb_resource',
    'get_table_data',
    # S3
    'upload_to_s3',
    'list_s3_files',
    'delete_old_versions',
    # Athena
    'AthenaQueryExecutor',
    # JWT
    'generar_token',
    'validar_token',
    'verificar_rol',
    # Authentication
    'obtener_usuario_autenticado',
    'verificar_local_gerente',
    'verificar_rol_solicitado',
    'obtener_local_del_gerente',
    'es_mismo_usuario',
    'validar_acceso_usuario',
    'validar_acceso_local',
    'require_roles',
    # CORS
    'get_cors_headers',
]
