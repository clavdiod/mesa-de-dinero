"""Autopsia del día: qué dijo cada analista, qué filtró Riesgo y el Jefe, y cómo va cada operación simulada.
Imprime anotaciones sin secretos ni datos personales."""
import json
import os
from datetime import datetime, timedelta, timezone

import requests

base = (os.environ.get("MESA_WORKER_URL") or "https://mesa-de-dinero.clavdio81.workers.dev").rstrip("/")
if not base.startswith("http"):
    base = "https://" + base
h = {"Authorization": f"Bearer {os.environ['MESA_INGESTA_TOKEN']}"}


def kv(k, d=None):
    r = requests.get(f"{base}/api/kv/{requests.utils.quote(k, safe='')}", headers=h, timeout=30)
    return r.json() if r.ok else d


hoy = (datetime.now(timezone.utc) - timedelta(hours=3)).date().isoformat()
est = kv("ui/estado", {})
pos = kv("sim/posiciones", [])
deb = kv("ui/debates", {})
desc = kv(f"jefe/descartes/{hoy}", {})
props = kv("registro/propuestas", [])
out = []
out.append(f"ronda {est.get('fecha')} {est.get('hora')} clima={est.get('clima')} rp={(est.get('riesgo_pais') or {}).get('valor')} "
           f"propuestas_hoy={sum(1 for p in props if p.get('fecha') == hoy)} descartes_jefe={desc}")
for e in est.get("evaluados", []):
    r = e.get("riesgo") or {}
    out.append(f"EVAL {e['ticker']} puntaje={e['puntaje']} ok={r.get('ok')} rneto={r.get('r_neto')} motivos={r.get('motivos')} avisos={r.get('avisos')}")
sen = est.get("senales", [])
tks = sorted({p["ticker"] for p in pos if p["fecha"] == hoy})
for tk in tks:
    p = next(x for x in pos if x["ticker"] == tk)
    ss = [f"{s['agente']}({s['direccion']:+d},{s['fuerza']:.2f}):{s['texto'][:110]}" for s in sen if s["ticker"] == tk]
    d = deb.get(tk) or {}
    sup = (d.get("supervisor") or {}).get("titulo")
    out.append(f"SIM {tk} {p['origen']}/{p['setup']} sem={p['semaforo']} {p.get('hora')} entrada={p['entrada']} ult={p.get('ultimo')} "
               f"precio={(p.get('ultimo', p['entrada']) / p['entrada'] - 1) * 100:+.2f}% obj={p['objetivo']} stop={p['stop']} "
               f"agentes={p.get('agentes')} supervisor={sup} || " + " | ".join(ss))
for tk in tks:
    c = kv(f"cache/diario/{tk}", [])
    if c:
        u = c[-25:]
        out.append(f"HIST {tk} n={len(c)} cierres25=" + ",".join(f"{v['cierre']:g}" for v in u) +
                   f" vol5=" + ",".join(f"{(v.get('volumen') or 0):.0f}" for v in u[-5:]))
for o in out:
    for i in range(0, len(o), 3500):
        print("::notice::" + o[i:i + 3500])
