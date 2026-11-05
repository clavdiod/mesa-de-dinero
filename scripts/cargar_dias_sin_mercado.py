"""05/11: Clau avisa que no hay operaciones el viernes 6, lunes 9 y martes 10 de noviembre."""
from datetime import date
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.reloj import feriados, es_dia_habil
a = almacen_por_defecto()
f = feriados(2026, a) | {"2026-11-06", "2026-11-09", "2026-11-10"}
a.put("ref/feriados_2026", sorted(f))
dias = [date(2026, 11, d) for d in range(5, 12)]
print("::notice::" + " · ".join(f"{d.strftime('%a %d')}: {'hay mercado' if es_dia_habil(d, a) else 'sin mercado'}" for d in dias) + f" · {len(f)} feriados en 2026")
