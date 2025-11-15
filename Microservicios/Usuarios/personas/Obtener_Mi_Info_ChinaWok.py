import json
import boto3
import os
from personas.utils.utils import verificar_rol

TABLE_USUARIOS_NAME = os.getenv("TABLE_USUARIOS", "ChinaWok-Usuarios")

dynamodb = boto3.resource("dynamodb")
usuarios_table = dynamodb.Table(TABLE_USUARIOS_NAME)


def lambda_handler(event, context):
    print("Event recibido:", json.dumps(event))
    
    # Obtener usuario autenticado
    authorizer = event.get("requestContext", {}).get("authorizer", {})
    usuario_autenticado = {
        "correo": authorizer.get("correo"),
        "role": authorizer.get("role")
    }
    
    print("Usuario autenticado:", json.dumps(usuario_autenticado))
    
    # Obtener correo del query parameter
    correo_solicitado = None
    
    if event.get("queryStringParameters"):
        correo_solicitado = event["queryStringParameters"].get("correo")
    
    # Si no se proporciona correo, retornar info del usuario autenticado
    if not correo_solicitado:
        correo_solicitado = usuario_autenticado["correo"]
    
    print("Correo solicitado:", correo_solicitado)
    
    # 🔒 Verificar permisos ANTES de consultar
    es_admin = verificar_rol(usuario_autenticado, ["Admin"])
    es_gerente = verificar_rol(usuario_autenticado, ["Gerente"])
    es_mismo_usuario = usuario_autenticado["correo"] == correo_solicitado
    
    print(f"Permisos: Admin={es_admin}, Gerente={es_gerente}, MismoUsuario={es_mismo_usuario}")
    
    # Admin ve a todos
    if es_admin:
        print("Acceso concedido: Admin")
        pass
    # Gerente ve Clientes y a sí mismo
    elif es_gerente:
        print("Verificando permisos de Gerente...")
        if not es_mismo_usuario:
            # Verificar que el usuario solicitado sea Cliente
            try:
                resp_temp = usuarios_table.get_item(Key={"correo": correo_solicitado})
                if "Item" not in resp_temp:
                    return {
                        "statusCode": 404,
                        "body": json.dumps({"message": "Usuario no encontrado"})
                    }
                role_solicitado = resp_temp["Item"].get("role", "Cliente")
                print(f"Rol del usuario solicitado: {role_solicitado}")
                if role_solicitado != "Cliente":
                    return {
                        "statusCode": 403,
                        "body": json.dumps({"message": "Gerente solo puede ver información de Clientes"})
                    }
            except Exception as e:
                print(f"Error al verificar usuario: {str(e)}")
                return {
                    "statusCode": 500,
                    "body": json.dumps({"message": f"Error al verificar usuario: {str(e)}"})
                }
    # Cliente solo ve su propia información
    elif not es_mismo_usuario:
        print("Acceso denegado: Cliente intenta ver info de otro")
        return {
            "statusCode": 403,
            "body": json.dumps({"message": "Solo puedes ver tu propia información"})
        }

    # Obtener información del usuario
    try:
        resp = usuarios_table.get_item(Key={"correo": correo_solicitado})
        
        if "Item" not in resp:
            return {
                "statusCode": 404,
                "body": json.dumps({"message": "Usuario no encontrado"})
            }
        
        usuario = resp["Item"]
        
        # Remover contraseña de la respuesta
        if "contrasena" in usuario:
            del usuario["contrasena"]
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Usuario encontrado",
                "usuario": usuario
            }, default=str)
        }
    except Exception as e:
        print(f"Error al buscar usuario: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": f"Error al buscar usuario: {str(e)}"})
        }
