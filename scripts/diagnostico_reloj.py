"""Diagnóstico del reloj de Cloudflare: ¿el cron corre? ¿el disparo a GitHub funciona? No imprime secretos."""
import json
import os

import requests

base = (os.environ.get("MESA_WORKER_URL") or "https://mesa-de-dinero.clavdio81.workers.dev").rstrip("/")
if not base.startswith("http"):
    base = "https://" + base
h = {"Authorization": f"Bearer {os.environ['MESA_INGESTA_TOKEN']}"}
for k in ("reloj/latido", "reloj/log"):
    r = requests.get(f"{base}/api/kv/{requests.utils.quote(k, safe='')}", headers=h, timeout=20)
    txt = r.text if r.ok else f"HTTP {r.status_code}"
    print(f"::notice::{k}: {txt[:900]}")
cf, acc = os.environ.get("CLOUDFLARE_API_TOKEN"), os.environ.get("CLOUDFLARE_ACCOUNT_ID")
if cf and acc:
    r = requests.get(f"https://api.cloudflare.com/client/v4/accounts/{acc}/workers/scripts/mesa-de-dinero/schedules",
                     headers={"Authorization": f"Bearer {cf}"}, timeout=20)
    d = r.json()
    print(f"::notice::crons en Cloudflare: {json.dumps(d.get('result'), ensure_ascii=False)[:600]} errores: {d.get('errors')}")
