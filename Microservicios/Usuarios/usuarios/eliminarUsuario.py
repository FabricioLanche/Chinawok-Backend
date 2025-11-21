import json
import boto3
import os
from utils.authentication_utils import obtener_usuario_autenticado, verificar_rol, verificar_rol_solicitado

TABLE_USUARIOS_NAME = os.getenv("TABLE_USUARIOS", "ChinaWok-Usuarios")

dynamodb = boto3.resource("dynamodb")
usuarios_table = dynamodb.Table(TABLE_USUARIOS_NAME)


def lambda_handler(event, context):
    # Obtener usuario autenticado (centralizado)
    usuario_autenticado = obtener_usuario_autenticado(event)

     # Determinar correo a eliminar: preferir path /usuarios/{correo} o /usuarios/me
     path_params = event.get("pathParameters") or {}
     path_correo = path_params.get("correo")
     if path_correo:
         if path_correo == "me":
             correo_a_eliminar = usuario_autenticado["correo"]
         else:
             correo_a_eliminar = path_correo
     else:
         # Fallback antiguo por compatibilidad
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
         return {"statusCode": 400, "body": json.dumps({"message": "correo es obligatorio (path /usuarios/{correo} o body)"})}

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
    if es_gerente:
        # Validar que el objetivo sea Cliente antes de eliminar
        if role_a_eliminar == "Cliente":
            usuarios_table.delete_item(Key={"correo": correo_a_eliminar})
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Usuario eliminado correctamente"})
            }
        else:
            return {
                "statusCode": 403,
                "body": json.dumps({"message": "Gerente solo puede eliminar Clientes"})
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
