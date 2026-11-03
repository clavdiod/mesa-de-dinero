import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
o = a.get("opciones/estado") or {}
print(f"::notice::{o.get('fecha')} {o.get('hora')} papeles {len(o.get('papeles') or [])} papel {len(o.get('papel') or [])} res {o.get('resultado_papel')}")
for p in (o.get("papeles") or [])[:9]:
    v = p["volatilidad"]
    print(f"::notice::{p['ticker']} spot {p['spot']} liq {p['liquidas']}/{p['opciones']} mesa {p['mesa']} IV {v.get('iv_atm')} HV20 {v.get('hv20')} HV60 {v.get('hv60')} ratio {v.get('ratio')} | " +
          " || ".join(f"{i['estrategia']} {'OK' if i['aprobada'] else 'no'}: {i['texto'][:200]} {i['motivo']}" for i in p["ideas"]))
