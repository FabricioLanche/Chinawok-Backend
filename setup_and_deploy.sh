#!/bin/bash

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
    npm install -g serverless
    
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
    
    # Limpiar build anterior de libs (las dependencias de terceros)
    log "🗑️  Limpiando python/libs anterior..."
    rm -rf python/libs/*
    
    # Crear estructura si no existe
    mkdir -p python/libs
    
    # Instalar dependencias de terceros en python/libs
    log "📦 Instalando dependencias de terceros en python/libs..."
    pip install -r requirements.txt \
        -t python/libs \
        --quiet \
        --upgrade \
        --no-cache-dir
    
    if [ $? -ne 0 ]; then
        log_error "Error al instalar dependencias del layer"
        exit 1
    fi
    
    log_success "✅ Dependencias instaladas en python/libs/"
    log_info "ℹ️  Las utilidades compartidas ya están en python/utils/"
    
    # Verificar estructura
    log "🔍 Verificando estructura del layer..."
    if [ -d "python/libs" ] && [ -d "python/utils" ]; then
        log_success "✅ Estructura del layer correcta"
        log_info "   📂 python/libs/ - Dependencias de terceros"
        log_info "   📂 python/utils/ - Código compartido"
    else
        log_error "❌ Estructura del layer incorrecta"
        exit 1
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
        
        # Paso 1: Construir Lambda Layer
        log ""
        log "═══════════════════════════════════════════════════════"
        log "🔧 PASO 1/3: Construyendo Lambda Layer compartido"
        log "═══════════════════════════════════════════════════════"
        build_layer
        
        # Paso 2: Poblar datos
        populate_data
        
        # Paso 3: Despliegue de microservicios
        log ""
        log "═══════════════════════════════════════════════════════"
        log "⚙️  PASO 3/3: Despliegue de microservicios"
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
