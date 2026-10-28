"""Lista de hoy del Anticipador ARG (modelo en dólares CCL), con las velas guardadas convertidas a dólares."""
from mesa.agentes import anticipadores as A
from mesa.datos import gratis
from mesa.datos.cache import CacheHistorico
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
ma = a.get("anticipo_arg/modelo") or {}
panel = (a.get("ui/panel") or {}).get("titulos") or {}
cache = CacheHistorico(a)
acc = {}
for tk, x in panel.items():
    if x and x[4] == "acciones":
        vs = cache.velas(tk)
        if len(vs) > 60:
            acc[tk] = [{"fecha": v["fecha"], "c": v["cierre"], "h": v.get("maximo") or v["cierre"], "l": v.get("minimo") or v["cierre"],
                        "v": v.get("volumen") or 0} for v in vs[-200:] if v.get("cierre")]
macro = gratis.series_macro(1)
ccl, rp = macro.get("ccl") or {}, macro.get("riesgo_pais") or {}
mv = {f: c for f, c in gratis.yahoo("^MERV", "6mo")}
acc_u, mv_u = A.a_dolares(acc, ccl), A.merval_dolares(mv, ccl)
fecha = max(v[-1]["fecha"] for v in acc.values())
la = A.lista_arg(ma, acc_u, mv_u, rp, ccl, fecha)
li = [x for x in la if x["prob"] >= (ma.get("umbral") or 1)][:10]
a.put("anticipo_arg/lista", {"fecha": fecha, "activo": ma.get("activo"), "umbral": ma.get("umbral"), "prueba": ma.get("prueba"),
                             "version": ma.get("version"), "lista": li})
print(f"::notice::modelo {ma.get('version')} activo {ma.get('activo')} umbral {ma.get('umbral')} | lista del {fecha}: " +
      " | ".join(f"{x['ticker']} {x['prob']:.2f} {', '.join(x['razones'])}" for x in li))
