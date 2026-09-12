# 🚀 Servidor de Ofertas Tech y Afiliados (Perú)

Sistema de scraping híbrido para monitoreo de productos tech (Laptops, Smartphones, Televisores, Consolas) en Falabella, Plaza Vea y Promart Perú con envío automático de ofertas a Telegram.

---

## 🛠️ Despliegue Rápido en Ubuntu Server

### Opción 1: Script Automatizado 1-Click
```bash
chmod +x setup_ubuntu.sh
./setup_ubuntu.sh
```

### Opción 2: Pasos Manuales
```bash
# 1. Actualizar e instalar dependencias del sistema
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip sqlite3

# 2. Crear y activar entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar librerías de Python
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
nano .env  # Coloca tu TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID
```

---

## ⚡ Ejecución

- **Modo 24/7 Orquestador**: `python scheduler.py`
- **Barrido Masivo Manual**: `python main_bulk.py`
- **Monitoreo VIP Manual**: `python main.py`
