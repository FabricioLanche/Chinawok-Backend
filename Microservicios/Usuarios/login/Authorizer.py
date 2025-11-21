"""
Lambda Authorizer para validar tokens JWT en API Gateway
"""
import json
from utils.jwt_utils import validar_token


def lambda_handler(event, context):
    """
    Lambda Authorizer con validación de JWT
    
    Este authorizer valida el token JWT y retorna una política IAM
    que permite o deniega el acceso al endpoint solicitado.
    """
    token = event.get("authorizationToken", "")
    
    # Extraer token si viene con prefijo "Bearer "
    if token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1].strip()
    
    # Validar token usando la utilidad compartida
    resultado = validar_token(token)
    
    if not resultado.get("valido"):
        # Token inválido o expirado
        raise Exception("Unauthorized")
    
    # Token válido - Retornar política IAM con contexto del usuario
    return {
        "principalId": resultado["correo"],
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "execute-api:Invoke",
                    "Effect": "Allow",
                    "Resource": event["methodArn"]
                }
            ]
        },
        "context": {
            "correo": resultado["correo"],
            "role": resultado["role"],
            "nombre": resultado.get("nombre", "")
        }
    }
