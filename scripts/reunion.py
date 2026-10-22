"""Reunión de la mesa: revisión de lo que se miró en la última semana (solo imprime, no guarda)."""
import json
import os
from datetime import datetime, timedelta, timezone

from mesa.agentes import revision
from mesa.datos.cache import CacheHistorico
from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
hoy = (datetime.now(timezone.utc) - timedelta(hours=3)).date()
panel = (a.get("ui/panel") or {}).get("titulos") or {}
r = revision.reunir(a, CacheHistorico(a), panel, hoy, int(os.environ.get("DIAS", "7")))
print("::notice::AGENTES " + f"{r['senales']} señales || " + " | ".join(f"{x['nombre']}: {x['casos']} · {x['acierto_pct']}% · {x['promedio_pct']:+}% · fuertes {x['fuertes']} · {json.dumps(x['por_grupo'], ensure_ascii=False)}" for x in r["agentes"])[:3900])
print("::notice::PAPELES " + " | ".join(f"{p['ticker']}({p['grupo']}) desde {p['desde'][5:]} {p['ret']:+}% max {p['max']:+} min {p['min']:+} mesa {p['mesa']} {'OK' if p['acerto'] else 'X' if p['acerto'] is False else '-'} F:{','.join(p['favor'])[:60]} C:{','.join(p['contra'])[:60]}" for p in r["papeles"][:22])[:3900])
print("::notice::JEFE " + json.dumps(r["jefe"], ensure_ascii=False)[:1200] + " || SIM " + json.dumps(r["simulacion"], ensure_ascii=False)[:1200] + " || PRON " + json.dumps(r["pronosticos"], ensure_ascii=False)[:1000])
print("::notice::CIEGOS " + json.dumps(r["ciegos"], ensure_ascii=False)[:1500] + " || AJUSTES " + json.dumps(revision.ajustes(r), ensure_ascii=False)[:1200])
print("::notice::LECCIONES " + " || ".join(revision.lecciones(r))[:3900])
