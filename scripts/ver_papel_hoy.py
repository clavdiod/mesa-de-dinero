"""Todo lo que la mesa dijo hoy de un papel (TK en la variable de entorno o LRCX)."""
import json, os
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
tk = os.environ.get("TK", "LRCX")
est = a.get("ui/estado") or {}
props = [p for p in (a.get("registro/propuestas") or []) if p["ticker"] == tk]
print("::notice::PROPUESTAS " + json.dumps([{k: p.get(k) for k in ("fecha", "hora", "plan", "decision", "seguimiento", "cantidad_sugerida", "resumen_jefe")} for p in props[-3:]], ensure_ascii=False)[:1800])
ops = [o for l in (est.get("oportunidades") or {}).values() for o in l if o["ticker"] == tk]
print("::notice::OPS " + json.dumps(ops, ensure_ascii=False)[:1500])
print("::notice::PRON " + json.dumps([x for x in (a.get("pronosticos/libreta") or []) if x["ticker"] == tk][:5], ensure_ascii=False)[:1500])
deb = (a.get("ui/debates") or {}).get(tk) or {}
print("::notice::DEBATE " + json.dumps({k: deb.get(k) for k in ("fecha", "hora", "supervisor", "plan", "precio")}, ensure_ascii=False)[:1500])
print("::notice::OTROS ganadores=" + json.dumps([x for x in ((est.get("ganadores") or {}).get("lista") or []) if x["ticker"] == tk]) + " prof=" + json.dumps(((est.get("profesionales") or {}).get("lista") or {}).get(tk)) + " anticipo=" + json.dumps([x for x in (est.get("anticipos") or []) if x["ticker"] == tk]) + " lista=" + json.dumps([x for x in ((est.get("anticipo_lista") or {}).get("lista") or []) if x["ticker"] == tk]) + f" hora={est.get('hora')}")
