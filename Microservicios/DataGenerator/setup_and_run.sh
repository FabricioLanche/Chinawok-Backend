#!/bin/bash

# Colores para los logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para imprimir logs con timestamp
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}"
}

# Inicio del script
log "============================================================"
log "🚀 Iniciando proceso de generación y población de datos"
log "============================================================"

# 1. Verificar credenciales de AWS
log "📋 Paso 1/4: Verificando credenciales de AWS..."

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
log "Verificando conectividad con AWS..."
if aws sts get-caller-identity &> /dev/null; then
    log_success "Conexión con AWS verificada correctamente"
else
    log_error "No se pudo conectar con AWS. Verifica tus credenciales."
    exit 1
fi

# 2. Instalar dependencias
log "📦 Paso 2/4: Instalando dependencias de Python..."

# Usar requirements.txt del directorio raíz del proyecto (dos niveles arriba)
if [ -f ../../requirements.txt ]; then
    log "Instalando paquetes desde ../../requirements.txt..."
    pip install -r ../../requirements.txt --quiet
    
    if [ $? -eq 0 ]; then
        log_success "Dependencias instaladas correctamente"
    else
        log_error "Error al instalar dependencias"
        exit 1
    fi
else
    log_error "Archivo requirements.txt no encontrado en el directorio raíz"
    exit 1
fi

# 3. Generar datos si no existen
log "🔍 Paso 3/4: Verificando existencia de datos generados..."

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

if [ ! -d "dynamodb_data" ] || [ ! "$(ls -A dynamodb_data)" ]; then
    log "📝 Generando nuevos datos..."
    log "============================================================"
    
    python3 DataGenerator.py
    
    if [ $? -eq 0 ]; then
        log "============================================================"
        log_success "Datos generados correctamente en dynamodb_data/"
    else
        log_error "Error al generar datos"
        exit 1
    fi
else
    log_success "Usando datos existentes en dynamodb_data/"
fi

# 4. Poblar DynamoDB
log "🗄️  Paso 4/4: Poblando DynamoDB..."
log "============================================================"
log ""
log "⚠️  IMPORTANTE: El script te preguntará qué hacer con los datos existentes:"
log "   - Opción 1: Agregar datos nuevos (mantener los actuales)"
log "   - Opción 2: Eliminar datos existentes y reemplazar"
log ""

python3 DataPoblator.py

if [ $? -eq 0 ]; then
    log "============================================================"
    log_success "Datos poblados correctamente en DynamoDB"
else
    log_error "Error al poblar DynamoDB"
    exit 1
fi

# Finalización exitosa
log "============================================================"
log_success "🎉 Proceso completado exitosamente"
log "============================================================"
log ""
log "📊 Resumen:"
log "   ✅ Credenciales AWS verificadas"
log "   ✅ Dependencias instaladas"
log "   ✅ Datos generados en dynamodb_data/"
log "   ✅ Datos poblados en DynamoDB"
log ""
log "Para consultar los datos generados, revisa la carpeta: dynamodb_data/"
log "============================================================"

exit 0
