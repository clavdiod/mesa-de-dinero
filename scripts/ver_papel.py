"""Todo lo que la mesa tiene de un papel: debate, pronósticos, panel, noticias y precio en EE.UU."""
import json
import os

from mesa.agentes import mundo
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto

tk = os.environ.get("TICKER", "IREN")
a = almacen_por_defecto()
deb = (a.get("ui/debates") or {}).get(tk) or {}
print("::notice::DEBATE " + json.dumps({k: deb.get(k) for k in ("fecha", "hora", "precio", "puntaje", "supervisor", "jefe", "plan", "riesgo")}, ensure_ascii=False)[:3800])
print("::notice::FAVOR " + " | ".join(f"{x['agente']} {x['fuerza']}: {x['texto'][:220]}" for x in deb.get("favor", []))[:3800])
print("::notice::CONTRA " + " | ".join(f"{x['agente']} {x['fuerza']}: {x['texto'][:220]}" for x in deb.get("contra", []))[:3800]
      + " || NEUTRAL " + " | ".join(f"{x['agente']}: {x['texto'][:200]}" for x in deb.get("neutral", []))[:1500])
lib = [x for x in (a.get("pronosticos/libreta") or []) if x["ticker"] == tk]
print("::notice::PRON " + json.dumps(lib[:5], ensure_ascii=False)[:2000])
v = gratis.yahoo_vivo(tk, prepost=True) if hasattr(gratis, "yahoo_vivo") else None
h = gratis.yahoo(tk, "1y")
cierres = [c for _, c in h]
if cierres:
    mx, mn = max(cierres), min(cierres)
    print("::notice::EEUU vivo " + json.dumps(v)[:400] + f" || 1 año: min {mn} max {mx} ult {cierres[-1]} || ult 30: " + " ".join(f"{f[5:]}:{c}" for f, c in h[-30:]))
cache = (a.get("mundo/papeles") or {}).get("papeles", {}).get(tk) or mundo.noticias_papel(tk, "IREN Limited", False)
print("::notice::NOTICIAS " + " | ".join(f"[{t['dir']:+d}] {t['titulo'][:150]} ({(t.get('fecha') or '')[:10]})" for t in cache.get("titulares", []))[:3800])
ev = [e for e in ((a.get("eventos/eeuu") or {}).get("eventos") or []) if e.get("ticker") == tk]
print("::notice::EVENTOS " + json.dumps(ev, ensure_ascii=False)[:800])
