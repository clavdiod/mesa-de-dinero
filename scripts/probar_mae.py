"""Prueba el calendario de licitaciones de MAE Market Data y busca su fuente de datos."""
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "text/html,application/json"}
out = []
url = "https://marketdata.mae.com.ar/calendario-licitaciones"
try:
    r = requests.get(url, headers=UA, timeout=30)
    html = r.text
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)))
    eps = sorted(set(re.findall(r'["\']((?:https?://[^"\']*)?/(?:api|Api|API|servicios|ws|data)[^"\'\s]{0,120})["\']', html)))
    js = sorted(set(re.findall(r'src="([^"]+\.js[^"]*)"', html)))[:8]
    out.append(f"{r.status_code} {len(html)}b eps={eps[:12]} js={js} texto={t[:1500]}")
    # buscar endpoints dentro de los JS
    for j in js[:6]:
        u = j if j.startswith("http") else "https://marketdata.mae.com.ar" + ("" if j.startswith("/") else "/") + j
        try:
            c = requests.get(u, headers=UA, timeout=30).text
            found = sorted(set(re.findall(r'["\`]((?:https?://[^"\`]*)?/(?:api|Api|API)[^"\`\s]{0,100})["\`]', c)))[:15]
            if found:
                out.append(f"JS {j}: {found}")
        except Exception as e:
            out.append(f"JS {j}: ERROR {e}")
except Exception as e:
    out.append(f"ERROR {type(e).__name__}: {e}")
print("::notice::" + " || ".join(out)[:3900])
