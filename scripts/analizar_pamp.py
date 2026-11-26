"""26/11: ¿mantener PAMP? Corre el análisis de los agentes (salida.analizar) con los datos reales. Solo lectura; solo PAMP."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos.cache import CacheHistorico
from mesa.agentes import salida
TK = "PAMP"
a = almacen_por_defecto()
est = a.get("ui/estado") or {}
seg = (est.get("seguimiento_cartera") or {}).get(TK) or {}
proy = (est.get("proyeccion_cartera") or {}).get(TK) or {}
print("::notice::seguimiento " + json.dumps({k: seg.get(k) for k in ("precio", "piso", "objetivo", "sugerida", "por_que", "estructura", "a_favor", "en_contra", "cambios")}, ensure_ascii=False, default=str)[:1500])
print("::notice::proyeccion " + json.dumps({k: proy.get(k) for k in ("precio", "resultado_pct", "max_desde_compra", "consejo", "motivo", "mesa", "rango_1m")}, ensure_ascii=False, default=str)[:1000])
panel = (a.get("ui/panel") or {}).get("titulos") or {}
t = panel.get(TK)
if isinstance(t, list):
    t = {"ultimo": t[0]}
t = t or {}
precio = float(t.get("ultimo") or proy.get("precio") or 0)
vel = [v for v in CacheHistorico(a).velas(TK) if v.get("fecha") != est.get("fecha")]
op = (est.get("opinion_cartera") or {}).get(TK) or {}
r = salida.analizar(TK, precio, 4290.0, precio, vel[-400:], t, "acciones", seg.get("a_favor") or op.get("a_favor"), seg.get("en_contra") or op.get("en_contra"), est.get("hora") or "13:00")
print("::notice::agentes " + json.dumps(r, ensure_ascii=False))
