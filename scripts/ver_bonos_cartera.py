import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
for c in a.get("usuario/cartera") or []:
    if str(c.get("ticker", "")).upper().startswith(("AO", "AN", "BAO")):
        print("::notice::" + json.dumps({k: c.get(k) for k in ("ticker", "cantidad", "precio", "fecha", "moneda", "nota")}, ensure_ascii=False))
pan = (a.get("ui/panel") or {}).get("titulos") or {}
print("::notice::precios: " + ", ".join(f"{t}={pan[t][0]}" for t in ("AO27", "AO27D", "AO27C", "AO29", "AO29D", "AO29C", "BAO27") if t in pan))
