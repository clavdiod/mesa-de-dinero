"""Inventario de la API pública de MAE market data: rutas que usa la web y qué devuelven."""
import re
from datetime import date, timedelta

import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar",
     "Referer": "https://marketdata.mae.com.ar/"}
B = "https://api.marketdata.mae.com.ar/api/"
html = requests.get("https://marketdata.mae.com.ar/", headers=H, timeout=30).text
js = set(re.findall(r'(?:src|href)="([^"]+\.js)"', html))
codigo = ""
for j in js:
    u = j if j.startswith("http") else "https://marketdata.mae.com.ar" + ("" if j.startswith("/") else "/") + j
    codigo += requests.get(u, headers=H, timeout=30).text
# trozos importados (lazy)
for c in set(re.findall(r'"(assets/[^"]+\.js)"', codigo))[:80] if False else list(set(re.findall(r'(?:assets|static/js)/[\w.\-]+\.js', codigo)))[:120]:
    try:
        codigo += requests.get("https://marketdata.mae.com.ar/" + c, headers=H, timeout=20).text
    except Exception:
        pass
rutas = sorted(set(re.findall(r'["`/]((?:mercado|cotizaciones|instrumentos|especies|licitaciones|indices|renta|cauciones|forex|repo|series|historico|boletin|resumen|panel|monedas|tasas|futuros|negociacion)[\w/\-${}.?=&]*)', codigo)))
print("::notice::RUTAS " + str(len(rutas)) + " || " + " | ".join(rutas)[:3900])
hoy = date.today()
pruebas = {}
for r in rutas:
    base = re.sub(r"\$\{[^}]*\}", "", r).split("?")[0].rstrip("/")
    if not base or base in pruebas or "licitacion" in base:
        continue
    try:
        x = requests.get(B + base, headers=H, timeout=15,
                         params={"fechaDesde": (hoy - timedelta(days=3)).isoformat(), "fechaHasta": hoy.isoformat(),
                                 "fecha": hoy.isoformat()})
        pruebas[base] = f"{x.status_code} {x.text[:220]!r}"
    except Exception as e:
        pruebas[base] = f"ERR {e}"
items = [f"{k} -> {v}" for k, v in pruebas.items()]
for i in range(0, len(items), 8):
    print("::notice::PRUEBA " + " || ".join(items[i:i + 8])[:3900])
