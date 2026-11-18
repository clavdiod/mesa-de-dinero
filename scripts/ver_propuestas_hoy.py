"""Qué propuso hoy la mesa: acta del Comité (aprobó / revisión en frío) y propuestas registradas del día."""
import json
from datetime import date
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto(); h = date.today().isoformat()
e = a.get("ui/estado") or {}
c = e.get("comite") or {}
print(f"::notice::ronda {e.get('hora')} clima={e.get('clima')} comite fecha={c.get('fecha')} hora={c.get('hora')} prot={json.dumps(e.get('protecciones'), ensure_ascii=False)[:300]}")
for x in c.get("acta") or []:
    print(f"::notice::ACTA {x.get('ticker')} aprobada={x.get('aprobada')} favor={x.get('favor')} contra={x.get('contra')} frio={x.get('frio')} propuesta={x.get('propuesta')} · {str(x.get('motivo'))[:150]} · FRIO: {x.get('frio_motivo')}")
for p in a.get("registro/propuestas") or []:
    if p.get("fecha") == h:
        pl = p.get("plan") or {}
        print(f"::notice::PROP {p.get('ticker')} {p.get('hora')} entrada {pl.get('entrada')} stop {pl.get('stop')} obj {pl.get('objetivo')} cant {p.get('cantidad_sugerida')} mitad {p.get('tamano_mitad')} decision {p.get('decision')} seg {json.dumps(p.get('seguimiento'), ensure_ascii=False)[:200]} · {str(p.get('ficha_txt'))[:400]}")
