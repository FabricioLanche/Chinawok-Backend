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

# Verificar credenciales AWS
log "Verificando credenciales AWS..."
if ! aws sts get-caller-identity &> /dev/null; then
    log_error "No se pudo conectar con AWS"
    exit 1
fi
log_success "Credenciales AWS verificadas"

# Menú de opciones
echo ""
echo "┌─────────────────────────────────────────────────────────┐"
echo "│  📋 OPCIONES DE DESPLIEGUE                              │"
echo "├─────────────────────────────────────────────────────────┤"
echo "│  1) 🚀 Despliegue completo (datos + microservicios)     │"
echo "│  2) 📊 Solo poblar datos (DataGenerator)               │"
echo "│  3) ⚙️  Solo desplegar microservicios                   │"
echo "│  4) 🗑️  Eliminar todo (remove)                          │"
echo "│  5) 🔄 Repoblar datos (limpia y recrea)                │"
echo "└─────────────────────────────────────────────────────────┘"
echo ""
read -p "Selecciona una opción (1-5): " opcion

case $opcion in
    1)
        log_info "Iniciando despliegue completo..."
        
        # Paso 0: Construir Lambda Layer
        log "═══════════════════════════════════════════════════════"
        log "🔧 PASO 0/3: Construyendo Lambda Layer compartido"
        log "═══════════════════════════════════════════════════════"
        cd layers || exit 1
        bash build-layer.sh
        if [ $? -ne 0 ]; then
            log_error "Error al construir Lambda Layer"
            exit 1
        fi
        cd ..
        
        # Paso 1: DataGenerator
        log ""
        log "═══════════════════════════════════════════════════════"
        log "📊 PASO 1/3: Población de datos"
        log "═══════════════════════════════════════════════════════"
        cd DataGenerator || exit 1
        bash setup_and_run.sh
        if [ $? -ne 0 ]; then
            log_error "Error en DataGenerator"
            exit 1
        fi
        cd ..
        
        # Paso 2: Microservicios
        log ""
        log "═══════════════════════════════════════════════════════"
        log "⚙️  PASO 2/3: Despliegue de microservicios"
        log "═══════════════════════════════════════════════════════"
        serverless deploy
        
        if [ $? -eq 0 ]; then
            log_success "🎉 Despliegue completo exitoso"
        else
            log_error "Error en despliegue de microservicios"
            exit 1
        fi
        ;;
        
    2)
        log_info "Poblando datos..."
        cd DataGenerator || exit 1
        bash setup_and_run.sh
        cd ..
        log_success "Datos poblados"
        ;;
        
    3)
        log_info "Desplegando microservicios..."
        
        # Construir layer primero
        log "Construyendo Lambda Layer..."
        cd layers && bash build-layer.sh && cd ..
        
        # Desplegar todo
        serverless deploy
        log_success "Microservicios desplegados"
        ;;
        
    4)
        log_warning "⚠️  ADVERTENCIA: Esto eliminará TODOS los recursos"
        read -p "¿Estás seguro? (s/n): " confirmar
        if [ "$confirmar" = "s" ] || [ "$confirmar" = "S" ]; then
            serverless remove
            log_success "Recursos eliminados"
        else
            log_info "Operación cancelada"
        fi
        ;;
        
    5)
        log_info "Repoblando datos..."
        cd DataGenerator || exit 1
        
        # Forzar regeneración
        if [ -d "dynamodb_data" ]; then
            log "Eliminando datos anteriores..."
            rm -rf dynamodb_data
        fi
        
        # Configurar modo replace automático
        export AUTO_REPLACE=true
        bash setup_and_run.sh
        cd ..
        log_success "Datos repoblados"
        ;;
        
    *)
        log_error "Opción inválida"
        exit 1
        ;;
esac

echo ""
log_success "✨ Operación completada"
echo ""
