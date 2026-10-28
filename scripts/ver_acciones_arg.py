"""Lo que dice la mesa ahora de las acciones argentinas."""
import json
from collections import defaultdict
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
e = a.get("ui/estado") or {}
pre = e.get("precios") or {}
acc = {tk for tk, p in pre.items() if p.get("grupo") == "acciones"}
print(f"::notice::ronda {e.get('hora')} clima {e.get('clima')} riesgo país {(e.get('riesgo_pais') or {}).get('valor')} (ayer {e.get('riesgo_pais_ayer')})")
la = (e.get("anticipo_listas") or {}).get("anticipador_arg") or {}
print("::notice::ARG " + " | ".join(f"#{x.get('prioridad')} {x['ticker']} prob {x['prob']} plan {x.get('plan')} hasta {x.get('vence')} {x.get('razones')}" for x in la.get("lista") or []))
ops = [o for l in (e.get("oportunidades") or {}).values() for o in l if o["ticker"] in acc]
print("::notice::OPS " + " | ".join(f"{o['ticker']} {o.get('setup')} {o.get('semaforo')} aprob={o.get('mesa',{}).get('aprobada')} plan={o.get('plan')}" for o in ops)[:1500])
c = e.get("comite") or {}
print("::notice::COMITE " + json.dumps([(x["ticker"], x["aprobada"], x["favor"], x["contra"]) for x in c.get("acta") or []]))
por = defaultdict(lambda: [0, 0, []])
for s in e.get("senales") or []:
    if s.get("ticker") in acc and s.get("direccion"):
        p = por[s["ticker"]]
        p[0 if s["direccion"] > 0 else 1] += 1
        if s["direccion"] > 0:
            p[2].append(s["agente"])
top = sorted(por.items(), key=lambda kv: -(kv[1][0] - kv[1][1]))[:10]
print("::notice::SENALES " + " | ".join(f"{tk} {f}+/{c}- {pre.get(tk, {}).get('ultimo')} ({pre.get(tk, {}).get('variacion')}%) {','.join(ag[:4])}" for tk, (f, c, ag) in top))
mi = e.get("ministro") or {}
print("::notice::MINISTRO " + str(mi.get("titulo") or mi.get("lectura") or "")[:400] + " | " + json.dumps(mi.get("favorece") or mi.get("sesgo") or {}, ensure_ascii=False)[:300])
mu = e.get("mundo") or {}
print("::notice::MUNDO temas " + " | ".join(f"{t.get('tema')} {t.get('n')}" for t in (mu.get("temas") or [])[:6]))
eco = e.get("economista") or {}
print("::notice::ECONOMISTA " + json.dumps({k: eco.get(k) for k in ("titulo", "favorece", "evitar")}, ensure_ascii=False)[:500])
