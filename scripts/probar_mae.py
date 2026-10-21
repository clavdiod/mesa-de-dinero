"""Pruebas concretas de rutas públicas del MAE."""
import json
import re
from datetime import date, timedelta

import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
B = "https://api.marketdata.mae.com.ar/api/"
html = requests.get("https://marketdata.mae.com.ar/", headers=H, timeout=30).text
codigo = ""
for j in set(re.findall(r'(?:src|href)="([^"]+\.js)"', html)):
    codigo += requests.get("https://marketdata.mae.com.ar" + ("" if j.startswith("/") else "/") + j, headers=H, timeout=30).text
m = re.search(r'aw\s*=\s*(\{[^}]{0,400}\})', codigo) or re.search(r'(\{[^{}]{0,300}"/rentafija"[^{}]{0,300}\})', codigo)
print("::notice::MAPA " + (m.group(1)[:800] if m else "no") + " || SEGMENTOS " + " ".join(sorted(set(re.findall(r'"/(rentafija\w*|forex\w*|cauciones\w*|repo\w*|futuros\w*|derivados\w*)"', codigo)))))
hoy = date.today()
d3 = (hoy - timedelta(days=5)).isoformat()
q = lambda o: json.dumps(o, separators=(",", ":"))
casos = ["mercado/datos/rentafija", "mercado/datos/RF", "mercado/datos/forex", "mercado/datos/cauciones", "mercado/resumen/rentafija", "mercado/resumen/RF",
         "mercado/volumen", "mercado/volumen-categoria/rentafija", f"mercado/titulo/historicorentafija?oTitulo={q({'fechaDesde': d3, 'fechaHasta': hoy.isoformat()})}",
         f"mercado/titulosactivos?oTitulo={q({'titulo': 'YM'})}", "mercado/pagoamortizrenta", "mercado/boletin-mpmae", "mercado/inforelevante",
         f"mercado/historico/preciocierre?oTitulo={q({'fechaDesde': d3, 'fechaHasta': hoy.isoformat()})}"]
out = []
for c in casos:
    try:
        x = requests.get(B + c, headers=H, timeout=25)
        t = x.text
        n = ""
        try:
            jj = x.json(); n = f"[{len(jj)} items]" if isinstance(jj, list) else f"[keys {list(jj)[:8]}]"
        except Exception:
            pass
        out.append(f"{c[:70]} -> {x.status_code} {n} {t[:330]!r}")
    except Exception as e:
        out.append(f"{c} -> ERR {e}")
for i in range(0, len(out), 4):
    print("::notice::" + " ##### ".join(out[i:i + 4])[:3950])
