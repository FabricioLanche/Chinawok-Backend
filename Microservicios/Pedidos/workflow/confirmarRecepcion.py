import json
import boto3
import os
from utils.dynamodb_helper import (
    obtener_pedido,
    marcar_empleado_libre,
    finalizar_pedido,
    agregar_pedido_a_usuario
)
from utils.json_encoder import json_dumps

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
stepfunctions = boto3.client('stepfunctions', region_name='us-east-1')

def lambda_handler(event, context):
    """Lambda para procesar la confirmación del usuario y liberar empleados"""
    print(f'Procesando confirmación de recepción: {json.dumps(event)}')
    
    body = json.loads(event.get('body', '{}')) if isinstance(event.get('body'), str) else event
    
    local_id = body.get('local_id')
    pedido_id = body.get('pedido_id')
    confirmado = body.get('confirmado', True)
    repartidor_dni = body.get('repartidor_dni')  # opcional, si viene del frontend
    
    if not local_id or not pedido_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Faltan parámetros requeridos'})
        }
    
    try:
        # Obtener el pedido
        pedido = obtener_pedido(local_id, pedido_id)
        if not pedido:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Pedido no encontrado'})
            }
        
        usuario_correo = pedido.get('usuario_correo')
        historial = pedido.get('historial_estados', [])
        empleados_liberados = []

        # Liberar empleados activos del historial
        for estado in historial:
            if estado.get('activo') and estado.get('empleado'):
                empleado = estado['empleado']
                empleado_dni = empleado.get('dni')
                empleado_rol = empleado.get('rol', '').lower()
                
                try:
                    marcar_empleado_libre(local_id, empleado_dni)
                    empleados_liberados.append({'dni': empleado_dni, 'rol': empleado_rol})
                    print(f'Empleado {empleado_rol} {empleado_dni} liberado')
                except Exception as e:
                    print(f'Error liberando empleado {empleado_dni}: {str(e)}')
        
        # Liberar repartidor específico si no fue liberado arriba
        if repartidor_dni and not any(e['dni'] == repartidor_dni for e in empleados_liberados):
            try:
                marcar_empleado_libre(local_id, repartidor_dni)
                empleados_liberados.append({'dni': repartidor_dni, 'rol': 'repartidor'})
                print(f'Repartidor adicional {repartidor_dni} liberado')
            except Exception as e:
                print(f'Error liberando repartidor adicional {repartidor_dni}: {str(e)}')

        if empleados_liberados:
            print(f'Total empleados liberados: {len(empleados_liberados)}')
        else:
            print('Advertencia: No se encontraron empleados activos para liberar')
        
        # Finalizar pedido
        pedido_actualizado = finalizar_pedido(local_id, pedido_id)
        
        # Agregar pedido al historial del usuario
        if usuario_correo:
            try:
                agregar_pedido_a_usuario(usuario_correo, pedido_id)
            except Exception as e:
                print(f'Error agregando pedido al historial del usuario: {str(e)}')

        # Manejo de Step Functions
        table = dynamodb.Table(os.environ['TABLE_PEDIDOS'])
        task_token = pedido.get('task_token')
        if task_token:
            stepfunctions.send_task_success(
                taskToken=task_token,
                output=json.dumps({
                    'confirmado': confirmado,
                    'tipo': 'manual',
                    'mensaje': 'Usuario confirmó la recepción del pedido',
                    'empleados_liberados': empleados_liberados
                })
            )
            table.update_item(
                Key={'local_id': local_id, 'pedido_id': pedido_id},
                UpdateExpression='REMOVE task_token, esperando_confirmacion'
            )
        
        result = {
            'message': 'Confirmación procesada y pedido completado',
            'pedido_id': pedido_id,
            'local_id': local_id,
            'estado': 'recibido',
            'empleados_liberados': empleados_liberados,
            'historial_estados': pedido_actualizado.get('historial_estados', historial),
            'pedido_completo': pedido_actualizado
        }
        
        return {
            'statusCode': 200,
            'body': json_dumps(result),
            'headers': {'Content-Type': 'application/json'}
        }
    
    except Exception as e:
        print(f'Error al procesar confirmación: {str(e)}')
        import traceback
        print(f'Traceback: {traceback.format_exc()}')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)}),
            'headers': {'Content-Type': 'application/json'}
        }
