import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto(); h = "2026-11-20"
for x in (a.get("ui/alertas") or [])[:15]:
    if x.get("fecha") == h and x.get("tipo") in ("cartera_hoy", "buen_dia"):
        print(f"::notice::{x.get('hora')} {x.get('ticker')}: {str(x.get('texto'))[:1500]}")
for p in a.get("registro/propuestas") or []:
    if p.get("fecha") == h:
        print("::notice::PROP " + json.dumps({k: p.get(k) for k in ("hora", "ticker", "linea", "tipo_posicion", "plan", "cantidad_sugerida", "monto_sugerido", "ranking", "noticias")}, ensure_ascii=False, default=str)[:700])
print("::notice::CAND " + json.dumps(((a.get("posiciones/candidatas") or {}).get("lista") or [])[:20], ensure_ascii=False)[:1200])
print("::notice::avisos " + str({k: a.get(k) for k in ("avisos/buen_dia", "avisos/cartera_hoy")}))
