"""Reunión de toda la mesa sobre todos estos días (desde el 19/10): guarda, pone en la app e imprime el detalle."""
import json
import os
from datetime import datetime, timedelta, timezone

from mesa.agentes import revision
from mesa.datos.cache import CacheHistorico
from mesa.nucleo import pronosticos as pr
from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
hoy = (datetime.now(timezone.utc) - timedelta(hours=3)).date()
dias = int(os.environ.get("DIAS", "10"))
panel = (a.get("ui/panel") or {}).get("titulos") or {}
r = revision.reunir(a, CacheHistorico(a), panel, hoy, dias)
aj = revision.ajustes(r)
r["lecciones"], r["ajustes"] = revision.lecciones(r), aj
a.put("revision/ultima", r)
a.put("revision/ajustes", aj)
est = a.get("ui/estado") or {}
est["reunion"] = r
a.put("ui/estado", est)
print("::notice::AGENTES " + f"{r['senales']} señales desde {r['desde']} || " + " | ".join(f"{x['nombre']}: {x['casos']} · {x['acierto_pct']}% · {x['promedio_pct']:+}%" for x in r["agentes"])[:3800])
print("::notice::PAPELES " + " | ".join(f"{p['ticker']} {p['ret']:+}% desde {p['desde'][5:]} mesa {p['mesa']} {'OK' if p['acerto'] else 'X' if p['acerto'] is False else '-'}" for p in r["papeles"][:25])[:3800])
lib = a.get("pronosticos/libreta") or []
print("::notice::PRONOSTICOS " + json.dumps(pr.resumen(lib), ensure_ascii=False)[:1500] + " || JEFE " + json.dumps(r["jefe"], ensure_ascii=False)[:800] + " || SIM " + json.dumps(r["simulacion"], ensure_ascii=False)[:600])
ms = a.get("mundo/stats") or {}
mn = (est.get("ministro") or {}).get("reglas")
print("::notice::CORRESPONSAL " + json.dumps(ms, ensure_ascii=False)[:800] + " || MINISTRO " + json.dumps(mn, ensure_ascii=False)[:600] + " || CIEGOS " + json.dumps(r["ciegos"], ensure_ascii=False)[:600] + " || AJUSTES " + json.dumps(aj, ensure_ascii=False)[:800])
anti = a.get("anticipo/estadistica") or {}
adr = a.get("adr/estadistica") or {}
mae = a.get("mae/comparacion") or {}
print("::notice::ANTICIPOS " + json.dumps(anti, ensure_ascii=False)[:700] + " || ADR " + json.dumps(adr, ensure_ascii=False)[:700] + " || MAE " + json.dumps([d["resumen"] for d in mae.get("dias", [])][-3:], ensure_ascii=False)[:700])
print("::notice::LECCIONES " + " || ".join(r["lecciones"])[:3000])
