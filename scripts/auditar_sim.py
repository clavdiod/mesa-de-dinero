"""20/11: la simulación en papel da 12% ganadoras: demasiado bajo. ¿Los stops son reales?"""
from collections import Counter
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos.cache import CacheHistorico
a = almacen_por_defecto(); c = CacheHistorico(a)
pos = a.get("sim/posiciones") or []
st = [p for p in pos if p.get("estado") == "stop"]
print(f"::notice::posiciones {len(pos)} · estados {Counter(p.get('estado') for p in pos).most_common()}")
raros, ok, sin = [], 0, 0
for p in st:
    v = {x["fecha"]: x for x in c.velas(p["ticker"])}
    vel = v.get(p.get("fecha_cierre"))
    if not vel:
        sin += 1; continue
    if vel["minimo"] > p["stop"] * 1.005 and vel["cierre"] > p["stop"]:
        raros.append(f"{p['ticker']} {p.get('fecha_cierre')} stop {p['stop']:.0f} · vela mín {vel['minimo']:.0f} cierre {vel['cierre']:.0f} · último sim {p.get('ultimo')}")
    else:
        ok += 1
print(f"::notice::stops {len(st)}: confirmados por la vela del día {ok} · NO confirmados (la vela nunca tocó el stop) {len(raros)} · sin vela {sin}")
print("::notice::EJEMPLOS " + " | ".join(raros[:15]))
g = Counter(p.get("grupo") for p in st); print(f"::notice::stops por grupo {g.most_common()}")
