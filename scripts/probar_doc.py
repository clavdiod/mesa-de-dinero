"""Prueba el proxy de documentos del Worker con un PDF de A3."""
import os

import requests

base = (os.environ.get("MESA_WORKER_URL") or "https://mesa-de-dinero.clavdio81.workers.dev").rstrip("/")
if not base.startswith("http"):
    base = "https://" + base
H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
d = requests.get("https://api.marketdata.mae.com.ar/api/mercado/boletin-mpmae", headers=H, timeout=30).json()[0]
r = requests.get(f"{base}/api/doc", params={"u": d["url"], "n": "prueba"}, headers={"Authorization": f"Bearer {os.environ['MESA_INGESTA_TOKEN']}"}, timeout=60)
print(f"::notice::{r.status_code} {r.headers.get('content-type')} {len(r.content)} bytes pdf={r.content[:4] == b'%PDF'} {r.text[:200] if r.content[:4] != b'%PDF' else ''}")
