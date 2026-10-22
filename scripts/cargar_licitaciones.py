"""Carga ya las licitaciones del MAE con sus fichas (resumen del aviso de suscripción) y las pone en la app."""
from mesa.datos.eventos import actualizar_licitaciones
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.reloj import ahora

a = almacen_por_defecto()
hoy = ahora().date()
r = actualizar_licitaciones(a, hoy, ahora().strftime("%H:%M"), forzar=True)
est = a.get("ui/estado") or {}
if est:
    hasta = (hoy.toordinal() + 45)
    nuevas = [{**e, "mio": True} for e in r.get("eventos") or [] if hoy.isoformat() <= e["fecha"]]
    est["eventos"] = sorted([e for e in est.get("eventos") or [] if e.get("tipo") != "licitacion"] + nuevas, key=lambda e: (e["fecha"], e.get("tipo", "")))
    est["licitaciones_avisos"] = r.get("avisos")
    est["licitaciones_noticias"] = r.get("noticias")
    a.put("ui/estado", est)
for e in r.get("eventos") or []:
    if e.get("resumen"):
        print(f"::notice::{e['fecha']} {e['titulo'][:50]} || {e['resumen']} || campos: {list((e.get('ficha') or {}).get('campos', {}))} || docs: {len(e.get('documentos') or [])}")
for t in ("anuncios", "resultados"):
    for x in (r.get("avisos") or {}).get(t) or []:
        print(f"::notice::{t} {x['titulo'][:50]} || {x.get('resumen') or '(sin resumen)'} || {list((x.get('campos') or {}).keys())}")
