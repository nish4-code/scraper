import json
import sqlite3
from datetime import datetime
from category_scraper import ejecutar_extraccion_categoria
from telegram_sender import enviar_alerta_telegram

DB_PATH = "database.db"
CONFIG_PATH = "categories.json"
DESCUENTO_MINIMO_NOTIFICACION = 10.0  # Porcentaje mínimo de bajada para alerta

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(mass_price_history)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if columns and "raw_data" not in columns:
            cursor.execute("DROP TABLE mass_price_history")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mass_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                category TEXT,
                store TEXT,
                brand TEXT,
                title TEXT,
                price REAL,
                original_price REAL,
                discount_pct REAL,
                currency TEXT,
                in_stock BOOLEAN,
                seller TEXT,
                rating REAL,
                reviews_count INTEGER,
                url TEXT,
                image_url TEXT,
                raw_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_url ON mass_price_history(url)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON mass_price_history(category)")
        conn.commit()

def procesar_lote_productos(category: str, productos: list):
    ofertas_detectadas = []
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        for prod in productos:
            url = prod["url"]
            precio_actual = prod["price"]
            store = prod["store"]
            title = prod["title"]
            image_url = prod["image_url"]

            # Obtener el último precio registrado de esta URL
            cursor.execute("""
                SELECT price FROM mass_price_history 
                WHERE url = ? 
                ORDER BY created_at DESC LIMIT 1
            """, (url,))
            resultado = cursor.fetchone()

            # Insertar registro completo con raw_data
            cursor.execute("""
                INSERT INTO mass_price_history (
                    product_id, category, store, brand, title, price, original_price,
                    discount_pct, currency, in_stock, seller, rating, reviews_count,
                    url, image_url, raw_data
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prod.get("product_id"), category, store, prod.get("brand"), title,
                precio_actual, prod.get("original_price"), prod.get("discount_pct"),
                prod.get("currency", "PEN"), prod.get("in_stock", True), prod.get("seller"),
                prod.get("rating"), prod.get("reviews_count"), url, image_url,
                prod.get("raw_data")
            ))

            # Comparar con precio previo o evaluar descuento directo de tienda
            if resultado and resultado[0] is not None:
                precio_anterior = resultado[0]
                if precio_actual < precio_anterior:
                    bajon = ((precio_anterior - precio_actual) / precio_anterior) * 100
                    if bajon >= DESCUENTO_MINIMO_NOTIFICACION:
                        oferta = {
                            "title": title,
                            "store": store,
                            "url": url,
                            "image_url": image_url,
                            "precio_anterior": precio_anterior,
                            "precio_actual": precio_actual,
                            "descuento_pct": round(bajon, 2)
                        }
                        ofertas_detectadas.append(oferta)
            elif prod.get("discount_pct") and prod.get("discount_pct") >= DESCUENTO_MINIMO_NOTIFICACION:
                oferta = {
                    "title": title,
                    "store": store,
                    "url": url,
                    "image_url": image_url,
                    "precio_anterior": prod.get("original_price"),
                    "precio_actual": precio_actual,
                    "descuento_pct": prod.get("discount_pct")
                }
                ofertas_detectadas.append(oferta)

        conn.commit()
    return ofertas_detectadas

def correr_extraccion_masiva():
    init_db()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        categorias = json.load(f)

    print(f"\n==================================================")
    print(f"  INICIANDO EXTRACCIÓN MASIVA CON FILTRADO ESTRICTO: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"==================================================")

    todas_las_ofertas = []

    for cat in categorias:
        categoria_nombre = cat["category"]
        tienda = cat["store"]
        url = cat["url"]
        max_pages = cat.get("max_pages", 3)

        print(f"\nProcesando [{categoria_nombre.upper()}] en {tienda}...")
        productos = ejecutar_extraccion_categoria(categoria_nombre, tienda, url, max_pages)
        print(f"  Total extraídos filtrados estrictos: {len(productos)} productos.")

        if productos:
            alertas = procesar_lote_productos(categoria_nombre, productos)
            todas_las_ofertas.extend(alertas)

    print(f"\n==================================================")
    print(f"  RESUMEN: {len(todas_las_ofertas)} OFERTAS DE IMPACTO DETECTADAS EN ESTE CICLO")
    print(f"==================================================")

    for oferta in todas_las_ofertas:
        orig_str = f"S/ {oferta['precio_anterior']:,.2f}" if oferta.get('precio_anterior') else "N/A"
        print(f"🔥 [-{oferta['descuento_pct']}%] {oferta['title'][:60]}...")
        print(f"   De: {orig_str} ➔ A: S/ {oferta['precio_actual']:,.2f} ({oferta['store']})")
        print(f"   Link: {oferta['url']}\n")
        # Enviar alerta a Telegram si está configurado
        enviar_alerta_telegram(oferta)

if __name__ == "__main__":
    correr_extraccion_masiva()
