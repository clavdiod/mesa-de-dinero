"""Borra los avisos de venta de las 10:30 del 03/11 (precios de antes de la apertura) y resetea 'avisados'."""
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
al = a.get("ui/alertas") or []
n = [x for x in al if not (x.get("fecha") == "2026-11-03" and "VEND" in str(x.get("texto", "")).upper())]
a.put("ui/alertas", n); a.put("cartera/avisados", {})
print(f"::notice::borrados {len(al) - len(n)}")
