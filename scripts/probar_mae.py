"""Mira el calendario de colocaciones de A3 Mercados y busca de dónde salen los datos."""
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
url = "https://www.a3mercados.com.ar/productos/emisiones-primarias/colocaciones"
r = requests.get(url, headers=UA, timeout=25)
html = r.text
t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)))
urls = sorted(set(re.findall(r'(https?://[a-zA-Z0-9.-]*(?:a3|mae)[a-zA-Z0-9./_?=&-]*)', html)))
endpoints = sorted(set(re.findall(r'["\'](/(?:api|servicios|ws)[^"\'\\]{0,100})', html)))
rsc = [m for m in re.findall(r'(?:Clase|CLASE|licitaci|Licitaci|Fecha de licitaci)[^"\\]{0,160}', html)][:15]
print("::notice::" + f"{r.status_code} {len(html)}b | urls={urls[:20]} | endpoints={endpoints[:15]} | rsc={rsc} | texto={t[:1800]}"[:3900])
