#!/bin/bash

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      🔧 CONSTRUYENDO LAMBDA LAYER COMPARTIDO          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

# Crear estructura de directorios
echo -e "${BLUE}📁 Creando estructura de directorios...${NC}"
rm -rf python-dependencies/python
mkdir -p python-dependencies/python

# Instalar dependencias
echo -e "${BLUE}📦 Instalando dependencias Python...${NC}"
pip install -r python-dependencies/requirements.txt -t python-dependencies/python/ --quiet

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dependencias instaladas correctamente${NC}"
else
    echo -e "${RED}❌ Error al instalar dependencias${NC}"
    exit 1
fi

# Crear archivo ZIP
echo -e "${BLUE}📦 Creando archivo ZIP del layer...${NC}"
cd python-dependencies
zip -r ../python-dependencies-layer.zip python/ -q

if [ $? -eq 0 ]; then
    cd ..
    echo -e "${GREEN}✅ Layer empaquetado: python-dependencies-layer.zip${NC}"
    echo -e "${GREEN}   Tamaño: $(du -h python-dependencies-layer.zip | cut -f1)${NC}"
else
    echo -e "${RED}❌ Error al crear ZIP${NC}"
    exit 1
fi

# Limpiar directorio temporal
echo -e "${BLUE}🗑️  Limpiando archivos temporales...${NC}"
rm -rf python-dependencies/python

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      ✅ LAYER CONSTRUIDO EXITOSAMENTE                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📝 Próximos pasos:${NC}"
echo -e "   1. El layer será desplegado automáticamente con serverless deploy"
echo -e "   2. Todos los microservicios lo usarán automáticamente"
echo ""
