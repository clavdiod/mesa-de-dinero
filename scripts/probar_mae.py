"""Texto de los avisos de suscripción (para diseñar el resumen)."""
import io
import re

import requests
from pypdf import PdfReader

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
docs = requests.get("https://api.marketdata.mae.com.ar/api/mercado/boletin-mpmae", headers=H, timeout=30).json()
for pat in (r"COLGAS.*Suscrip", r"AGROCAP.*Suscrip"):
    d = next((d for d in docs if re.search(pat, d["titulo"], re.I)), None)
    if not d:
        print(f"::notice::{pat}: no está")
        continue
    u = d["url"] + ("&" if "?" in d["url"] else "?") + "download=1"
    pdf = requests.get(u, timeout=60, headers={"User-Agent": "Mozilla/5.0"}).content
    txt = re.sub(r"\s+", " ", " ".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(pdf)).pages[:8]))
    for i in range(0, min(len(txt), 11000), 3800):
        print(f"::notice::{pat} [{i}] " + txt[i:i + 3800])
