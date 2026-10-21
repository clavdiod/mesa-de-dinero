"""Muestra las alertas del Radar de la última ronda."""
import os

import requests

base = (os.environ.get("MESA_WORKER_URL") or "https://mesa-de-dinero.clavdio81.workers.dev").rstrip("/")
if not base.startswith("http"):
    base = "https://" + base
h = {"Authorization": f"Bearer {os.environ['MESA_INGESTA_TOKEN']}"}
e = requests.get(f"{base}/api/kv/ui%2Festado", headers=h, timeout=30).json()
rs = e.get("radar") or []
print("::notice::" + f"ronda {e.get('hora')} radar={len(rs)} | " + " || ".join(
    f"[{r['severidad']}] {r['texto']} → {r['conclusion']} ({r['favor']}+/{r['contra']}-; noticias {len(r.get('noticias') or [])})" for r in rs[:8])[:3800])
