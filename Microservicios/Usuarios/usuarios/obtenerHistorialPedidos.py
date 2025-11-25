import json
import boto3
import os
from decimal import Decimal
from utils.cors_utils import get_cors_headers

# Tablas DynamoDB
dynamodb = boto3.resource('dynamodb')

usuarios_table_name = os.environ.get('TABLE_USUARIOS', 'ChinaWok-Usuarios')
pedidos_table_name = os.environ.get('TABLE_PEDIDOS', 'ChinaWok-Pedidos')

usuarios_table = dynamodb.Table(usuarios_table_name)
pedidos_table = dynamodb.Table(pedidos_table_name)


def decimal_to_float(obj):
    """Convierte Decimal a float/int para JSON"""
    if isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj


def lambda_handler(event, context):
    """
    Lambda para obtener el historial de pedidos del usuario autenticado
    Usa JWT del authorizer para identificar al usuario
    
    Parámetros query opcionales:
    - detallado=true: Expande los detalles completos de cada pedido
    - limite=N: Limita el número de pedidos retornados (default: todos)
    """
    try:
        # Obtener usuario autenticado del authorizer (JWT)
        authorizer = event.get("requestContext", {}).get("authorizer", {})
        correo_autenticado = authorizer.get("correo")
        
        if not correo_autenticado:
            return {
                'statusCode': 401,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'No autenticado', 'message': 'Token JWT requerido'})
            }
        
        # Obtener parámetros opcionales
        query_params = event.get('queryStringParameters') or {}
        detallado = query_params.get('detallado', 'false').lower() == 'true'
        limite = int(query_params.get('limite', 0)) if query_params.get('limite') else None
        
        # Obtener usuario de DynamoDB
        response = usuarios_table.get_item(Key={'correo': correo_autenticado})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Usuario no encontrado'})
            }
        
        usuario = response['Item']
        historial_pedidos = usuario.get('historial_pedidos', [])
        
        # Aplicar límite si se especificó
        if limite and limite > 0:
            historial_pedidos = historial_pedidos[-limite:]  # Últimos N pedidos
        
        # Si no se pide detallado, solo retornar los IDs
        if not detallado:
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': 'Historial de pedidos obtenido',
                    'correo': correo_autenticado,
                    'total_pedidos': len(historial_pedidos),
                    'pedidos_ids': historial_pedidos
                })
            }
        
        # Modo detallado: obtener información completa de cada pedido
        pedidos_detallados = []
        pedidos_no_encontrados = []
        
        for pedido_id in historial_pedidos:
            try:
                # Nota: necesitamos el local_id para hacer get_item
                # Si no lo tenemos, debemos usar scan con filter
                # Por eficiencia, usamos query en el índice o scan con filter
                
                # Scan buscando el pedido_id específico
                scan_response = pedidos_table.scan(
                    FilterExpression='pedido_id = :pid',
                    ExpressionAttributeValues={':pid': pedido_id},
                    Limit=1
                )
                
                if scan_response.get('Items'):
                    pedido = scan_response['Items'][0]
                    # Convertir Decimal a tipos JSON serializables
                    pedido = decimal_to_float(pedido)
                    pedidos_detallados.append(pedido)
                else:
                    pedidos_no_encontrados.append(pedido_id)
                    
            except Exception as e:
                print(f"Error obteniendo pedido {pedido_id}: {str(e)}")
                pedidos_no_encontrados.append(pedido_id)
        
        response_body = {
            'message': 'Historial de pedidos detallado obtenido',
            'correo': correo_autenticado,
            'total_pedidos': len(historial_pedidos),
            'pedidos': pedidos_detallados
        }
        
        if pedidos_no_encontrados:
            response_body['pedidos_no_encontrados'] = pedidos_no_encontrados
            response_body['warning'] = f'{len(pedidos_no_encontrados)} pedidos no encontrados (posiblemente eliminados)'
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(response_body, default=str)
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'error': 'Error interno del servidor',
                'message': str(e)
            })
        }
