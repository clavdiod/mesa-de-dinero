"""¿Se pueden bajar los PDF de MAE (SharePoint) y leer las condiciones?"""
import io
import re

import requests
from pypdf import PdfReader

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
docs = requests.get("https://api.marketdata.mae.com.ar/api/mercado/boletin-mpmae", headers=H, timeout=30).json()
out = []
for d in docs[:40]:
    if not re.search(r"COLGAS|AGROCAP", d["titulo"], re.I) or not re.search(r"Aviso|Suplemento", d["titulo"], re.I):
        continue
    u = d["url"]
    for url in (u + ("&" if "?" in u else "?") + "download=1", u):
        r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
        ct = r.headers.get("content-type", "")
        ok = r.content[:4] == b"%PDF"
        out.append(f"{d['titulo'][:60]} | {url[-30:]} -> {r.status_code} {ct[:30]} pdf={ok} {len(r.content)}B final={r.url[:80]}")
        if ok:
            txt = " ".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(r.content)).pages[:6])
            txt = re.sub(r"\s+", " ", txt)
            out.append("TXT " + txt[:1500])
            break
    if len(out) > 8:
        break
print("::notice::" + " ||| ".join(out)[:3950])
