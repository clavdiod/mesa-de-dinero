"""YPFD a un mes, en frío: rango normal, historia de casos parecidos, anticipador, analistas del ADR, balance."""
import json, traceback, math, statistics as st
import numpy as np
from mesa.agentes import anticipadores as A
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
try:
    e = a.get("ui/estado") or {}
    p = (e.get("proyeccion_cartera") or {}).get("YPFD") or {}
    print("::notice::proyección " + json.dumps({k: p.get(k) for k in ("precio", "rango_1m", "objetivo", "piso", "mesa", "favor", "contra", "estructura")}, ensure_ascii=False)[:900])
    la = (e.get("anticipo_listas") or {}).get("anticipador_arg") or (a.get("anticipo_arg/lista") or {})
    print("::notice::anticipador ARG lista " + str(la.get("fecha")) + ": " + ", ".join(f"{x['ticker']} {x['prob']}" for x in (la.get("lista") or [])))
    print("::notice::consenso YPF " + json.dumps((a.get("profesionales/consensos") or {}).get("YPF") or (a.get("profesionales/consensos") or {}).get("YPFD")))
    print("::notice::eventos " + json.dumps([x for x in (e.get("eventos") or []) if "YPF" in str(x.get("ticker")) or "YPF" in str(x.get("nombre"))], ensure_ascii=False)[:500])
    # historia: YPFD en USD 10 años, días con caída de 8%+ en 4 ruedas y mínimo de 60 ruedas -> qué pasó a 20 ruedas
    acc, mer, rp, ccl = A.datos_arg(["YPFD"], 10)
    f = acc["YPFD"]; c = np.array([x["c"] for x in f])
    res = []
    for i in range(70, len(c) - 21):
        if c[i] / c[i - 4] - 1 <= -0.08 and c[i] <= c[i - 60:i].min():
            res.append(c[i + 20] / c[i] - 1)
    v = np.array(res) * 100
    print(f"::notice::YPFD 10 años, casos parecidos (cae 8%+ en 4 ruedas a mínimo de 3 meses): {len(v)} | a 20 ruedas promedio {v.mean():+.1f}%, mediana {np.median(v):+.1f}%, suben 10%+ {np.mean(v >= 10)*100:.0f}%, caen 10%+ {np.mean(v <= -10)*100:.0f}%, terminan arriba {np.mean(v > 0)*100:.0f}%")
    r = [math.log(c[k] / c[k - 1]) for k in range(len(c) - 63, len(c))]
    s = st.pstdev(r) * math.sqrt(20)
    print(f"::notice::volatilidad 1 mes: ±{s*100:.1f}% → rango 2 de cada 3 veces {7430*math.exp(-s):.0f} a {7430*math.exp(s):.0f}")
except Exception:
    print("::notice::ERR " + traceback.format_exc().replace(chr(10), " | ")[-600:])
