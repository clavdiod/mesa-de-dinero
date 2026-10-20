"""Detalle de casos puntuales (TXAR, METR, HOOD, SE): propuesta del Jefe, señales e historial."""
import json
import os

import requests

base = (os.environ.get("MESA_WORKER_URL") or "https://mesa-de-dinero.clavdio81.workers.dev").rstrip("/")
if not base.startswith("http"):
    base = "https://" + base
h = {"Authorization": f"Bearer {os.environ['MESA_INGESTA_TOKEN']}"}


def kv(k, d=None):
    r = requests.get(f"{base}/api/kv/{requests.utils.quote(k, safe='')}", headers=h, timeout=30)
    return r.json() if r.ok else d


props = kv("registro/propuestas", [])
partes = []
for p in props[:3]:
    q = {k: p.get(k) for k in ("fecha", "hora", "ticker", "puntaje", "plan", "riesgo", "debate", "resumen_jefe", "confianza", "seguimiento")}
    q["senales"] = [f"{s['agente']}({s['direccion']:+d},{s['fuerza']:.2f}):{s['texto'][:140]}" for s in p.get("senales", [])]
    partes.append("PROP " + json.dumps(q, ensure_ascii=False))
for tk in ("TXAR", "METR", "HOOD", "SE"):
    c = kv(f"cache/diario/{tk}", [])
    partes.append(f"HIST {tk} n={len(c)} " + ",".join(f"{v['fecha'][5:]}:{v['cierre']:g}" for v in c[-30:]))
texto = " ##### ".join(partes)
for i in range(0, len(texto), 3900):
    print("::notice::" + texto[i:i + 3900])
