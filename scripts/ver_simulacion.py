"""Resumen de la simulación en papel para diagnóstico (como anotaciones del job). Sin secretos ni datos personales."""
import json
import os
from collections import defaultdict

import requests

base = (os.environ.get("MESA_WORKER_URL") or "https://mesa-de-dinero.clavdio81.workers.dev").rstrip("/")
if not base.startswith("http"):
    base = "https://" + base
h = {"Authorization": f"Bearer {os.environ['MESA_INGESTA_TOKEN']}"}
pos = requests.get(f"{base}/api/kv/sim%2Fposiciones", headers=h, timeout=30).json()
com = 1.2
g = defaultdict(list)
for p in pos:
    if p["estado"] != "abierta":
        continue
    bruto = (p["ultimo"] / p["entrada"] - 1) * 100
    g[(p["origen"], p["setup"], p["semaforo"])].append((p["ticker"], round(bruto, 2), p.get("hora")))
for k, v in g.items():
    prom = sum(x[1] for x in v) / len(v)
    print(f"::notice::{k} n={len(v)} bruto_prom={prom:.2f}% suben={sum(1 for x in v if x[1] > 0)} | " +
          " ".join(f"{t}:{b:+.1f}%@{hh}" for t, b, hh in v)[:700])
print("::notice::estados " + json.dumps({e: sum(1 for p in pos if p['estado'] == e) for e in {p['estado'] for p in pos}}))
