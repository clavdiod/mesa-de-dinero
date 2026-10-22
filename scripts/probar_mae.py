"""Flujos de fondos desde MAE: detalle de título -> id de emisión -> emisiones/flujofondos/{id}."""
import json

import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
B = "https://api.marketdata.mae.com.ar/api/"
q = lambda o: json.dumps(o, separators=(",", ":"))
out = []
for tk in ("TTD26", "YM34O", "AL30", "S13N6"):
    act = requests.get(B + f"mercado/titulosactivos?oTitulo={q({'titulo': tk})}", headers=H, timeout=20).json()
    m = next((x for x in act if x["codTitulo"].strip() == tk), act[0] if act else None)
    out.append(f"{tk} activos: {json.dumps(m)[:250]}")
    if not m:
        continue
    for extra in ({"tipoNegociacion": "TRD"}, {"tipoNegociacion": "F"}, {}):
        o = {"codTitulo": tk, "tipoEmision": m.get("tipoEspecie") or m.get("tipoEmision"), "plazo": m.get("plazo"), "moneda": m.get("moneda"), "segmento": m.get("codSegmento"), **extra}
        d = requests.get(B + f"mercado/titulo/detalle?oTitulo={q(o)}", headers=H, timeout=20)
        out.append(f"  detalle {extra}: {d.status_code} {d.text[:700]}")
        if d.status_code == 200 and d.text.strip():
            break
print("::notice::" + " ||| ".join(out)[:3950])
