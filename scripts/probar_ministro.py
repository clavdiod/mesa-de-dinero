"""Prueba con la historia de las reglas del Ministro (BCRA desde 2022 + cierres guardados)."""
import json
from datetime import date

from mesa.agentes import ministro
from mesa.datos.cache import CacheHistorico
from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
series = ministro.bajar_series(date(2022, 1, 1), date.today())
print("::notice::series " + " ".join(f"{k}:{len(v)}({min(v) if v else '-'})" for k, v in series.items()))
cache = CacheHistorico(a)
tks = set(ministro.SOBERANOS + ministro.BANCOS + ministro.COBERTURA)
cierres = {}
for tk in tks:
    v = cache.velas(tk)
    if not v:
        cache.asegurar_mae(tk)
        v = cache.velas(tk)
    cierres[tk] = {x["fecha"]: x["cierre"] for x in v if x.get("cierre")}
print("::notice::cierres " + " ".join(f"{k}:{len(v)}" for k, v in cierres.items()))
r = ministro.entrenar(series, cierres)
print("::notice::PRUEBA " + json.dumps({k: {**v, "acierto": round(v["aciertos"] / v["casos"] * 100, 1), "prom": round(v["suma_ret"] / v["casos"], 2)} for k, v in r["stats"].items()}, ensure_ascii=False)[:3000] + " || activas " + json.dumps(r["activas"]))
f = ministro.foto(series, date.today().isoformat())
print("::notice::HOY " + json.dumps(ministro.lectura(f, r["activas"]), ensure_ascii=False)[:3000])
