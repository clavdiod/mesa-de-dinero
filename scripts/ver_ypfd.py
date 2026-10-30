import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
e = a.get("ui/estado") or {}
g = (e.get("seguimiento_cartera") or {}).get("YPFD") or {}
print("::notice::plazo " + json.dumps({k: g.get(k) for k in ("vence", "vence_base", "plazo_motivo", "cambios_plazo", "dias", "total")}, ensure_ascii=False))
d = (a.get("ui/debates") or {}).get("YPFD") or {}
print("::notice::contra " + " || ".join(f"{s.get('agente')} ({s.get('fuerza')}): {s.get('texto')}" for s in (d.get("contra") or []))[:1200])
print("::notice::eventos " + json.dumps([x for x in (e.get("eventos") or []) if "YPF" in str(x.get("ticker"))], ensure_ascii=False)[:600])
