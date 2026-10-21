"""Lee el módulo useLicitacionesCalendar de MAE Market Data para encontrar la ruta de la API y la prueba."""
import re
from datetime import date, timedelta

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar",
      "Referer": "https://marketdata.mae.com.ar/"}
c = requests.get("https://marketdata.mae.com.ar/assets/useLicitacionesCalendar-DCUzzxDC.js", headers=UA, timeout=40).text
out = [f"modulo {len(c)}b: {c[:1500]}"]
rutas = sorted(set(re.findall(r'["\'`]([a-zA-Z0-9/_${}.?=&:-]*(?:licit|calend|Licit)[a-zA-Z0-9/_${}.?=&:-]*)["\'`]', c)))
out.append(f"rutas={rutas}")
hoy = date.today()
for r in rutas[:8]:
    for u in (f"https://api.marketdata.mae.com.ar/api/{r.lstrip('/')}",):
        u = u.replace("${", "{")
        u = re.sub(r"\{[^}]*\}", "", u)
        try:
            rr = requests.get(u, headers=UA, timeout=20, params={"fechaDesde": hoy.isoformat(), "fechaHasta": (hoy + timedelta(days=14)).isoformat()})
            out.append(f"GET {rr.url} -> {rr.status_code} {rr.text[:400]!r}")
        except Exception as e:
            out.append(f"GET {u} -> ERROR {type(e).__name__}")
print("::notice::" + " || ".join(out)[:3900])
