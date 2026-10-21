"""Busca en el sitio de MAE/A3 la sección pública de licitaciones (colocaciones primarias)."""
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
out = []
for url in ("https://www.mae.com.ar/", "https://www.mae.com.ar/mercado-primario/licitaciones", "https://www.mae.com.ar/mercado-primario",
            "https://www.a3mercados.com.ar/", "https://servicios.mae.com.ar/"):
    try:
        r = requests.get(url, headers=UA, timeout=25)
        links = sorted(set(re.findall(r'href="([^"]*(?:licitac|colocac|primari)[^"]*)"', r.text, re.I)))[:12]
        apis = sorted(set(re.findall(r'(https?://[^"\']*(?:api|ws|json)[^"\']*)', r.text, re.I)))[:6]
        out.append(f"{url} -> {r.status_code} {len(r.text)}b links={links} apis={apis}")
    except Exception as e:
        out.append(f"{url} -> ERROR {type(e).__name__}")
print("::notice::" + " || ".join(out)[:3900])
