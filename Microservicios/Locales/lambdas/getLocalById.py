import os, json, boto3, logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_LOCALES', 'ChinaWok-Locales'))

def lambda_handler(event, context):
    try:
        local_id = event.get('pathParameters', {}).get('local_id')
        
        if not local_id:
            return _resp(400, {"message": "Falta el parámetro 'local_id' en el path"})
        
        logger.info(f"Buscando local con local_id: {local_id}")
        logger.info(f"Tabla: {table.table_name}")
        
        # Log del esquema de la tabla
        logger.info(f"Key schema: {table.key_schema}")
        
        resp = table.get_item(Key={"local_id": local_id})
        item = resp.get("Item")
        
        if not item:
            return _resp(404, {"message": "Local no encontrado"})
        
        return _resp(200, item)
        
    except Exception as e:
        logger.exception(f"Error al obtener local: {str(e)}")
        return _resp(500, {"message": "Error al obtener el local", "error": str(e)})

def _resp(status, body):
    return {"statusCode": status, "headers": {"Content-Type":"application/json","Access-Control-Allow-Origin":"*"}, "body": json.dumps(body, ensure_ascii=False)}
