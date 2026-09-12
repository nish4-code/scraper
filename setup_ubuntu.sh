#!/bin/bash
# ==========================================================
# Script de Instalación Rápida para Servidores Ubuntu / Debian
# ==========================================================

echo "=================================================="
echo "🚀 Instalando dependencias del sistema en Ubuntu..."
echo "=================================================="

sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip sqlite3 curl

echo "\n📦 Creando entorno virtual aislado de Python..."
python3 -m venv venv
source venv/bin/activate

echo "\n⚡ Instalando paquetes de Python desde requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

if [ ! -f .env ]; then
    echo "\n📝 Creando archivo .env desde .env.example..."
    cp .env.example .env
fi

echo "\n=================================================="
echo "✔ ¡INSTALACIÓN COMPLETADA CON ÉXITO!"
echo "=================================================="
echo "Para arrancar el orquestador:"
echo "  source venv/bin/activate"
echo "  python scheduler.py"
echo "=================================================="
