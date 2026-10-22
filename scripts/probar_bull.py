"""¿Bull Market publica el flujo de fondos en la página o por una API?"""
import re

import requests

H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
r = requests.get("https://inversiones.bullmarket.com.ar/Cotizaciones/Bonos/baf27", headers=H, timeout=30)
t = r.text
urls = sorted(set(re.findall(r'["\'](/[A-Za-z0-9_/\-]*(?:Flujo|flujo|Calcul|calcul|Bono|bono)[A-Za-z0-9_/\-?=&.]*)["\']', t)))
print("::notice::" + f"{r.status_code} {len(t)} bytes || rutas: {urls[:40]} || " + " ".join(re.findall(r".{80}(?:flujo|Flujo|amortiz).{120}", t)[:6])[:2500])
