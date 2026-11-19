"""19/11: ¿por qué la mesa no propuso VXX el 12-13/11 (a ~6.145)? Lo que quedó registrado de esos días."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
c = (a.get("ui/estado") or {}).get("comite") or {}
for d, xs in sorted((c.get("historial") or {}).items()):
    v = [x for x in xs if x.get("ticker") == "VXX"]
    print(f"::notice::COMITE {d}: {len(xs)} votados · VXX: {json.dumps(v, ensure_ascii=False)[:600] if v else 'no llegó al Comité'}")
for d in ("2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13", "2026-11-16", "2026-11-17", "2026-11-18"):
    ds = a.get(f"jefe/descartes/{d}") or {}
    print(f"::notice::DESCARTES {d}: VXX={ds.get('VXX')} ({len(ds)} descartados)")
for p in a.get("pronosticos/libreta") or []:
    if str(p.get("ticker")) in ("VXX", "VXXD") and str(p.get("fecha") or "") >= "2026-11-05":
        print("::notice::PRONOSTICO " + json.dumps(p, ensure_ascii=False)[:400])
sim = a.get("sim/posiciones") or []
for s in (sim if isinstance(sim, list) else sim.values() if isinstance(sim, dict) else []):
    if isinstance(s, dict) and s.get("ticker") == "VXX":
        print("::notice::SIM " + json.dumps(s, ensure_ascii=False)[:300])
v = []
try:
    from mesa.datos.cache import CacheHistorico
    v = CacheHistorico(a).velas("VXX")[-12:]
except Exception as ex:
    print(f"::notice::velas err {ex}")
print("::notice::VELAS " + " | ".join(f"{x['fecha']} {x['cierre']} vol {x.get('volumen')}" for x in v))
