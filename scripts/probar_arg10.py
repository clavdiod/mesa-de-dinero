"""Anticipador ARG: 10 años en pesos y 5/10 años en dólares CCL (sin el efecto inflación). Guarda solo si alguno aprueba."""
import json, traceback
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipadores as A
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
panel = (a.get("ui/panel") or {}).get("titulos") or {}
tks = sorted(tk for tk, x in panel.items() if x and x[4] == "acciones")
with ThreadPoolExecutor(8) as ex:
    s10 = {tk: f for tk, f in zip(tks, ex.map(lambda t: gratis.yahoo_ohlcv(t + ".BA", "10y"), tks)) if len(f) > 500}
merval = {f: c for f, c in gratis.yahoo("^MERV", "10y")}
macro = gratis.series_macro(10)
rp, ccl = macro.get("riesgo_pais") or {}, macro.get("ccl") or {}
print(f"::notice::{len(s10)} acciones, {sum(len(v) for v in s10.values())} velas; desde {min(v[0]['fecha'] for v in s10.values())}; riesgo país desde {min(rp) if rp else '-'}, ccl desde {min(ccl) if ccl else '-'}")
fechas_ccl = sorted(ccl)
import bisect
def en_usd(f):
    out = []
    for x in f:
        j = bisect.bisect_right(fechas_ccl, x["fecha"]) - 1
        if j < 0:
            continue
        c = ccl[fechas_ccl[j]]
        out.append({**x, "c": x["c"] / c, "h": x["h"] / c, "l": x["l"] / c, "o": (x.get("o") or x["c"]) / c})
    return out
def corte(ser, desde):
    return {tk: [x for x in f if x["fecha"] >= desde] for tk, f in ser.items()}
mer_usd = {f: v / ccl[fechas_ccl[bisect.bisect_right(fechas_ccl, f) - 1]] for f, v in merval.items() if fechas_ccl and f >= fechas_ccl[0]}
pruebas = {
    "pesos_10a": (s10, merval),
    "usd_10a": ({tk: en_usd(f) for tk, f in s10.items()}, mer_usd),
}
from datetime import date, timedelta
d5 = (date.today() - timedelta(days=365 * 5)).isoformat()
pruebas["usd_5a"] = (corte(pruebas["usd_10a"][0], d5), {f: v for f, v in mer_usd.items() if f >= d5})
mejor = None
for nom, (ser, mv) in pruebas.items():
    try:
        m = A.entrenar_arg({k: v for k, v in ser.items() if len(v) > 300}, mv, rp, ccl)
        p = m.get("prueba") or {}
        print(f"::notice::{nom}: activo={m.get('activo')} " + json.dumps(p) + " | " + str(m.get("importancia"))[:200])
        if m.get("activo") and (not mejor or p.get("ret5_top10", 0) > mejor[1]["prueba"]["ret5_top10"]):
            mejor = (nom, m)
    except Exception:
        print(f"::notice::{nom} ERROR " + traceback.format_exc().replace(chr(10), " | ")[-600:])
if mejor:
    mejor[1]["version"] = mejor[0]
    a.put("anticipo_arg/modelo", mejor[1])
    print(f"::notice::APROBÓ {mejor[0]}: se guarda")
else:
    print("::notice::Ninguna aprobó: queda el de 5 años en pesos")
