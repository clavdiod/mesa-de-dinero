"""06/11: el viernes 6 SÍ hubo mercado (se había cargado como día sin mercado). Lunes 9 feriado nacional; martes 10 feriado en CABA."""
from datetime import date
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.reloj import es_dia_habil
a = almacen_por_defecto()
f = set(a.get("ref/feriados_2026") or []) - {"2026-11-06"}
a.put("ref/feriados_2026", sorted(f))
print("::notice::" + " · ".join(f"{d.strftime('%a %d')}: {'hay mercado' if es_dia_habil(d, a) else 'sin mercado'}" for d in [date(2026, 11, x) for x in (6, 9, 10, 11, 20, 23)]))
