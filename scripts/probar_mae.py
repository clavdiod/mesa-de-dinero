"""Mira la sección de emisiones primarias de A3 Mercados (ex MAE)."""
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
out = []
for url in ("https://www.a3mercados.com.ar/productos/emisiones-primarias",):
    r = requests.get(url, headers=UA, timeout=25)
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S)
    texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))
    links = sorted(set(re.findall(r'href="([^"]+)"', r.text)))
    rel = [l for l in links if re.search(r"licit|coloca|primari|emisi|calend|aviso", l, re.I)][:25]
    apis = sorted(set(re.findall(r'["\'](/?(?:api|_next|wp-json|graphql)[^"\']{0,80})["\']', r.text)))[:15]
    i = texto.lower().find("licit")
    out.append(f"{r.status_code} {len(r.text)}b | links={rel} | apis={apis} | texto: {texto[max(0, i - 300):i + 1500]}")
print("::notice::" + " || ".join(out)[:3900])
