import os, json, boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_LOCALES', 'ChinaWok-Locales'))

def lambda_handler(event, context):
    try:
        # Realizamos un scan de los locales (página completa)
        resp = table.scan()
        items = resp.get("Items", [])
        return _resp(200, items)
    except Exception as e:
        return _resp(500, {"message": "Error al listar los locales", "error": str(e)})

def _resp(status, body):
    return {"statusCode": status, "headers": {"Content-Type":"application/json","Access-Control-Allow-Origin":"*"}, "body": json.dumps(body, ensure_ascii=False)}
