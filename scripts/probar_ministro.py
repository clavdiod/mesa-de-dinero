"""Series del BCRA v4 y titulares del ministro."""
import json

import requests

out = []
for i in (1, 47, 5, 44, 27, 29):
    r = requests.get(f"https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/{i}", params={"desde": "2025-01-01", "hasta": "2026-10-23", "limit": 3000}, timeout=40)
    j = r.json()
    res = j.get("results")
    out.append(f"id {i}: {r.status_code} keys {list(j)[:5]} tipo {type(res).__name__} " + json.dumps(res if not isinstance(res, list) else res[:2], ensure_ascii=False)[:400] + f" n={len(res) if isinstance(res, list) else (len(res.get('detalle', [])) if isinstance(res, dict) else '?')} meta={json.dumps(j.get('metadata'))[:150]}")
print("::notice::" + " ||| ".join(out)[:3950])
from mesa.datos import gratis
ns = gratis.buscar_noticias("Caputo ministro de Economía", horas=48, max_items=10)
ns += gratis.buscar_noticias("licitación Tesoro rollover", horas=168, max_items=8)
print("::notice::NOTICIAS " + " | ".join(n["titulo"][:110] for n in ns)[:3900])
