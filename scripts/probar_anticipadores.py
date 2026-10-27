"""Entrena y examina el Anticipador ARG y el Anticipador Mundo; guarda modelo y lista de hoy."""
import json
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipadores as A, anticipo
from mesa.cierre import _universo_cedears
from mesa.datos import gratis
from mesa.datos.cache import CacheHistorico
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.reloj import ahora
a = almacen_por_defecto()
hoy = ahora().date().isoformat()
# --- Argentina ---
cache = CacheHistorico(a)
panel = (a.get("ui/panel") or {}).get("titulos") or {}
acc = {}
for tk in cache.indice:
    if (panel.get(tk) or [None] * 5)[4] == "acciones":
        vs = cache.velas(tk)
        if len(vs) > 120:
            acc[tk] = [{"fecha": v["fecha"], "c": v["cierre"], "h": v.get("maximo") or v["cierre"], "l": v.get("minimo") or v["cierre"],
                        "v": v.get("volumen") or 0, "o": v.get("apertura")} for v in vs if v.get("cierre")]
merval = {f: c for f, c in gratis.yahoo("^MERV", "5y")}
macro = gratis.series_macro()
rp, ccl = macro.get("riesgo_pais") or {}, macro.get("ccl") or {}
print(f"::notice::ARG datos: {len(acc)} acciones, {sum(len(v) for v in acc.values())} velas, merval {len(merval)}, riesgo país {len(rp)}, ccl {len(ccl)}")
m_arg = A.entrenar_arg(acc, merval, rp, ccl)
print("::notice::ARG " + json.dumps(A.resumen_prueba(m_arg), ensure_ascii=False)[:1500])
if m_arg.get("w"):
    a.put("anticipo_arg/modelo", m_arg)
    lst = A.lista_arg(m_arg, acc, merval, rp, ccl, max(merval) if merval else hoy)
    li = [x for x in lst if x["prob"] >= (m_arg.get("umbral") or 1)][:10]
    a.put("anticipo_arg/lista", {"fecha": max(v[-1]["fecha"] for v in acc.values()), "activo": m_arg.get("activo"), "umbral": m_arg.get("umbral"),
                                 "prueba": m_arg.get("prueba"), "lista": li})
    print("::notice::ARG HOY " + " | ".join(f"{x['ticker']} {x['prob']:.2f} {', '.join(x['razones'])}" for x in li))
# --- Mundo ---
uni = _universo_cedears(a)
with ThreadPoolExecutor(8) as ex:
    s5 = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "5y"), uni)) if len(f) > 300}
spy = {f: c for f, c in gratis.yahoo("SPY", "5y")}
vix = {f: c for f, c in gratis.yahoo("^VIX", "5y")}
btc = {f: c for f, c in gratis.yahoo("BTC-USD", "5y")}
glob = {k: {f: c for f, c in gratis.yahoo(sym, "5y")} for k, sym in A.GLOBALES.items()}
from mesa.agentes import profesionales as pro
etfs = {e: {f: c for f, c in gratis.yahoo(e, "5y")} for e in pro.NOMBRE_SECTOR}
sect = {k: v for k, v in (a.get("profesionales/sectores") or {}).items() if v}
print("::notice::MUNDO datos: " + json.dumps({k: len(v) for k, v in glob.items()}) + f" cedears {len(s5)} sectores {len(sect)}")
base = anticipo.entrenar(s5, spy, vix, btc)
m_mun = A.entrenar_mundo(s5, spy, vix, btc, glob, sect, etfs)
print("::notice::BASE (solo CEDEARs, mismo examen) " + json.dumps(base.get("prueba")))
print("::notice::MUNDO " + json.dumps(A.resumen_prueba(m_mun), ensure_ascii=False)[:1500])
if m_mun.get("w"):
    a.put("anticipo_mundo/modelo", m_mun)
    lst = A.lista_mundo(m_mun, s5, spy, vix, btc, glob, sect, etfs, max(spy))
    li = [x for x in lst if x["prob"] >= (m_mun.get("umbral") or 1)][:10]
    a.put("anticipo_mundo/lista", {"fecha": max(spy), "activo": m_mun.get("activo"), "umbral": m_mun.get("umbral"), "prueba": m_mun.get("prueba"),
                                   "base": base.get("prueba"), "lista": li})
    print("::notice::MUNDO HOY " + " | ".join(f"{x['ticker']} {x['prob']:.2f} {', '.join(x['razones'])}" for x in li))
