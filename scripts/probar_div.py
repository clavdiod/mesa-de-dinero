from datetime import date
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.agentes import informe_semanal as inf
a = almacen_por_defecto()
panel = (a.get("ui/panel") or {}).get("titulos") or {}
r = inf.armar(a, date(2026, 11, 13), panel, lambda tk: [], lambda tk: "x", {}, {}, [])
for s in r["secciones"]:
    if "Dividendos" in s["titulo"]:
        for l in s["lineas"]: print("DV| " + l)
