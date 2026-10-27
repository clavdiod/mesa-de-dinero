"""Aplica el examen 'tiene que mejorar al común' al Anticipador Mundo ya guardado."""
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
for k in ("anticipo_mundo/modelo", "anticipo_mundo/lista"):
    m = a.get(k) or {}
    if m:
        m["activo"] = False
        a.put(k, m)
print("::notice::Anticipador Mundo en observación (no mejora al común)")
