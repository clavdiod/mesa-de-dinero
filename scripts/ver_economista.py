"""Muestra la clase del Economista de la última ronda."""
import json
import os

import requests

base = (os.environ.get("MESA_WORKER_URL") or "https://mesa-de-dinero.clavdio81.workers.dev").rstrip("/")
if not base.startswith("http"):
    base = "https://" + base
h = {"Authorization": f"Bearer {os.environ['MESA_INGESTA_TOKEN']}"}
e = requests.get(f"{base}/api/kv/ui%2Festado", headers=h, timeout=30).json()
r = e.get("economista") or {}
print("::notice::" + f"ronda {e.get('hora')} " + json.dumps({k: r.get(k) for k in ("titulo", "inclinacion", "clase", "ensena", "ensenanza_activa", "ensenanza_motivo")}, ensure_ascii=False)[:3800])
