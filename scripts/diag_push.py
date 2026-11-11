"""11/11: Clau no recibió avisos hoy. Suscripciones guardadas y prueba de envío."""
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo import push
from mesa.nucleo.config import env
a = almacen_por_defecto()
subs = a.get("push/suscripciones") or []
print(f"::notice::{len(subs)} suscripciones: " + " | ".join(f"{s.get('endpoint','')[:45]}… alta {s.get('alta')}" for s in subs) + f" · claves {'OK' if env('VAPID_PRIVADA') and env('VAPID_PUBLICA') else 'FALTAN'}")
al = a.get("ui/alertas") or []
print("::notice::últimas alertas: " + " | ".join(f"{x.get('fecha')} {x.get('hora')} {x.get('ticker')}" for x in al[:8]))
r = push.enviar(subs)
print(f"::notice::prueba de envío: {r}")
