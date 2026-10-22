"""Corre la reunión de la mesa ahora, la guarda y la pone en la app (sin esperar al cierre de mañana)."""
from datetime import datetime, timedelta, timezone

from mesa.agentes import revision
from mesa.datos.cache import CacheHistorico
from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
hoy = (datetime.now(timezone.utc) - timedelta(hours=3)).date()
panel = (a.get("ui/panel") or {}).get("titulos") or {}
r = revision.reunir(a, CacheHistorico(a), panel, hoy, 7)
aj = revision.ajustes(r)
r["lecciones"], r["ajustes"] = revision.lecciones(r), aj
a.put("revision/ultima", r)
a.put("revision/ajustes", aj)
est = a.get("ui/estado") or {}
est["reunion"] = r
a.put("ui/estado", est)
print("::notice::" + f"{r['senales']} señales · ajustes {aj} || " + " || ".join(r["lecciones"])[:3500])
