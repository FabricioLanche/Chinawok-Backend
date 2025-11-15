# 🥡 ChinaWok Backend

Backend completo para la plataforma ChinaWok usando arquitectura de microservicios en AWS.

## 📋 Índice

- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Configuración Inicial](#configuración-inicial)
- [Despliegue](#despliegue)
- [Estructura del Proyecto](#estructura-del-proyecto)

## 🏗️ Arquitectura

## ✅ Requisitos

- **Node.js >= 18** y npm
- **Python >= 3.12**
- **Serverless Framework CLI**
- **AWS CLI** configurado
- Cuenta AWS con LabRole

### Instalación de requisitos

```bash
# 1. Verificar Node.js y npm
node --version  # Debe ser >= 18
npm --version

# Si no están instalados (Ubuntu/Debian):
sudo apt update
sudo apt install -y nodejs npm

# 2. Instalar Serverless Framework
npm install -g serverless

# 3. Verificar instalación
serverless --version

# 4. Instalar Python dependencies
pip install -r requirements.txt

# 5. Configurar AWS CLI
aws configure
```

## 🚀 Despliegue

Despliegue de los microservicios usando el framework Serverless.

## 📦 Estructura del Proyecto

- `serverless.yml`: Configuración del despliegue de los microservicios.
- `requirements.txt`: Dependencias de Python.
- `package.json`: Dependencias de Node.js.