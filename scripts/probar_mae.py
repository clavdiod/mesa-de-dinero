"""¿Por qué no aparecen las ONs en el calendario de licitaciones del MAE?"""
import re
from datetime import date, timedelta

import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
B = "https://api.marketdata.mae.com.ar/api/"
hoy = date.today()
out = []
for d1, d2 in ((hoy - timedelta(days=1), hoy + timedelta(days=45)), (hoy - timedelta(days=2), hoy + timedelta(days=10)), (hoy, hoy + timedelta(days=14))):
    r = requests.get(B + "mercado/licitaciones", headers=H, params={"fechaDesde": d1.isoformat(), "fechaHasta": d2.isoformat()}, timeout=30).json()
    out.append(f"{d1}..{d2}: " + " ; ".join(f"{e['start'][:10]} {e['title'][:40]}" for e in r.get("events") or []))
html = requests.get("https://marketdata.mae.com.ar/", headers=H, timeout=30).text
codigo = ""
for j in set(re.findall(r'(?:src|href)="([^"]+\.js)"', html)):
    codigo += requests.get("https://marketdata.mae.com.ar" + ("" if j.startswith("/") else "/") + j, headers=H, timeout=30).text
for c in list(set(re.findall(r'(?:assets|static/js)/[\w.\-]+\.js', codigo)))[:200]:
    try:
        codigo += requests.get("https://marketdata.mae.com.ar/" + c, headers=H, timeout=20).text
    except Exception:
        pass
for m in list(re.finditer(r"licitacionesporestado|mercado/licitaciones", codigo))[:4]:
    out.append("JS: " + codigo[max(0, m.start() - 300): m.start() + 250].replace("\n", " "))
for est in ("Activa", "Abierta", "Todos", "1", "0", "Vigente", "Proxima", "Cerrada"):
    r = requests.get(B + f"mercado/licitacionesporestado/{est}", headers=H, timeout=20)
    out.append(f"estado {est}: {r.status_code} {r.text[:300]}")
print("::notice::" + " ||| ".join(out)[:3950])
