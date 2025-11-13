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
    
    # 🔒 Solo Admin puede listar todos los usuarios
    if not verificar_rol(usuario_autenticado, ["Admin"]):
        return {
            "statusCode": 403,
            "body": json.dumps({"message": "Acceso denegado. Solo Admin puede listar usuarios."})
        }
    
    try:
        response = usuarios_table.scan()
        usuarios = response.get("Items", [])
        
        # Remover contraseñas de la respuesta
        for usuario in usuarios:
            if "contrasena" in usuario:
                del usuario["contrasena"]
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Usuarios obtenidos correctamente",
                "usuarios": usuarios
            }, default=str)
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Error al listar usuarios: {str(e)}"})
        }
