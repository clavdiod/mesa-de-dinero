"""Arma la memoria por papel y muestra cómo están las protecciones hoy (sin esperar al cierre)."""
import json

from mesa.nucleo import protecciones as pr
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.registro import Registro
from mesa.nucleo.reloj import ahora

a = almacen_por_defecto()
reg = Registro(a)
mem = pr.memoria(reg.propuestas, a.get("pronosticos/libreta") or [])
a.put("memoria/papeles", mem)
ev = pr.evaluar(reg.propuestas, ahora().date())
cer = pr._cerradas(reg.propuestas)
print("::notice::PROTECCIONES " + json.dumps(ev, ensure_ascii=False)[:1500])
print(f"::notice::MEMORIA {len(mem)} papeles; propuestas cerradas {len(cer)}: " + " | ".join(
    f"{p['ticker']} {p['seguimiento']['estado']} {p['seguimiento'].get('r_neto')} {p['seguimiento']['fecha_cierre']}" for p in cer[-25:]))
for tk, xs in list(mem.items())[:6]:
    print(f"::notice::{tk}: " + " // ".join(x["texto"] for x in xs)[:900])
