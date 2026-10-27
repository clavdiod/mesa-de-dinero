"""Cómo vienen de verdad el Anticipador, el Anticipo NY, el Jefe y el resto (libreta, simulación y propuestas)."""
import json, statistics as st
from collections import defaultdict
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
lib = a.get("pronosticos/libreta") or []
por = defaultdict(lambda: defaultdict(list))
for x in lib:
    por[x["origen"]][x["fecha"]].append(x)
for o, dias in por.items():
    filas = []
    for f in sorted(dias)[-8:]:
        xs = dias[f]
        c = lambda e: sum(1 for x in xs if x["estado"] == e)
        va = [x.get("ahora_pct") for x in xs if x.get("ahora_pct") is not None and x.get("ref")]
        mej = [x.get("mejor") for x in xs if x.get("ref")]
        filas.append(f"{f[5:]}: n{len(xs)} ok{c('se_dio')} fallo{c('fallo')} nose{c('no_se_dio')} curso{c('en_curso')+c('esperando')} va{st.mean(va):+.1f} mejor{st.mean(mej):+.1f}" if va else f"{f[5:]}: n{len(xs)} sin ref")
    print(f"::notice::{o}: " + " | ".join(filas))
props = a.get("registro/propuestas") or []
print("::notice::JEFE " + " | ".join(f"{p['fecha'][5:]} {p['ticker']} {p['seguimiento'].get('estado')} r={p['seguimiento'].get('r_actual', p['seguimiento'].get('r_neto'))} dec={p.get('decision')}" for p in props[-25:]))
sim = a.get("sim/resumen") or {}
print("::notice::SIM " + json.dumps({k: sim.get(k) for k in ("total", "abiertas", "latente", "por_agente")}, ensure_ascii=False)[:2500])
est = a.get("anticipo/estadistica") or {}
print("::notice::ANTICIPO_EST " + json.dumps(est, ensure_ascii=False)[:800])
mod = a.get("anticipo/modelo") or {}
print("::notice::MODELO " + json.dumps({k: mod.get(k) for k in ("activo", "umbral", "prueba", "motivo")}, ensure_ascii=False)[:800])
