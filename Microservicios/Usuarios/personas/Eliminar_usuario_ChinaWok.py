import json
import boto3
import os
from personas.utils.utils import verificar_rol

TABLE_USUARIOS_NAME = os.getenv("TABLE_USUARIOS", "ChinaWok-Usuarios")

dynamodb = boto3.resource("dynamodb")
usuarios_table = dynamodb.Table(TABLE_USUARIOS_NAME)


def lambda_handler(event, context):
    # Obtener usuario autenticado
    authorizer = event.get("requestContext", {}).get("authorizer", {})
    usuario_autenticado = {
        "correo": authorizer.get("correo"),
        "role": authorizer.get("role")
    }
    
    body = {}
    if isinstance(event, dict) and "body" in event:
        raw_body = event.get("body")
        if isinstance(raw_body, str):
            if raw_body:
                body = json.loads(raw_body)
            else:
                body = {}
        elif isinstance(raw_body, dict):
            body = raw_body
    elif isinstance(event, dict):
        body = event
    elif isinstance(event, str):
        body = json.loads(event)

    correo_a_eliminar = body.get("correo")
    if not correo_a_eliminar:
        return {
            "statusCode": 400,
            "body": json.dumps({"message": "correo es obligatorio"})
        }

    # Obtener información del usuario a eliminar
    resp = usuarios_table.get_item(Key={"correo": correo_a_eliminar})
    if "Item" not in resp:
        return {
            "statusCode": 404,
            "body": json.dumps({"message": "Usuario no encontrado"})
        }
    
    usuario_a_eliminar = resp["Item"]
    role_a_eliminar = usuario_a_eliminar.get("role", "Cliente")
    
    # 🔒 Lógica de permisos
    es_admin = verificar_rol(usuario_autenticado, ["Admin"])
    es_gerente = verificar_rol(usuario_autenticado, ["Gerente"])
    es_mismo_usuario = usuario_autenticado["correo"] == correo_a_eliminar
    
    # Todos pueden eliminarse a sí mismos
    if es_mismo_usuario:
        usuarios_table.delete_item(Key={"correo": correo_a_eliminar})
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Usuario eliminado correctamente"})
        }
    
    # Gerente puede eliminar solo Clientes
    if es_gerente and role_a_eliminar == "Cliente":
        usuarios_table.delete_item(Key={"correo": correo_a_eliminar})
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Usuario eliminado correctamente"})
        }
    
    # Admin puede eliminar a todos (Clientes y Gerentes)
    if es_admin:
        usuarios_table.delete_item(Key={"correo": correo_a_eliminar})
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Usuario eliminado correctamente"})
        }
    
    # Si no cumple ninguna condición
    return {
        "statusCode": 403,
        "body": json.dumps({"message": "No tienes permiso para eliminar este usuario"})
    }
