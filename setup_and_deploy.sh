#!/bin/bash

# Aumentar memoria de Node.js para Serverless Framework
export NODE_OPTIONS="--max-old-space-size=4096"

# Colores para los logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
log_success() { echo -e "${GREEN}[$(date +'%H:%M:%S')] ✅ $1${NC}"; }
log_error() { echo -e "${RED}[$(date +'%H:%M:%S')] ❌ $1${NC}"; }
log_warning() { echo -e "${YELLOW}[$(date +'%H:%M:%S')] ⚠️  $1${NC}"; }
log_info() { echo -e "${CYAN}[$(date +'%H:%M:%S')] ℹ️  $1${NC}"; }

# Banner
echo ""
echo "═════════════════════════════════════════════════════════════"
echo "         🥡 CHINAWOK BACKEND - DEPLOY MAESTRO 🥡           "
echo "═════════════════════════════════════════════════════════════"
echo ""

# Verificar archivo .env
if [ ! -f .env ]; then
    log_error "No se encontró el archivo .env"
    log_info "Copia .env.example a .env y configúralo:"
    log_info "  cp .env.example .env"
    log_info "  nano .env"
    exit 1
fi

log_success "Archivo .env encontrado"

# Verificar e instalar Serverless Framework
log "Verificando Serverless Framework..."
if ! command -v serverless &> /dev/null; then
    log_warning "Serverless Framework no está instalado"
    log "Instalando Serverless Framework globalmente..."
    
    # Verificar si npm está instalado
    if ! command -v npm &> /dev/null; then
        log_error "npm no está instalado. Instálalo primero:"
        log_error "  sudo apt update && sudo apt install -y nodejs npm"
        exit 1
    fi
    
    # Instalar serverless
    sudo npm install -g serverless
    
    if [ $? -eq 0 ]; then
        log_success "Serverless Framework instalado correctamente"
    else
        log_error "Error al instalar Serverless Framework"
        exit 1
    fi
else
    log_success "Serverless Framework encontrado: $(serverless --version | head -n1)"
fi

# Verificar credenciales AWS
log "Verificando credenciales AWS..."

if [ -f ~/.aws/credentials ]; then
    log_success "Archivo de credenciales AWS encontrado: ~/.aws/credentials"
    
    # Verificar si el perfil default existe
    if grep -q "\[default\]" ~/.aws/credentials; then
        log_success "Perfil [default] encontrado"
    else
        log_warning "Perfil [default] no encontrado. Usando credenciales del entorno."
    fi
else
    log_warning "Archivo ~/.aws/credentials no encontrado"
    log_warning "Buscando credenciales en variables de entorno..."
    
    if [ -n "$AWS_ACCESS_KEY_ID" ] && [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
        log_success "Credenciales AWS encontradas en variables de entorno"
    else
        log_error "No se encontraron credenciales de AWS"
        log_error "Por favor, configura tus credenciales en ~/.aws/credentials o en variables de entorno"
        exit 1
    fi
fi

# Verificar conectividad con AWS
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "No se pudo conectar con AWS. Verifica tus credenciales."
    exit 1
fi
log_success "Credenciales AWS verificadas"

# Función para construir Lambda Layer
build_layer() {
    log "🔧 Construyendo Lambda Layer compartido..."
    
    cd Layers || exit 1
    
    # Limpiar build anterior completamente
    log "🗑️  Limpiando estructura anterior del layer..."
    rm -rf python/lib
    rm -rf python/libs
    rm -rf python-dependencies
    rm -rf .serverless
    
    # Crear estructura correcta para Lambda Layer
    mkdir -p python/lib/python3.12/site-packages
    
    # IMPORTANTE: Asegurar que utils existe antes de continuar
    if [ ! -d "python/utils" ]; then
        log_error "❌ ERROR: python/utils/ no existe"
        exit 1
    fi
    
    # Instalar dependencias de terceros
    log "📦 Instalando dependencias de terceros..."
    pip install -r requirements.txt \
        -t python/lib/python3.12/site-packages \
        --quiet \
        --upgrade \
        --no-cache-dir
    
    if [ $? -ne 0 ]; then
        log_error "Error al instalar dependencias del layer"
        exit 1
    fi
    
    log_success "✅ Dependencias instaladas en python/lib/python3.12/site-packages/"
    
    # Verificar estructura final
    log "🔍 Verificando estructura del layer..."
    
    # Verificar que utils tiene archivos
    utils_files=$(find python/utils -type f -name "*.py" | wc -l)
    log_info "   📂 python/utils/ contiene $utils_files archivos .py"
    
    if [ "$utils_files" -eq 0 ]; then
        log_error "❌ ERROR: python/utils/ no contiene archivos .py"
        exit 1
    fi
    
    # Listar archivos de utils para debug
    log_info "   📋 Archivos en python/utils/:"
    ls -1 python/utils/*.py | while read file; do
        log_info "      - $(basename $file)"
    done
    
    # Verificar PyJWT
    if [ -d "python/lib/python3.12/site-packages/jwt" ]; then
        log_info "   ✅ PyJWT instalado correctamente"
    else
        log_warning "   ⚠️  PyJWT NO se instaló correctamente"
    fi
    
    cd ..
    log_success "Lambda Layer construido correctamente"
}

# Función para generar y poblar datos
populate_data() {
    log ""
    log "═══════════════════════════════════════════════════════════"
    log "📊 Generación y población de datos"
    log "═══════════════════════════════════════════════════════════"
    
    cd DataGenerator || exit 1
    
    # Instalar dependencias de Python del DataGenerator
    log "📦 Instalando dependencias de DataGenerator..."
    if [ -f requirements.txt ]; then
        pip install -r requirements.txt --quiet
        
        if [ $? -eq 0 ]; then
            log_success "Dependencias de DataGenerator instaladas correctamente"
        else
            log_error "Error al instalar dependencias de DataGenerator"
            cd ..
            exit 1
        fi
    else
        log_error "Archivo requirements.txt no encontrado en DataGenerator/"
        cd ..
        exit 1
    fi
    
    # Verificar existencia de datos generados
    log "🔍 Verificando existencia de datos generados..."
    
    if [ -d "dynamodb_data" ] && [ "$(ls -A dynamodb_data)" ]; then
        log_warning "La carpeta dynamodb_data ya existe y contiene archivos"
        read -p "¿Deseas regenerar los datos? (s/n): " respuesta
        
        if [ "$respuesta" = "s" ] || [ "$respuesta" = "S" ]; then
            log "🗑️  Eliminando datos anteriores..."
            rm -rf dynamodb_data
            log_success "Datos anteriores eliminados"
        else
            log "⏭️  Saltando generación de datos. Usando datos existentes."
        fi
    fi
    
    # Generar datos si no existen
    if [ ! -d "dynamodb_data" ] || [ ! "$(ls -A dynamodb_data)" ]; then
        log "📝 Generando nuevos datos..."
        log "────────────────────────────────────────────────────────────"
        
        python3 DataGenerator.py
        
        if [ $? -eq 0 ]; then
            log "────────────────────────────────────────────────────────────"
            log_success "Datos generados correctamente en dynamodb_data/"
        else
            log_error "Error al generar datos"
            cd ..
            exit 1
        fi
    else
        log_success "Usando datos existentes en dynamodb_data/"
    fi
    
    # Poblar DynamoDB
    log "🗄️  Poblando DynamoDB..."
    log "────────────────────────────────────────────────────────────"
    
    python3 DataPoblator.py
    
    if [ $? -eq 0 ]; then
        log "────────────────────────────────────────────────────────────"
        log_success "Datos poblados correctamente en DynamoDB"
        log ""
        log "📊 Resumen de datos:"
        log "   ✅ Datos generados en dynamodb_data/"
        log "   ✅ Datos poblados en DynamoDB"
    else
        log_error "Error al poblar DynamoDB"
        cd ..
        exit 1
    fi
    
    cd ..
}

# Función para mostrar URLs de los servicios desplegados
show_endpoints() {
    log ""
    log "═══════════════════════════════════════════════════════"
    log "         📡 ENDPOINTS DE MICROSERVICIOS                "
    log "═══════════════════════════════════════════════════════"
    log ""
    
    # Arrays de servicios
    declare -A service_dirs=(
        ["👤 Usuarios"]="Microservicios/Usuarios"
        ["🏪 Locales (incluye Analítica)"]="Microservicios/Locales"
        ["👨‍🍳 Empleados"]="Microservicios/Empleados"
        ["🍜 Pedidos (incluye Workflow)"]="Microservicios/Pedidos"
    )
    
    # Obtener región de AWS
    AWS_REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")
    
    # Obtener endpoints usando AWS CLI
    for service_name in "${!service_dirs[@]}"; do
        service_path="${service_dirs[$service_name]}"
        
        if [ -d "$service_path" ]; then
            # Extraer el nombre del servicio del serverless.yml
            cd "$service_path" || continue
            sls_service=$(grep "^service:" serverless.yml | awk '{print $2}')
            
            if [ -n "$sls_service" ]; then
                # Buscar API Gateway usando AWS CLI
                api_id=$(aws apigateway get-rest-apis --region "$AWS_REGION" --query "items[?name=='dev-$sls_service'].id" --output text 2>/dev/null)
                
                if [ -n "$api_id" ] && [ "$api_id" != "None" ]; then
                    endpoint="https://${api_id}.execute-api.${AWS_REGION}.amazonaws.com/dev"
                    log_success "$service_name"
                    log "   URL: $endpoint"
                else
                    log_warning "$service_name - API no encontrada en AWS"
                fi
            else
                log_warning "$service_name - No se pudo leer serverless.yml"
            fi
            
            cd - > /dev/null || exit 1
        fi
    done
    
    log ""
}

# Función para verificar/crear bucket S3
ensure_s3_bucket() {
    local bucket_name="${1:-chinawok-data}"
    
    log "🪣 Verificando bucket S3: $bucket_name"
    
    # Verificar si el bucket existe y es accesible
    if aws s3 ls "s3://$bucket_name" >/dev/null 2>&1; then
        log_success "✅ Bucket '$bucket_name' ya existe y es accesible"
        
        # Verificar permisos de escritura
        log "🔍 Verificando permisos de escritura..."
        if echo "test" | aws s3 cp - "s3://$bucket_name/.test-write-permission" 2>/dev/null; then
            aws s3 rm "s3://$bucket_name/.test-write-permission" >/dev/null 2>&1
            log_success "✅ Permisos de escritura confirmados"
            return 0
        else
            log_error "❌ No tienes permisos de escritura en '$bucket_name'"
            return 1
        fi
    fi
    
    # El bucket no existe, intentar crearlo
    log "📦 Bucket no existe, intentando crear..."
    
    if aws s3 mb "s3://$bucket_name" --region us-east-1 2>&1; then
        log_success "✅ Bucket '$bucket_name' creado exitosamente"
        
        # Configurar bucket
        configure_bucket "$bucket_name"
        return 0
    else
        # Si falla por nombre duplicado, intentar con UUID corto
        log_warning "⚠️  Nombre '$bucket_name' no disponible"
        
        # Generar UUID corto (8 caracteres)
        local uuid_short=$(cat /dev/urandom | tr -dc 'a-z0-9' | fold -w 8 | head -n 1)
        local bucket_with_uuid="${bucket_name}-${uuid_short}"
        
        log_info "💡 Intentando con nombre único: $bucket_with_uuid"
        
        if aws s3 mb "s3://$bucket_with_uuid" --region us-east-1 2>&1; then
            log_success "✅ Bucket '$bucket_with_uuid' creado exitosamente"
            
            # Actualizar .env con el nuevo nombre
            log "📝 Actualizando .env con el nuevo nombre de bucket..."
            sed -i "s/^S3_BUCKET_NAME=.*/S3_BUCKET_NAME=$bucket_with_uuid/" .env
            log_success "✅ .env actualizado con S3_BUCKET_NAME=$bucket_with_uuid"
            
            # Configurar bucket
            configure_bucket "$bucket_with_uuid"
            return 0
        else
            log_error "❌ Error al crear bucket con UUID"
            
            # Último intento: usar Account ID
            local account_id=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
            if [ -n "$account_id" ]; then
                local bucket_with_account="chinawok-data-${account_id}"
                log_info "💡 Último intento con Account ID: $bucket_with_account"
                
                if aws s3 mb "s3://$bucket_with_account" --region us-east-1 2>&1; then
                    log_success "✅ Bucket '$bucket_with_account' creado exitosamente"
                    
                    # Actualizar .env
                    sed -i "s/^S3_BUCKET_NAME=.*/S3_BUCKET_NAME=$bucket_with_account/" .env
                    log_success "✅ .env actualizado con S3_BUCKET_NAME=$bucket_with_account"
                    
                    # Configurar bucket
                    configure_bucket "$bucket_with_account"
                    return 0
                fi
            fi
            
            log_error "❌ No se pudo crear ningún bucket"
            return 1
        fi
    fi
}

# Función auxiliar para configurar un bucket S3
configure_bucket() {
    local bucket_name="$1"
    
    log "🔄 Configurando bucket '$bucket_name'..."
    
    # Configurar versionado
    aws s3api put-bucket-versioning \
        --bucket "$bucket_name" \
        --versioning-configuration Status=Enabled \
        --region us-east-1 2>/dev/null
    
    # Configurar bloqueo de acceso público
    aws s3api put-public-access-block \
        --bucket "$bucket_name" \
        --public-access-block-configuration \
            "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
        --region us-east-1 2>/dev/null
    
    # Configurar reglas de ciclo de vida
    cat > /tmp/lifecycle-policy.json << 'EOF'
{
  "Rules": [
    {
      "Id": "DeleteOldIngestionData",
      "Status": "Enabled",
      "Filter": {"Prefix": "data-ingestion/"},
      "Expiration": {"Days": 90}
    },
    {
      "Id": "DeleteOldAthenaResults",
      "Status": "Enabled",
      "Filter": {"Prefix": "athena-results/"},
      "Expiration": {"Days": 30}
    }
  ]
}
EOF
    
    aws s3api put-bucket-lifecycle-configuration \
        --bucket "$bucket_name" \
        --lifecycle-configuration file:///tmp/lifecycle-policy.json \
        --region us-east-1 2>/dev/null
    
    rm -f /tmp/lifecycle-policy.json
    
    log_success "✅ Bucket configurado completamente"
}

# Menú de opciones
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  📋 OPCIONES DE DESPLIEGUE                           "
echo "═══════════════════════════════════════════════════════"
echo "  1) 🚀 Despliegue completo (datos + microservicios)  "
echo "  2) 📊 Solo poblar datos (DataGenerator)             "
echo "  3) ⚙️  Solo desplegar microservicios                "
echo "  4) 🗑️  Eliminar todo (remove)                       "
echo "═══════════════════════════════════════════════════════"
echo ""
read -p "Selecciona una opción (1-4): " opcion

case $opcion in
    1)
        log_info "Iniciando despliegue completo..."
        
        # Paso 1: Verificar/crear bucket S3
        log ""
        log "═══════════════════════════════════════════════════════"
        log "🪣 PASO 1/4: Verificando infraestructura S3"
        log "═══════════════════════════════════════════════════════"
        
        # Leer nombre del bucket del .env
        BUCKET_NAME=$(grep '^S3_BUCKET_NAME=' .env | cut -d '=' -f2)
        BUCKET_NAME=${BUCKET_NAME:-chinawok-data}
        
        if ! ensure_s3_bucket "$BUCKET_NAME"; then
            log_error "No se pudo configurar el bucket S3"
            exit 1
        fi
        
        # Paso 2: Construir Lambda Layer
        log ""
        log "═══════════════════════════════════════════════════════"
        log "🔧 PASO 2/4: Construyendo Lambda Layer compartido"
        log "═══════════════════════════════════════════════════════"
        build_layer
        
        # Paso 3: Poblar datos
        populate_data
        
        # Paso 4: Despliegue de microservicios
        log ""
        log "═══════════════════════════════════════════════════════"
        log "⚙️  PASO 4/4: Despliegue de microservicios"
        log "═══════════════════════════════════════════════════════"
        serverless deploy
        
        if [ $? -eq 0 ]; then
            log_success "🎉 Despliegue completo exitoso"
            
            # Mostrar endpoints
            show_endpoints
        else
            log_error "Error en despliegue de microservicios"
            exit 1
        fi
        ;;
        
    2)
        log_info "Poblando datos..."
        populate_data
        log_success "✨ Datos poblados exitosamente"
        ;;
        
    3)
        log_info "Desplegando microservicios..."
        
        # Verificar bucket S3 primero
        log ""
        log "🪣 Verificando infraestructura S3..."
        BUCKET_NAME=$(grep '^S3_BUCKET_NAME=' .env | cut -d '=' -f2)
        BUCKET_NAME=${BUCKET_NAME:-chinawok-data}
        
        if ! ensure_s3_bucket "$BUCKET_NAME"; then
            log_warning "⚠️  No se pudo configurar el bucket S3"
            read -p "¿Continuar de todos modos? (s/n): " continuar
            if [ "$continuar" != "s" ] && [ "$continuar" != "S" ]; then
                log_info "Despliegue cancelado"
                exit 0
            fi
        fi
        
        # Construir layer primero
        build_layer
        
        # Desplegar todo
        log ""
        log "Desplegando servicios..."
        serverless deploy
        
        if [ $? -eq 0 ]; then
            log_success "Microservicios desplegados exitosamente"
            
            # Mostrar endpoints
            show_endpoints
        else
            log_error "Error en despliegue"
            exit 1
        fi
        ;;
        
    4)
        log_warning "⚠️  ADVERTENCIA: Esto eliminará TODOS los recursos"
        read -p "¿Estás seguro? (s/n): " confirmar
        if [ "$confirmar" = "s" ] || [ "$confirmar" = "S" ]; then
            log "Eliminando recursos..."
            serverless remove
            
            if [ $? -eq 0 ]; then
                log_success "Recursos eliminados exitosamente"
            else
                log_error "Error al eliminar recursos"
                exit 1
            fi
        else
            log_info "Operación cancelada"
        fi
        ;;
        
    *)
        log_error "Opción inválida"
        exit 1
        ;;
esac

echo ""
log_success "✨ Operación completada"
echo ""
