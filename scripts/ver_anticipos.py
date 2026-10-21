"""Muestra los anticipos de la última ronda."""
import os

import requests

base = (os.environ.get("MESA_WORKER_URL") or "https://mesa-de-dinero.clavdio81.workers.dev").rstrip("/")
if not base.startswith("http"):
    base = "https://" + base
h = {"Authorization": f"Bearer {os.environ['MESA_INGESTA_TOKEN']}"}
e = requests.get(f"{base}/api/kv/ui%2Festado", headers=h, timeout=30).json()
at = e.get("anticipos") or []
print("::notice::" + f"ronda {e.get('hora')} anticipos={len(at)} | " + " ; ".join(
    f"{a['ticker']} NY {a['us']:+.1f}% CEDEAR {a['cedear']:+.1f}% falta {a['atraso']:+.1f}%" for a in at[:10]))
