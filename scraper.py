import json
import re
from typing import Optional, Dict, Any
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

def get_request(url: str):
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

def scrape_falabella_pdp(url: str) -> Dict[str, Any]:
    try:
        res = get_request(url)
        if res.status_code != 200:
            return {"store": "Falabella", "url": url, "status": "error", "error": f"HTTP {res.status_code}"}

        soup = BeautifulSoup(res.text, "html.parser")
        next_data = soup.find("script", id="__NEXT_DATA__")
        if next_data and next_data.string:
            data = json.loads(next_data.string)
            pdata = data.get("props", {}).get("pageProps", {}).get("productData", {})
            title = pdata.get("name")
            prices = pdata.get("prices", [])
            price = None
            if prices:
                pval = prices[0].get("price", [None])[0]
                if pval:
                    price = float(re.sub(r"[^\d.]", "", str(pval)))
            
            media = pdata.get("media", [])
            image_url = media[0].get("url") if media else None

            return {
                "store": "Falabella",
                "title": title,
                "price": price,
                "currency": "PEN",
                "in_stock": pdata.get("isAvailable", True),
                "image_url": image_url,
                "url": url,
                "status": "success"
            }
        return {"store": "Falabella", "url": url, "status": "error", "error": "Datos no encontrados"}
    except Exception as e:
        return {"store": "Falabella", "url": url, "status": "error", "error": str(e)}

def scrape_vtex_pdp(store_name: str, url: str) -> Dict[str, Any]:
    try:
        res = get_request(url)
        if res.status_code != 200:
            return {"store": store_name, "url": url, "status": "error", "error": f"HTTP {res.status_code}"}

        soup = BeautifulSoup(res.text, "html.parser")
        scripts = soup.find_all("script", type="application/ld+json")
        for s in scripts:
            if not s.string: continue
            try:
                data = json.loads(s.string)
                if isinstance(data, dict) and data.get("@type") == "Product":
                    offers = data.get("offers", {})
                    price = offers.get("price") or offers.get("lowPrice")
                    title = data.get("name")
                    image = data.get("image")
                    return {
                        "store": store_name,
                        "title": title,
                        "price": float(price) if price else None,
                        "currency": "PEN",
                        "in_stock": True,
                        "image_url": image if isinstance(image, str) else (image[0] if isinstance(image, list) else None),
                        "url": url,
                        "status": "success"
                    }
            except Exception:
                continue

        return {"store": store_name, "url": url, "status": "error", "error": "Schema JSON-LD no encontrado"}
    except Exception as e:
        return {"store": store_name, "url": url, "status": "error", "error": str(e)}

def ejecutar_scraping(store: str, url: str) -> Dict[str, Any]:
    store_lower = store.lower()
    if "falabella" in store_lower:
        return scrape_falabella_pdp(url)
    elif "plaza vea" in store_lower or "promart" in store_lower:
        return scrape_vtex_pdp(store, url)
    return {"store": store, "url": url, "status": "error", "error": "Tienda no soportada"}
