import json
import re
import time
import random
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from proxy_manager import proxy_manager

try:
    from curl_cffi import requests as http_client
    HAS_CURL_CFFI = True
except ImportError:
    import httpx as http_client
    HAS_CURL_CFFI = False

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-PE,es;q=0.9,en-US;q=0.8,en;q=0.7",
}

EXCLUDE_KEYWORDS = {
    "smartphones": [
        "secadora", "secador", "rizador", "ondulador", "funda", "estuche", "protector", "cable",
        "soporte", "mica", "carcasa", "cargador", "audifono", "audífono", "adaptador",
        "vidrio", "correa", "holder", "anillo", "tripode", "trípode", "lente", "parlante",
        "alaciadora", "multistyler", "alisadora", "plancha", "multigroom", "estilizador",
        "cepillo", "depiladora", "recortadora", "afeitadora", "barbera", "cortapelo"
    ],
    "laptops": [
        "funda", "mochila", "soporte", "mouse", "teclado", "cargador", "hub",
        "limpiador", "base enfriadora", "estuche", "maletin", "maletín", "cable",
        "adaptador", "memoria ram", "disco duro", "memoria"
    ],
    "televisores": [
        "soporte", "control remoto", "antena", "rack", "cable", "limpiador", "funda"
    ],
    "consolas_gaming": [
        "polera", "taza", "poster", "mochila", "llavero", "polo", "gorra"
    ]
}

REQUIRED_KEYWORDS = {
    "smartphones": [
        "celular", "smartphone", "iphone", "galaxy", "xiaomi", "redmi", "poco",
        "moto", "honor", "realme", "zflip", "zfold", "pixel", "oppo", "vivo",
        "infinix", "tecno", "zte", "huawei", "samsung", "nokia"
    ],
    "laptops": [
        "laptop", "notebook", "macbook", "zenbook", "vivobook", "ideapad", "thinkpad",
        "tuf", "nitro", "loq", "legion", "victus", "alienware", "rog", "predator",
        "inspiron", "pavilion", "hp", "dell", "asus", "lenovo", "acer"
    ],
    "televisores": [
        "tv", "televisor", "smart tv", "oled", "qled", "nanocell", "crystal uhd"
    ],
    "consolas_gaming": [
        "playstation", "ps5", "ps4", "nintendo", "switch", "xbox", "rog ally", "consola"
    ]
}

def es_producto_valido(category: str, title: str) -> bool:
    """Verifica estrictamente que el título pertenezca a la categoría y no sea un producto no relevante."""
    if not title:
        return False
    t_lower = title.lower()

    # 1. Verificar descartes por palabras prohibidas
    for exc in EXCLUDE_KEYWORDS.get(category, []):
        if exc in t_lower:
            return False

    # 2. Verificar inclusión por palabras requeridas obligatorias
    reqs = REQUIRED_KEYWORDS.get(category, [])
    if reqs:
        if not any(req in t_lower for req in reqs):
            return False

    return True

def get_request(url: str):
    """Realiza una petición HTTP utilizando curl_cffi y rotación opcional de proxies."""
    proxies = proxy_manager.get_proxy()
    if HAS_CURL_CFFI:
        kwargs = {"headers": HEADERS, "impersonate": "chrome110", "timeout": 15}
        if proxies:
            kwargs["proxies"] = proxies
        return http_client.get(url, **kwargs)
    else:
        kwargs = {"headers": HEADERS, "timeout": 15}
        if proxies:
            kwargs["proxies"] = proxies
        return http_client.get(url, **kwargs)

def scrapear_vtex_store(category: str, store_name: str, base_domain: str, query: str, max_paginas: int = 3) -> List[Dict[str, Any]]:
    """Extrae productos de tiendas basadas en VTEX API (Plaza Vea, Promart, etc.) con filtrado estricto."""
    productos = []
    items_per_page = 50

    for pagina in range(max_paginas):
        from_idx = pagina * items_per_page
        to_idx = from_idx + items_per_page - 1
        endpoint = f"https://{base_domain}/api/catalog_system/pub/products/search?ft={query}&_from={from_idx}&_to={to_idx}"

        print(f"  -> [{store_name}] Descargando API lote {pagina + 1} ({from_idx}-{to_idx})...")
        try:
            res = get_request(endpoint)
            if res.status_code not in [200, 206]:
                print(f"  ✖ HTTP Status {res.status_code} en {store_name}")
                break

            items = res.json()
            if not isinstance(items, list) or not items:
                break

            for p in items:
                try:
                    title = p.get("productName")
                    if not es_producto_valido(category, title):
                        continue

                    product_id = str(p.get("productId"))
                    brand = p.get("brand")
                    link = p.get("link")
                    
                    skus = p.get("items", [])
                    if not skus:
                        continue
                    
                    sku_first = skus[0]
                    sellers = sku_first.get("sellers", [])
                    if not sellers:
                        continue
                    
                    offer = sellers[0].get("commertialOffer", {})
                    seller_name = sellers[0].get("sellerName") or store_name
                    
                    price = offer.get("Price")
                    original_price = offer.get("ListPrice")
                    in_stock = offer.get("IsAvailable", True)
                    
                    discount_pct = None
                    if original_price and price and original_price > price:
                        discount_pct = round(((original_price - price) / original_price) * 100, 2)

                    images = sku_first.get("images", [])
                    image_url = images[0].get("imageUrl") if images else None

                    if title and price and link:
                        full_url = link if link.startswith("http") else f"https://{base_domain}{link}"
                        productos.append({
                            "product_id": product_id,
                            "store": store_name,
                            "brand": brand,
                            "title": title,
                            "price": float(price),
                            "original_price": float(original_price) if original_price else None,
                            "discount_pct": discount_pct,
                            "currency": "PEN",
                            "in_stock": bool(in_stock),
                            "seller": seller_name,
                            "rating": None,
                            "reviews_count": None,
                            "url": full_url,
                            "image_url": image_url,
                            "raw_data": json.dumps(p, ensure_ascii=False)
                        })
                except Exception:
                    continue

            time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            print(f"  ✖ Error en {store_name} lote {pagina + 1}: {e}")
            break

    return productos

def scrapear_falabella_categoria(category: str, url_base: str, max_paginas: int = 3) -> List[Dict[str, Any]]:
    productos = []

    for pagina in range(1, max_paginas + 1):
        url_actual = f"{url_base}?page={pagina}" if "?" not in url_base else f"{url_base}&page={pagina}"
        print(f"  -> [Falabella] Descargando página {pagina}...")

        try:
            res = get_request(url_actual)
            if res.status_code != 200:
                print(f"  ✖ HTTP Status {res.status_code} en Falabella página {pagina}")
                break

            soup = BeautifulSoup(res.text, "html.parser")
            next_data = soup.find("script", id="__NEXT_DATA__")
            if not next_data or not next_data.string:
                print(f"  ✖ Script __NEXT_DATA__ no encontrado en Falabella página {pagina}")
                break

            data = json.loads(next_data.string)
            results = data.get("props", {}).get("pageProps", {}).get("results", [])
            if not results:
                break

            for prod in results:
                title = prod.get("displayName")
                if not es_producto_valido(category, title):
                    continue

                product_id = prod.get("id") or prod.get("skuId")
                brand = prod.get("brand")
                url = prod.get("url")
                image_url = prod.get("mediaUrls", [None])[0]
                seller = prod.get("sellerName") or "Falabella"
                rating = prod.get("rating")
                reviews_count = prod.get("reviewCount")

                prices = prod.get("prices", [])
                price = None
                original_price = None
                discount_pct = None

                if prices:
                    price_val = prices[0].get("price", [None])[0]
                    if price_val:
                        price = float(re.sub(r"[^\d.]", "", str(price_val)))

                    if len(prices) > 1:
                        orig_val = prices[1].get("price", [None])[0]
                        if orig_val:
                            original_price = float(re.sub(r"[^\d.]", "", str(orig_val)))
                            if original_price > price:
                                discount_pct = round(((original_price - price) / original_price) * 100, 2)

                if title and price and url:
                    full_url = url if url.startswith("http") else f"https://www.falabella.com.pe{url}"
                    productos.append({
                        "product_id": str(product_id) if product_id else None,
                        "store": "Falabella",
                        "brand": brand,
                        "title": title,
                        "price": price,
                        "original_price": original_price,
                        "discount_pct": discount_pct,
                        "currency": "PEN",
                        "in_stock": True,
                        "seller": seller,
                        "rating": float(rating) if rating is not None else None,
                        "reviews_count": int(reviews_count) if reviews_count is not None else None,
                        "url": full_url,
                        "image_url": image_url,
                        "raw_data": json.dumps(prod, ensure_ascii=False)
                    })

            time.sleep(random.uniform(1.5, 3))
        except Exception as e:
            print(f"  ✖ Error en Falabella página {pagina}: {e}")
            break

    return productos

def scrapear_mercadolibre_categoria(category: str, url_base: str, max_paginas: int = 2) -> List[Dict[str, Any]]:
    productos = []
    items_por_pagina = 50

    for pagina in range(max_paginas):
        offset = (pagina * items_por_pagina) + 1
        url_actual = (
            re.sub(r"_Desde_\d+", f"_Desde_{offset}", url_base)
            if "_Desde_" in url_base
            else f"{url_base.rstrip('/')}_Desde_{offset}"
        )

        print(f"  -> [Mercado Libre] Descargando página {pagina + 1}...")
        try:
            res = get_request(url_actual)
            if res.status_code != 200:
                print(f"  ✖ HTTP Status {res.status_code} en ML")
                break

            soup = BeautifulSoup(res.text, "html.parser")
            items = soup.find_all("li", class_="ui-search-layout__item") or soup.select(".poly-card")

            if not items:
                break

            for item in items:
                link_tag = item.find("a", class_="poly-component__title") or item.find("a", class_="ui-search-link")
                title = link_tag.text.strip() if link_tag else None
                if not es_producto_valido(category, title):
                    continue

                url = link_tag["href"].split("#")[0] if link_tag and link_tag.has_attr("href") else None
                price_tag = item.find("span", class_="andes-money-amount__fraction")
                price = float(price_tag.text.replace(".", "").replace(",", "")) if price_tag else None

                img_tag = item.find("img")
                image_url = img_tag.get("data-src") or img_tag.get("src") if img_tag else None
                seller_tag = item.find("span", class_="ui-search-official-store-label") or item.find("span", class_="poly-component__seller")
                seller = seller_tag.text.strip() if seller_tag else "Mercado Libre"

                if title and price and url:
                    productos.append({
                        "product_id": url.split("/")[-1],
                        "store": "Mercado Libre",
                        "brand": None,
                        "title": title,
                        "price": price,
                        "original_price": None,
                        "discount_pct": None,
                        "currency": "PEN",
                        "in_stock": True,
                        "seller": seller,
                        "rating": None,
                        "reviews_count": None,
                        "url": url,
                        "image_url": image_url,
                        "raw_data": json.dumps({"title": title, "price": price, "url": url, "image_url": image_url}, ensure_ascii=False)
                    })

            time.sleep(random.uniform(2, 3))
        except Exception as e:
            print(f"  ✖ Error en ML página {pagina + 1}: {e}")
            break

    return productos

def ejecutar_extraccion_categoria(category: str, store: str, url: str, max_pages: int = 3) -> List[Dict[str, Any]]:
    store_lower = store.lower()
    if "falabella" in store_lower:
        return scrapear_falabella_categoria(category, url, max_pages)
    elif "plaza vea" in store_lower:
        return scrapear_vtex_store(category, "Plaza Vea", "www.plazavea.com.pe", url, max_pages)
    elif "promart" in store_lower:
        return scrapear_vtex_store(category, "Promart", "www.promart.pe", url, max_pages)
    elif "mercado libre" in store_lower:
        return scrapear_mercadolibre_categoria(category, url, max_pages)
    return []
