"""Detalle de licitación: ¿responde?"""
from datetime import date, timedelta

import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
B = "https://api.marketdata.mae.com.ar/api/"
hoy = date.today()
ev = requests.get(B + "mercado/licitaciones", headers=H, params={"fechaDesde": hoy.isoformat(), "fechaHasta": (hoy + timedelta(days=10)).isoformat()}, timeout=30).json()["events"]
out = []
for e in ev[:4]:
    r = requests.get(B + f"mercado/licitacion/{e['id']}", headers=H, timeout=20)
    out.append(f"{e['id']} {e['title'][:30]} -> {r.status_code} {r.text[:160]}")
print("::notice::" + " || ".join(out))
