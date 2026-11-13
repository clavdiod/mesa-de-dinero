import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
e = a.get("ui/estado") or {}
print(f"::notice::ronda {e.get('hora')} clima={e.get('clima')} protecciones={json.dumps(e.get('protecciones'), ensure_ascii=False)[:800]}")
c = e.get("comite") or {}
print("::notice::comite claves=" + ",".join(c.keys()) + " · " + json.dumps({k: (v if not isinstance(v, list) else v[:6]) for k, v in c.items() if k not in ("historia",)}, ensure_ascii=False)[:3500])
props = a.get("registro/propuestas") or []
cer = [p for p in props if (p.get("seguimiento") or {}).get("estado") in ("stop", "objetivo", "tiempo")]
print("::notice::cerradas últimos 15 días: " + " | ".join(f"{p['ticker']} {p['seguimiento'].get('fecha_cierre')} {p['seguimiento'].get('estado')} {p['seguimiento'].get('r_neto', p['seguimiento'].get('r'))}R" for p in cer if (p["seguimiento"].get("fecha_cierre") or "") >= "2026-10-29"))
