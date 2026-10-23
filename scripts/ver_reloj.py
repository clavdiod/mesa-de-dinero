"""¿El Worker responde y puede escribir en KV?"""
import os
import time

import requests

base = (os.environ.get("MESA_WORKER_URL") or "https://mesa-de-dinero.clavdio81.workers.dev").rstrip("/")
if not base.startswith("http"):
    base = "https://" + base
h = {"Authorization": f"Bearer {os.environ['MESA_INGESTA_TOKEN']}"}
v = str(time.time())
w = requests.put(f"{base}/api/kv/prueba%2Fescritura", data=f'"{v}"', headers=h, timeout=30)
r = requests.get(f"{base}/api/kv/prueba%2Fescritura", headers=h, timeout=30)
e = requests.get(f"{base}/api/kv/ui%2Festado", headers=h, timeout=30)
print(f"::notice::PUT {w.status_code} {w.text[:200]} || GET {r.status_code} {r.text[:80]} igual={v in r.text} || estado {e.status_code} {e.text[:120]}")
