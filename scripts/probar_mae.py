"""Buscar en MAE los papeles sin flujo (códigos alternativos y avisos de pago)."""
import json

import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
B = "https://api.marketdata.mae.com.ar/api/"
q = lambda o: json.dumps(o, separators=(",", ":"))
out = []
for t in ("PR17", "BAF27", "BAO27", "SCX3", "SC3", "CORDOBA"):
    act = requests.get(B + f"mercado/titulosactivos?oTitulo={q({'titulo': t})}", headers=H, timeout=20).json()
    out.append(f"{t}: " + " ; ".join(f"{x['codTitulo']}={x['descripcion']}" for x in act[:8]))
pagos = requests.get(B + "mercado/pagoamortizrenta", headers=H, timeout=30).json()
out.append("PAGOS: " + " ; ".join(f"{p['fecha'][:10]} {p['titulo']}" for p in pagos if any(w in (p.get('empresa') or '') + p['titulo'] for w in ("CORDOBA", "Cordoba", "Consolid", "SCX", "Scania"))))
for tk in ("PR17", "BAF27", "BAO27"):
    r = requests.get(B + f"emisiones/flujofondos/{tk}", headers=H, timeout=20).json()
    out.append(f"FF {tk}: {len(r.get('detalle') or [])}")
print("::notice::" + " ||| ".join(out)[:3950])
