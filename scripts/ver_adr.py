"""Muestra las fotos de ADRs de hoy y la brecha en vivo de la última ronda."""
import json
import os
from datetime import datetime, timedelta, timezone

import requests

base = (os.environ.get("MESA_WORKER_URL") or "https://mesa-de-dinero.clavdio81.workers.dev").rstrip("/")
if not base.startswith("http"):
    base = "https://" + base
h = {"Authorization": f"Bearer {os.environ['MESA_INGESTA_TOKEN']}"}
hoy = (datetime.now(timezone.utc) - timedelta(hours=3)).date().isoformat()
g = lambda k: requests.get(f"{base}/api/kv/{requests.utils.quote(k, safe='')}", headers=h, timeout=30)
fotos = g(f"adr/fotos/{hoy}")
fotos = fotos.json() if fotos.ok else []
e = g("ui/estado").json()
print("::notice::" + f"fotos hoy: {len(fotos)} ({[f['hora'] for f in fotos]}) | última: {json.dumps(fotos[-1] if fotos else {}, ensure_ascii=False)[:1200]} | en vivo: {json.dumps((e.get('adr') or {}).get('vivo'), ensure_ascii=False)[:1200]}")
