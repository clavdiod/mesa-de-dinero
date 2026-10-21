"""Calendario de licitaciones de MAE: lista y detalle."""
import json
from datetime import date, timedelta

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar",
      "Referer": "https://marketdata.mae.com.ar/"}
B = "https://api.marketdata.mae.com.ar/api/"
hoy = date.today()
r = requests.get(B + "mercado/licitaciones", headers=UA, params={"fechaDesde": (hoy - timedelta(days=2)).isoformat(),
                                                                  "fechaHasta": (hoy + timedelta(days=10)).isoformat()}, timeout=30).json()
ev = r.get("events") or []
out = [f"{len(ev)} eventos: " + " | ".join(f"{e['start'][:16]} {e['title'][:70]} (id {e['id']})" for e in ev[:20])]
if ev:
    i = ev[0]["id"]
    for ruta in (f"mercado/licitaciones/{i}", f"mercado/licitaciones/detalle/{i}", f"licitaciones/{i}", f"mercado/licitacion/{i}"):
        try:
            d = requests.get(B + ruta, headers=UA, timeout=20)
            out.append(f"{ruta} -> {d.status_code} {d.text[:600]!r}")
        except Exception as e:
            out.append(f"{ruta} -> ERROR {e}")
print("::notice::" + " || ".join(out)[:3900])
