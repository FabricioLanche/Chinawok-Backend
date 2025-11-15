import boto3, json, uuid, os
from decimal import Decimal
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
tabla_resenas = dynamodb.Table(os.environ['TABLE_RESENAS'])
tabla_locales = dynamodb.Table(os.environ['TABLE_LOCALES'])
tabla_pedidos = dynamodb.Table(os.environ['TABLE_PEDIDOS'])

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    body = json.loads(event['body'])
    required = ['local_id', 'pedido_id', 'calificacion']

    for field in required:
        if field not in body:
            return {'statusCode': 400, 'body': json.dumps({'error': f"Falta el campo {field}"})}

    local_id = body['local_id']
    pedido_id = body['pedido_id']

    # Validar que el local existe
    try:
        response_local = tabla_locales.get_item(Key={'local_id': local_id})
        if 'Item' not in response_local:
            return {'statusCode': 404, 'body': json.dumps({'error': f"Local {local_id} no encontrado"})}
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': f"Error al validar local: {str(e)}"})}

    # Validar que el pedido existe y obtener empleados del historial
    try:
        response_pedido = tabla_pedidos.get_item(Key={'local_id': local_id, 'pedido_id': pedido_id})
        if 'Item' not in response_pedido:
            return {'statusCode': 404, 'body': json.dumps({'error': f"Pedido {pedido_id} no encontrado"})}
        
        pedido = response_pedido['Item']
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': f"Error al obtener pedido: {str(e)}"})}

    # Extraer DNIs de empleados del historial de estados
    historial_estados = pedido.get('historial_estados', [])
    cocinero_dni = None
    despachador_dni = None
    repartidor_dni = None

    for estado in historial_estados:
        empleado = estado.get('empleado')
        if empleado:
            rol = empleado.get('rol', '').lower()
            dni = empleado.get('dni')
            if dni:
                if rol == 'cocinero' and not cocinero_dni:
                    cocinero_dni = dni
                elif rol == 'despachador' and not despachador_dni:
                    despachador_dni = dni
                elif rol == 'repartidor' and not repartidor_dni:
                    repartidor_dni = dni

    # Validar que se encontraron todos los empleados necesarios
    if not cocinero_dni or not despachador_dni or not repartidor_dni:
        return {
            'statusCode': 400, 
            'body': json.dumps({
                'error': 'No se encontraron todos los empleados requeridos en el historial del pedido',
                'encontrados': {
                    'cocinero_dni': cocinero_dni,
                    'despachador_dni': despachador_dni,
                    'repartidor_dni': repartidor_dni
                }
            })
        }

    # Convertir calificacion a Decimal para DynamoDB
    calificacion = Decimal(str(body['calificacion']))

    # Validar rango de calificación
    if not (Decimal('0') <= calificacion <= Decimal('5')):
        return {'statusCode': 400, 'body': json.dumps({'error': 'La calificación debe estar entre 0 y 5'})}

    # Crear el item de reseña único
    resena_id = str(uuid.uuid4())
    item = {
        'local_id': local_id,
        'resena_id': resena_id,
        'pedido_id': pedido_id,
        'cocinero_dni': cocinero_dni,
        'despachador_dni': despachador_dni,
        'repartidor_dni': repartidor_dni,
        'resena': body.get('resena', ''),
        'calificacion': calificacion
    }

    try:
        tabla_resenas.put_item(Item=item)
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': f"Error al registrar reseña: {str(e)}"})}

    return {
        'statusCode': 201,
        'body': json.dumps({'message': 'Reseña registrada exitosamente', 'resena': item}, cls=DecimalEncoder)
    }
