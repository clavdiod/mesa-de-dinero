"""19/11: ¿con qué precios se armó la propuesta de VXX?"""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
for p in a.get("registro/propuestas") or []:
    if p.get("ticker") == "VXX" and p.get("fecha") == "2026-11-19":
        print("::notice::PROP " + json.dumps({k: p.get(k) for k in ("hora", "plan", "precio", "ficha_frio", "seguimiento")}, ensure_ascii=False, default=str)[:3000])
pan = (a.get("ui/panel") or {})
print("::notice::PANEL " + json.dumps({"fecha": pan.get("fecha"), "hora": pan.get("hora"), "VXX": (pan.get("titulos") or {}).get("VXX"), "cols": pan.get("columnas")}, ensure_ascii=False)[:800])
