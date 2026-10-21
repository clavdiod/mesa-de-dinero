"""Muestra la clase del Economista de la última ronda."""
import json
import os

import requests

base = (os.environ.get("MESA_WORKER_URL") or "https://mesa-de-dinero.clavdio81.workers.dev").rstrip("/")
if not base.startswith("http"):
    base = "https://" + base
h = {"Authorization": f"Bearer {os.environ['MESA_INGESTA_TOKEN']}"}
e = requests.get(f"{base}/api/kv/ui%2Festado", headers=h, timeout=30).json()
w = e.get("wallstreet") or {}
ws = [s for s in e.get("senales", []) if s.get("agente") == "wallstreet"]
print("::notice::" + f"ronda {e.get('hora')} " + json.dumps({k: w.get(k) for k in ("titulo", "riesgo", "clase", "ensena", "ensenanza_activa")}, ensure_ascii=False)[:2500]
      + " | señales WS: " + " ; ".join(f"{s['ticker']} {s['direccion']:+d} {s['texto'][:90]}" for s in ws[:6]))
