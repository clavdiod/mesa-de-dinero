"""Busca en el código de MAE Market Data la ruta de la API del calendario de licitaciones y la prueba."""
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "application/json"}
c = requests.get("https://marketdata.mae.com.ar/assets/index-DseC26QM.js", headers=UA, timeout=40).text
frag = []
for m in re.finditer(r"licitac|calendario|Licitac", c):
    frag.append(c[max(0, m.start() - 120): m.start() + 160].replace("\n", " "))
rutas = sorted(set(re.findall(r'["\'`](/?[a-zA-Z0-9/_-]*(?:licitac|calendari|colocac|primari)[a-zA-Z0-9/_?=&${}.-]*)["\'`]', c, re.I)))
out = [f"rutas={rutas[:30]}", "frag=" + " ## ".join(frag[:8])[:2000]]
base = "https://api.marketdata.mae.com.ar/api/"
for ruta in [r for r in rutas if "/" in r or r.islower()][:12]:
    u = base + ruta.lstrip("/").split("${")[0]
    try:
        rr = requests.get(u, headers=UA, timeout=20)
        out.append(f"GET {u} -> {rr.status_code} {rr.text[:300]!r}")
    except Exception as e:
        out.append(f"GET {u} -> ERROR {type(e).__name__}")
print("::notice::" + " || ".join(out)[:3900])
