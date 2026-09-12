import json
import os
import httpx
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

def generar_enlace_afiliado(store: str, url: str) -> str:
    """Adjunta la etiqueta de afiliado correspondiente según la tienda y las variables de entorno en .env."""
    store_key = store.upper().replace(" ", "")
    env_var_name = f"AFFILIATE_TAG_{store_key}"
    tag = os.getenv(env_var_name, "")

    if tag and not tag.startswith("tag_") and not tag.startswith("PENDIENTE"):
        if "?" in url:
            return f"{url}&tag={tag}"
        else:
            return f"{url}?tag={tag}"
    return url

def enviar_alerta_telegram(oferta: Dict[str, Any]) -> bool:
    """
    Envía una alerta estructurada de oferta a Telegram con foto, formato HTML y botón de compra con afiliado.
    """
    load_dotenv()
    
    enabled_str = os.getenv("TELEGRAM_ENABLED", "true").lower()
    enabled = enabled_str in ["true", "1", "yes"]
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not enabled or not bot_token or bot_token.startswith("7123456789") or "TU_BOT_TOKEN" in bot_token:
        print(f"  ℹ [Telegram] Alerta detectada (Telegram sin Token o deshabilitado en .env): {oferta['title'][:45]}... S/{oferta['precio_actual']}")
        return False

    title = oferta.get("title", "Producto Tech")
    store = oferta.get("store", "Tienda Tech")
    precio_actual = oferta.get("precio_actual", 0.0)
    precio_anterior = oferta.get("precio_anterior")
    descuento_pct = oferta.get("descuento_pct", 0.0)
    url_base = oferta.get("url", "#")
    url_afiliado = generar_enlace_afiliado(store, url_base)
    image_url = oferta.get("image_url")

    precio_orig_str = f"<s>S/ {precio_anterior:,.2f}</s> " if precio_anterior else ""
    
    mensaje_html = (
        f"🔥 <b>¡OFERTA DETECTADA! [-{descuento_pct:.1f}%]</b>\n\n"
        f"📱 <b>{title}</b>\n\n"
        f"💰 <b>Precio Oferta: S/ {precio_actual:,.2f} PEN</b> {precio_orig_str}\n"
        f"🏬 <b>Tienda:</b> {store}\n\n"
        f"⚡ <i>¡Liquidación en tiempo real!</i>"
    )

    api_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto" if image_url else f"https://api.telegram.org/bot{bot_token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {
                        "text": "🛒 Ver Oferta en " + store,
                        "url": url_afiliado
                    }
                ]
            ]
        }
    }

    if image_url:
        payload["photo"] = image_url
        payload["caption"] = mensaje_html
    else:
        payload["text"] = mensaje_html

    try:
        res = httpx.post(api_url, json=payload, timeout=10)
        if res.status_code == 200:
            print(f"  ✔ [Telegram] Alerta enviada con éxito: {title[:40]}...")
            return True
        else:
            print(f"  ✖ [Telegram] Error HTTP {res.status_code}: {res.text[:100]}")
            return False
    except Exception as e:
        print(f"  ✖ [Telegram] Error de envío: {e}")
        return False
