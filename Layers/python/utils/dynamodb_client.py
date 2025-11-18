import boto3
from decimal import Decimal
from ingesta.utils.logger import get_logger

logger = get_logger(__name__)

dynamodb = boto3.resource('dynamodb')

def decimal_to_float(obj):
    """Convierte Decimal a float para serialización JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def get_table_data(table_name):
    """
    Obtiene todos los datos de una tabla DynamoDB usando scan
    
    Args:
        table_name (str): Nombre de la tabla DynamoDB
        
    Returns:
        list: Lista de items de la tabla
    """
    table = dynamodb.Table(table_name)
    items = []
    
    try:
        # Scan inicial
        response = table.scan()
        items.extend(response.get('Items', []))
        
        # Paginación si hay más datos
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))
        
        # Convertir Decimal a float
        items = _convert_decimals(items)
        
        return items
        
    except Exception as e:
        logger.error(f'Error obteniendo datos de {table_name}: {str(e)}')
        raise

def _convert_decimals(obj):
    """Convierte recursivamente objetos Decimal a float"""
    if isinstance(obj, list):
        return [_convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: _convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj
