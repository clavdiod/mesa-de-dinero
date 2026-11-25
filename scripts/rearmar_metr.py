"""25/11: la alarma de METR (1.737,5, subida hoy) sonó por error con el mínimo de antes de crearla. La vuelve a armar. Solo METR."""
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
d = a.get("alertas/disparadas") or {}
print(f"::notice::antes: {d.get('stop-mwwefq03')}")
if d.pop("stop-mwwefq03", None):
    a.put("alertas/disparadas", d)
    print("::notice::alarma de METR 1.737,5 armada de nuevo")
