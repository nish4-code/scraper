import time
import schedule
from datetime import datetime
from main import correr_ciclo as monitoreo_vip
from main_bulk import correr_extraccion_masiva as barrido_masivo

def tarea_vip():
    print(f"\n⚡ [{datetime.now().strftime('%H:%M:%S')}] Executing VIP Monitoring (Every 2 Hours)...")
    try:
        monitoreo_vip()
    except Exception as e:
        print(f"✖ Error VIP: {e}")

def tarea_masiva():
    print(f"\n📦 [{datetime.now().strftime('%H:%M:%S')}] Executing Daily Mass Scan (04:00 AM)...")
    try:
        barrido_masivo()
    except Exception as e:
        print(f"✖ Error Masivo: {e}")

# 1. Monitoreo VIP cada 2 horas
schedule.every(2).hours.do(tarea_vip)

# 2. Barrido masivo diario a las 04:00 AM
schedule.every().day.at("04:00").do(tarea_masiva)

if __name__ == "__main__":
    print(f"==================================================")
    print(f"=== ORQUESTADOR DE SCRAPING TECH INICIADO 24/7 ===")
    print(f"==================================================")
    print("  • Monitoreo VIP: Cada 2 horas")
    print("  • Barrido Masivo: Todos los días a las 04:00 AM")
    print("--------------------------------------------------\n")
    
    # Prueba inicial al arrancar
    tarea_vip()
    
    while True:
        schedule.run_pending()
        time.sleep(10)
