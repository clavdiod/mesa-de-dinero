"""27/11: estado de los avisos al celular (solo fechas y cantidades, sin direcciones)."""
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
subs = a.get("push/suscripciones") or []
venc = a.get("push/vencidas") or []
print(f"::notice::suscripciones vivas: {len(subs)} altas={[s.get('alta') for s in subs]}")
print(f"::notice::vencidas: {[(v.get('fecha'), v.get('hora')) for v in venc]}")
print(f"::notice::corte: {a.get('push/corte')}")
