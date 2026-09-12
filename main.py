import json
import sqlite3
import time
import random
from datetime import datetime
from scraper import ejecutar_scraping
from telegram_sender import enviar_alerta_telegram

DB_PATH = "database.db"
SEEDS_PATH = "urls_seed.json"
DESCUENTO_MINIMO_ALERTA = 5.0  # Porcentaje mínimo de bajada para alerta VIP

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vip_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                store TEXT,
                title TEXT,
                price REAL,
                in_stock BOOLEAN,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def guardar_y_evaluar_precio(product_id: str, store: str, title: str, precio_actual: float, in_stock: bool, target_price: float = None, image_url: str = None, url: str = None):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT price FROM vip_price_history 
            WHERE product_id = ? AND store = ? 
            ORDER BY created_at DESC LIMIT 1
        """, (product_id, store))
        resultado = cursor.fetchone()
        
        cursor.execute("""
            INSERT INTO vip_price_history (product_id, store, title, price, in_stock)
            VALUES (?, ?, ?, ?, ?)
        """, (product_id, store, title, precio_actual, in_stock))
        conn.commit()

        if resultado and resultado[0] is not None:
            precio_anterior = resultado[0]
            if precio_actual < precio_anterior:
                bajon = ((precio_anterior - precio_actual) / precio_anterior) * 100
                if bajon >= DESCUENTO_MINIMO_ALERTA:
                    return {
                        "es_alerta": True,
                        "tipo": "caida_historica",
                        "title": title,
                        "store": store,
                        "url": url,
                        "image_url": image_url,
                        "descuento_pct": round(bajon, 2),
                        "precio_anterior": precio_anterior,
                        "precio_actual": precio_actual
                    }
        
        if target_price and precio_actual <= target_price:
            return {
                "es_alerta": True,
                "tipo": "target_price_alcanzado",
                "title": title,
                "store": store,
                "url": url,
                "image_url": image_url,
                "descuento_pct": round(((target_price - precio_actual) / target_price) * 100, 2) if target_price > precio_actual else 0,
                "precio_anterior": target_price,
                "precio_actual": precio_actual
            }

    return {"es_alerta": False}

def correr_ciclo():
    init_db()
    with open(SEEDS_PATH, "r", encoding="utf-8") as f:
        catalogo = json.load(f)

    print(f"\n==================================================")
    print(f"  ⚡ INICIANDO MONITOREO VIP: ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"==================================================")

    for item in catalogo:
        product_id = item["id"]
        product_name = item["name"]
        target_price = item.get("target_price_alert")

        for store_info in item["stores"]:
            store_name = store_info["name"]
            url = store_info["url"]

            print(f"\nExtrayendo VIP: [{store_name}] {product_name}...")
            data = ejecutar_scraping(store_name, url)

            if data.get("status") == "success" and data.get("price") is not None:
                title = data.get("title") or product_name
                evaluacion = guardar_y_evaluar_precio(
                    product_id=product_id,
                    store=store_name,
                    title=title,
                    precio_actual=data["price"],
                    in_stock=data.get("in_stock", True),
                    target_price=target_price,
                    image_url=data.get("image_url"),
                    url=url
                )

                print(f"  ✔ Título : {title[:60]}...")
                print(f"  ✔ Precio : S/ {data['price']:,.2f} {data['currency']}")

                if evaluacion["es_alerta"]:
                    print(f"  🔥 ALERTA VIP ACTIVADA ({evaluacion['tipo']}): S/ {evaluacion['precio_actual']:,.2f}")
                    enviar_alerta_telegram(evaluacion)
            else:
                print(f"  ✖ Error: {data.get('error', 'Sin datos')}")

            time.sleep(random.uniform(1.5, 3))

    print("\n=== CICLO VIP COMPLETADO ===")

if __name__ == "__main__":
    correr_ciclo()
