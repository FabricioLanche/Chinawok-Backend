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
echo "╔════════════════════════════════════════════════════════════╗"
echo "║         🥡 CHINAWOK BACKEND - DEPLOY MAESTRO 🥡           ║"
echo "╚════════════════════════════════════════════════════════════╝"
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
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "No se pudo conectar con AWS"
    exit 1
fi
log_success "Credenciales AWS verificadas"

# Función para construir Lambda Layer
build_layer() {
    log "🔧 Construyendo Lambda Layer compartido..."
    
    cd Layers || exit 1
    
    # Limpiar build anterior
    rm -rf python-dependencies/python
    rm -f python-dependencies-layer.zip
    
    # Crear estructura
    mkdir -p python-dependencies/python
    
    # Instalar dependencias
    log "📦 Instalando dependencias en el layer..."
    pip install -r python-dependencies/requirements.txt \
        -t python-dependencies/python/ \
        --quiet \
        --upgrade \
        --no-cache-dir
    
    if [ $? -ne 0 ]; then
        log_error "Error al instalar dependencias del layer"
        exit 1
    fi
    
    # Crear ZIP
    cd python-dependencies
    zip -r ../python-dependencies-layer.zip python/ -q
    cd ..
    
    # Limpiar temporal
    rm -rf python-dependencies/python
    
    cd ..
    log_success "Lambda Layer construido correctamente"
}

# Función para mostrar URLs de los servicios desplegados
show_endpoints() {
    log ""
    log "╔════════════════════════════════════════════════════════════╗"
    log "║              📡 ENDPOINTS DE MICROSERVICIOS                ║"
    log "╚════════════════════════════════════════════════════════════╝"
    log ""
    
    # Arrays de servicios
    declare -A service_dirs=(
        ["👤 Usuarios"]="Microservicios/Usuarios"
        ["🏪 Locales"]="Microservicios/Locales"
        ["👨‍🍳 Empleados"]="Microservicios/Empleados"
        ["🍜 Pedidos"]="Microservicios/Pedidos"
        ["⚙️  Workflow"]="Microservicios/Stepfunctions"
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
    
    # Guardar endpoints en archivo
    cat > endpoints.txt << EOF
╔════════════════════════════════════════════════════════════╗
║              📡 CHINAWOK - ENDPOINTS DE API                ║
╚════════════════════════════════════════════════════════════╝

Fecha: $(date)
Región: $AWS_REGION

EOF
    
    for service_name in "${!service_dirs[@]}"; do
        service_path="${service_dirs[$service_name]}"
        
        if [ -d "$service_path" ]; then
            cd "$service_path" || continue
            sls_service=$(grep "^service:" serverless.yml | awk '{print $2}')
            
            if [ -n "$sls_service" ]; then
                api_id=$(aws apigateway get-rest-apis --region "$AWS_REGION" --query "items[?name=='dev-$sls_service'].id" --output text 2>/dev/null)
                
                if [ -n "$api_id" ] && [ "$api_id" != "None" ]; then
                    endpoint="https://${api_id}.execute-api.${AWS_REGION}.amazonaws.com/dev"
                    echo "$service_name: $endpoint" >> ../../endpoints.txt
                fi
            fi
            
            cd - > /dev/null || exit 1
        fi
    done
    
    log_info "Endpoints guardados en: endpoints.txt"
}

# Menú de opciones
echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│  📋 OPCIONES DE DESPLIEGUE                              │"
echo "├─────────────────────────────────────────────────────────┤"
echo "│  1) 🚀 Despliegue completo (datos + microservicios)     │"
echo "│  2) 📊 Solo poblar datos (DataGenerator)               │"
echo "│  3) ⚙️  Solo desplegar microservicios                   │"
echo "│  4) 🗑️  Eliminar todo (remove)                          │"
echo "└─────────────────────────────────────────────────────────┘"
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
        log ""
        log "═══════════════════════════════════════════════════════"
        log "📊 PASO 2/3: Población de datos"
        log "═══════════════════════════════════════════════════════"
        cd Microservicios/DataGenerator || exit 1
        bash setup_and_run.sh
        if [ $? -ne 0 ]; then
            log_error "Error en DataGenerator"
            exit 1
        fi
        cd ../..
        
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
        cd Microservicios/DataGenerator || exit 1
        bash setup_and_run.sh
        if [ $? -ne 0 ]; then
            log_error "Error en DataGenerator"
            exit 1
        fi
        cd ../..
        log_success "Datos poblados exitosamente"
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
