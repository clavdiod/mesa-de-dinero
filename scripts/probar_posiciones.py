"""20/11: prueba en seco de la línea de posiciones con el panel guardado (no registra nada)."""
import json
from datetime import date
from types import SimpleNamespace
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos.cache import CacheHistorico
from mesa.agentes import posiciones as P

class Mem:
    def __init__(self, a): self.a, self.d = a, {}
    def get(self, k): return self.d.get(k, self.a.get(k))
    def put(self, k, v): self.d[k] = v
a = almacen_por_defecto(); m = Mem(a)
pan = (a.get("ui/panel") or {}).get("titulos") or {}
tit = {tk: {"ultimo": x[0], "variacion": x[1], "compra": x[2], "venta": x[3], "grupo": x[4], "monto": 1e9} for tk, x in pan.items() if x and x[0]}
ctx = SimpleNamespace(fecha=date.today(), por_simbolo=tit, titulo=lambda tk: tit.get(tk), cache=CacheHistorico(a))
props = P.proponer(ctx, m, date.today(), a.get("usuario/cartera") or [], [], 100000.0, "12:00")
c = m.d.get(P.CLAVE_CAND) or {}
print("::notice::CANDIDATAS " + json.dumps(c.get("lista"), ensure_ascii=False)[:1500])
for p in props:
    print("::notice::PROPUESTA " + json.dumps({k: p[k] for k in ("ticker", "tipo_posicion", "plan", "cantidad_sugerida", "monto_sugerido", "resumen_jefe")}, ensure_ascii=False)[:1200])
