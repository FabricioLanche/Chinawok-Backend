import json
import boto3
import os
from datetime import datetime, timezone
from utils.dynamodb_helper import (
    obtener_pedido,
    marcar_empleado_libre,
    resetear_pedido_a_inicial
)

def lambda_handler(event, context):
    """Lambda para liberar todos los empleados asignados a un pedido"""
    print(f'Liberando empleados del pedido: {json.dumps(event)}')
    
    local_id = event.get('local_id')
    pedido_id = event.get('pedido_id')
    motivo = event.get('motivo', 'error_workflow')
    resetear_estado = event.get('resetear_estado', True)
    
    if not local_id or not pedido_id:
        print('Faltan parámetros, no se puede liberar empleados')
        return {'liberados': 0}
    
    try:
        # Obtener el pedido para ver qué empleados están asignados
        pedido = obtener_pedido(local_id, pedido_id)
        historial = pedido.get('historial_estados', [])
        
        empleados_liberados = []
        
        # Buscar en el historial los empleados que estaban activos
        for estado in historial:
            if estado.get('activo') and estado.get('empleado'):
                empleado_dni = estado['empleado'].get('dni')
                empleado_rol = estado['empleado'].get('rol')
                
                try:
                    marcar_empleado_libre(local_id, empleado_dni)
                    empleados_liberados.append({
                        'dni': empleado_dni,
                        'rol': empleado_rol
                    })
                    print(f'Empleado {empleado_rol} {empleado_dni} liberado por {motivo}')
                except Exception as e:
                    print(f'Error liberando empleado {empleado_dni}: {str(e)}')
        
        #  --- NUEVO: marcar pedido como "cancelado" y cerrar historial activo ---
        # Solo si el pedido existe
        try:
            pedidos_table_name = os.environ.get('TABLE_PEDIDOS', 'ChinaWok-Pedidos')
            dynamodb = boto3.resource('dynamodb')
            pedidos_table = dynamodb.Table(pedidos_table_name)

            # Cerrar entradas activas del historial (activo -> False) y asegurar hora_fin
            ahora_iso = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
            nuevo_historial = []
            for estado in historial:
                estado_n = dict(estado)
                if estado_n.get('activo'):
                    estado_n['activo'] = False
                    # Si no tiene hora_fin, poner ahora
                    if not estado_n.get('hora_fin'):
                        estado_n['hora_fin'] = ahora_iso
                nuevo_historial.append(estado_n)

            # Actualizar el pedido: estado='cancelado' y historial_estados actualizado
            update_expr = "SET #estado = :estado, historial_estados = :hist"
            pedidos_table.update_item(
                Key={'local_id': local_id, 'pedido_id': pedido_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames={'#estado': 'estado'},
                ExpressionAttributeValues={
                    ':estado': 'cancelado',
                    ':hist': nuevo_historial
                }
            )
            print(f"Pedido {pedido_id} marcado como 'cancelado' y historial cerrado.")
        except Exception as e:
            print(f"Error actualizando estado del pedido a 'cancelado': {str(e)}")
        # ----------------------------------------------------------------------

        # Resetear el pedido a estado inicial si se solicita (mantener comportamiento previo)
        if resetear_estado:
            try:
                resetear_pedido_a_inicial(local_id, pedido_id)
                print(f'Pedido {pedido_id} reseteado a estado "procesando"')
            except Exception as e:
                print(f'Error reseteando estado del pedido: {str(e)}')
        
        print(f'Total empleados liberados: {len(empleados_liberados)}')
        
        return {
            'liberados': len(empleados_liberados),
            'empleados': empleados_liberados,
            'pedido_cancelado': True,
            'pedido_reseteado': resetear_estado,
            'motivo': motivo
        }
        
    except Exception as e:
        print(f'Error al liberar empleados: {str(e)}')
        return {'liberados': 0, 'error': str(e)}
