"""12/11: refresca las licitaciones y muestra si las de provincia ya traen detalle y documentos."""
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.reloj import ahora
from mesa.datos.eventos import actualizar_licitaciones
a = almacen_por_defecto()
r = actualizar_licitaciones(a, ahora().date(), ahora().strftime("%H:%M"), forzar=True)
evs = r.get("eventos") or []
print(f"::notice::{len(evs)} licitaciones; por clase: " + ", ".join(f"{c}: {sum(1 for e in evs if e.get('clase') == c)}" for c in sorted({e.get('clase') for e in evs})))
for e in [e for e in evs if e.get("clase") in ("Provincia", "Tesoro")][:6]:
    print(f"::notice::{e['fecha']} {e['titulo'][:70]} · emisor={e.get('emisor')} moneda={e.get('moneda')} monto={e.get('monto')} liq={e.get('liquidacion')} docs={len(e.get('documentos') or [])} resumen={str(e.get('resumen'))[:150]}")
