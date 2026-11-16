from datetime import date
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.agentes import revision_diaria as rd
a = almacen_por_defecto()
pts = rd.armar(a, date(2026, 11, 16), (a.get("ui/panel") or {}).get("titulos") or {})
print("RD| " + (" || ".join(pts) if pts else "sin novedades: no se avisaría"))
