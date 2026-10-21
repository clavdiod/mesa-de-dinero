"""Muestra la calibración de los agentes (sin secretos)."""
import json
import os

import requests

base = (os.environ.get("MESA_WORKER_URL") or "https://mesa-de-dinero.clavdio81.workers.dev").rstrip("/")
if not base.startswith("http"):
    base = "https://" + base
h = {"Authorization": f"Bearer {os.environ['MESA_INGESTA_TOKEN']}"}
cal = requests.get(f"{base}/api/kv/ranking%2Fcalibracion", headers=h, timeout=30).json()
hist = requests.get(f"{base}/api/kv/ranking%2Fstats_historicas", headers=h, timeout=30).json()
print("::notice::" + json.dumps({"calibracion": cal, "historia": hist}, ensure_ascii=False)[:3900])
