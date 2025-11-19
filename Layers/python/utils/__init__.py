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
    'download_from_s3',
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
]
