"""
Lambda Authorizer para validar tokens JWT en API Gateway
"""
import json
import logging
from utils.jwt_utils import validar_token
from utils.jwt_utils import _mask_token

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda Authorizer con validación de JWT
    
    Este authorizer valida el token JWT y retorna una política IAM
    que permite o deniega el acceso al endpoint solicitado.
    """
    token = event.get("authorizationToken", "") or ""
    
    # Log del token recibido (enmascarado) para debugging
    try:
        masked = _mask_token(token if isinstance(token, str) else (token.decode("utf-8") if isinstance(token, bytes) else None))
    except Exception:
        masked = "<no-mask-possible>"
    logger.info(f"Authorizer: authorizationToken recibido (enmascarado)={masked}")

    # Asegurarse de trabajar con str
    if isinstance(token, bytes):
        try:
            token = token.decode("utf-8")
        except Exception:
            logger.info("Authorization token no pudo decodificarse")
            raise Exception("Unauthorized")
    
    # Extraer token si viene con prefijo "Bearer "
    if isinstance(token, str) and token.lower().startswith("bearer "):
        token = token.split(" ", 1)[1].strip()
    
    # Validar token usando la utilidad compartida
    resultado = validar_token(token)
    
    if not resultado.get("valido"):
        # Log con detalle para debugging interno (no devolver al cliente)
        logger.info(f"Authorizer: token inválido: {resultado.get('error')} (token enmascarado={masked})")
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
