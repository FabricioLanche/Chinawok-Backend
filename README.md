# 🥡 ChinaWok Backend

Backend del sistema de pedidos de ChinaWok implementado con AWS Lambda, DynamoDB y Step Functions.

## 📁 Estructura del Proyecto

```
.
├── DataGenerator/              # 🔧 Scripts locales para generar datos de prueba
│   ├── DataGenerator.py        # Genera datos sintéticos
│   ├── DataPoblator.py         # Puebla DynamoDB con los datos
│   └── data_generator_utils/   # Utilidades del generador
├── Layers/                     # 📦 Lambda Layer compartido
│   └── python/
│       ├── libs/               # Dependencias de terceros
│       └── utils/              # Utilidades compartidas (JWT, DynamoDB, etc.)
├── Microservicios/             # 🚀 Microservicios Lambda
│   ├── Usuarios/               # Autenticación y gestión de usuarios
│   ├── Locales/                # CRUD de locales + Analítica
│   ├── Empleados/              # Gestión de empleados y reseñas
│   └── Pedidos/                # CRUD de pedidos + Workflow (Step Functions)
├── .env.example                # Plantilla de variables de entorno
├── serverless-compose.yml      # Orquestación de microservicios
└── setup_and_deploy.sh         # Script de despliegue automatizado
```

## 🚀 Despliegue Rápido

1. **Configurar variables de entorno:**
   ```bash
   cp .env.example .env
   nano .env  # Editar con tus valores
   ```

2. **Ejecutar script de despliegue:**
   ```bash
   bash setup_and_deploy.sh
   ```

3. **Opciones disponibles:**
   - `1)` Despliegue completo (genera datos + despliega microservicios)
   - `2)` Solo generar y poblar datos
   - `3)` Solo desplegar microservicios
   - `4)` Eliminar todos los recursos

## 📊 Generador de Datos

El generador de datos (`DataGenerator/`) es un script local que:

1. **Genera datos sintéticos** realistas de una colección preensamblada
2. **Guarda los datos** en archivos JSON (`dynamodb_data/`)
3. **Puebla DynamoDB** con los datos generados

### Uso manual:

```bash
cd DataGenerator
pip install -r requirements.txt
python3 DataGenerator.py  # Genera datos
python3 DataPoblator.py   # Puebla DynamoDB
```

## 🏗️ Arquitectura

### Microservicios

- **Usuarios**: Autenticación JWT, CRUD de usuarios
- **Locales**: CRUD de locales + Analítica con Athena
- **Empleados**: Gestión de empleados y reseñas
- **Pedidos**: CRUD completo + Workflow con Step Functions

### Lambda Layer Compartido

Contiene utilidades compartidas:
- `jwt_utils.py`: Generación y validación de tokens JWT
- `dynamodb_helper.py`: Operaciones comunes de DynamoDB
- `json_encoder.py`: Serialización de Decimal
- `s3_client.py`, `logger.py`, etc.

## 🔧 Desarrollo

### Requisitos

- Node.js 18+ (para Serverless Framework)
- Python 3.12+
- AWS CLI configurado
- Credenciales AWS en `~/.aws/credentials`

### Comandos útiles

```bash
# Desplegar todo
serverless deploy

# Desplegar un servicio específico
serverless deploy --service=usuarios

# Ver logs de una función
serverless logs -f nombreFuncion --tail

# Eliminar todo
serverless remove
```

## 📝 Variables de Entorno

Ver `.env.example` para la lista completa. Principales:

- `AWS_ACCOUNT_ID`: Tu AWS Account ID
- `TABLE_*`: Nombres de tablas DynamoDB
- `JWT_SECRET`: Clave secreta para JWT
- `ADMIN_*`: Credenciales del usuario administrador

## 🔐 Seguridad

- JWT para autenticación
- Lambda Authorizer para proteger endpoints
- Roles IAM con permisos mínimos necesarios
- Validación de schemas en todas las operaciones

## 📄 Licencia

MIT