"""Anticipador ARG con 5 años de historia (Yahoo .BA, gratis) en vez de los ~270 días guardados."""
import json
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipadores as A
from mesa.datos import gratis
from mesa.datos.cache import CacheHistorico
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
panel = (a.get("ui/panel") or {}).get("titulos") or {}
tks = sorted(tk for tk, x in panel.items() if x and x[4] == "acciones")
with ThreadPoolExecutor(8) as ex:
    ser = {tk: f for tk, f in zip(tks, ex.map(lambda t: gratis.yahoo_ohlcv(t + ".BA", "5y"), tks)) if len(f) > 500}
merval = {f: c for f, c in gratis.yahoo("^MERV", "5y")}
macro = gratis.series_macro(5)
rp, ccl = macro.get("riesgo_pais") or {}, macro.get("ccl") or {}
print(f"::notice::{len(ser)} de {len(tks)} acciones con 5 años; {sum(len(v) for v in ser.values())} velas; riesgo país {len(rp)}, ccl {len(ccl)}, merval {len(merval)}")
import traceback
try:
    m = A.entrenar_arg(ser, merval, rp, ccl)
except Exception:
    print("::notice::ERROR " + traceback.format_exc().replace("\n", " | ")[-1500:])
    raise
print("::notice::ARG5 " + json.dumps(A.resumen_prueba(m), ensure_ascii=False)[:1500])
if m.get("w"):
    a.put("anticipo_arg/modelo", m)
    # lista de hoy con las velas guardadas (las del día, en pesos)
    cache = CacheHistorico(a)
    acc = {}
    for tk in tks:
        vs = cache.velas(tk)
        if len(vs) > 60:
            acc[tk] = [{"fecha": v["fecha"], "c": v["cierre"], "h": v.get("maximo") or v["cierre"], "l": v.get("minimo") or v["cierre"],
                        "v": v.get("volumen") or 0} for v in vs[-200:] if v.get("cierre")]
    fuente = acc if len(acc) >= 20 else ser
    fecha = max(v[-1]["fecha"] for v in fuente.values())
    la = A.lista_arg(m, fuente, merval, rp, ccl, fecha)
    li = [x for x in la if x["prob"] >= (m.get("umbral") or 1)][:10]
    a.put("anticipo_arg/lista", {"fecha": fecha, "activo": m.get("activo"), "umbral": m.get("umbral"), "prueba": m.get("prueba"), "lista": li})
    print("::notice::ARG5 HOY " + " | ".join(f"{x['ticker']} {x['prob']:.2f} {', '.join(x['razones'])}" for x in li))
