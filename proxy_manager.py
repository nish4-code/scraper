import os
import random
from typing import Optional, Dict

PROXY_FILE = "proxies.txt"

class ProxyManager:
    def __init__(self, proxy_file: str = PROXY_FILE):
        self.proxy_file = proxy_file
        self.proxies = []
        self.load_proxies()

    def load_proxies(self):
        """Carga la lista de proxies desde el archivo text proxies.txt."""
        if not os.path.exists(self.proxy_file):
            self.proxies = []
            return

        with open(self.proxy_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        valid_proxies = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                valid_proxies.append(line)
        
        self.proxies = valid_proxies
        if self.proxies:
            print(f"  🌐 [ProxyManager] Se cargaron {len(self.proxies)} proxies activos.")

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """Devuelve un proxy aleatorio en formato dict para requests/curl_cffi, o None si no hay."""
        if not self.proxies:
            return None
        proxy_url = random.choice(self.proxies)
        return {"http": proxy_url, "https": proxy_url}

proxy_manager = ProxyManager()
