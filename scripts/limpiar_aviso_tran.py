"""Borra el aviso equivocado de TRAN del 28/10 (VENDÉ TODO por el máximo de antes de comprar) y lo saca de 'avisados'."""
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
al = a.get("ui/alertas") or []
nuevo = [x for x in al if not (str(x.get("ticker", "")).startswith("TRAN") and x.get("fecha") == "2026-10-28" and "VEND" in str(x.get("texto", "")).upper())]
a.put("ui/alertas", nuevo)
av = a.get("cartera/avisados") or {}
av.pop("TRAN", None)
a.put("cartera/avisados", av)
print(f"::notice::borrados {len(al) - len(nuevo)} avisos de TRAN")
