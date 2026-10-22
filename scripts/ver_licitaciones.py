"""Diagnóstico de licitaciones: KV y lo que recibe la app."""
from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
lic = a.get("eventos/licitaciones") or {}
print("::notice::KV " + (f"fecha {lic.get('fecha')} hora {lic.get('hora')} eventos {len(lic.get('eventos') or [])} avisos {[(k, len(v)) for k, v in (lic.get('avisos') or {}).items()]} noticias {len(lic.get('noticias') or [])} pagos {len(lic.get('pagos') or [])}" if isinstance(lic, dict) else str(type(lic))))
est = a.get("ui/estado") or {}
ev = est.get("eventos") or []
print("::notice::ESTADO hora " + str(est.get("hora")) + f" eventos {len(ev)} licitacion {[e['fecha'] + ' ' + e['nombre'][:40] for e in ev if e.get('tipo') == 'licitacion']} "
      + f"avisos {bool(est.get('licitaciones_avisos'))} noticias {len(est.get('licitaciones_noticias') or [])} tipos {sorted({e.get('tipo') for e in ev})}")
