"""Anticipador ARG con TODA la historia de Yahoo (range=max). CCL de antes de 2013 = implícito de Galicia (GGAL.BA x10 / GGAL).
Examen fijo: últimos 3 años, igual que el de 10 años en uso. Guarda solo si gana."""
import json, traceback, bisect
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from mesa.agentes import anticipadores as A
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
panel = (a.get("ui/panel") or {}).get("titulos") or {}
tks = sorted(tk for tk, x in panel.items() if x and x[4] == "acciones")
with ThreadPoolExecutor(8) as ex:
    ser = {tk: f for tk, f in zip(tks, ex.map(lambda t: gratis.yahoo_ohlcv(t + ".BA", "max"), tks)) if len(f) > 300}
macro = gratis.series_macro(30)
rp, ccl = macro.get("riesgo_pais") or {}, dict(macro.get("ccl") or {})
ba = {f: c for f, c in gratis.yahoo("GGAL.BA", "max")}
ny = {f: c for f, c in gratis.yahoo("GGAL", "max")}
d0 = min(ccl) if ccl else "9999"
imp = {f: ba[f] * 10 / ny[f] for f in ba if f in ny and ny[f] and f < d0}
# empalme: el implícito se ajusta para que coincida con el CCL oficial en el primer mes en común
com = [f for f in ba if f in ny and ny[f] and f in ccl][:20]
k = (sum(ccl[f] / (ba[f] * 10 / ny[f]) for f in com) / len(com)) if com else 1.0
ccl.update({f: v * k for f, v in imp.items()})
mer = {f: c for f, c in gratis.yahoo("^MERV", "max")}
desde_15 = sum(1 for v in ser.values() if v[0]["fecha"] <= (date.today() - timedelta(days=365 * 15)).isoformat())
print(f"::notice::{len(ser)} acciones; velas desde {min(v[0]['fecha'] for v in ser.values())}; con 15+ años: {desde_15}; "
      f"merval desde {min(mer) if mer else '-'}; CCL desde {min(ccl) if ccl else '-'} (implícito {len(imp)} días, ajuste {k:.3f}); riesgo país desde {min(rp) if rp else '-'}")
acc = {k_: v for k_, v in A.a_dolares(ser, ccl).items() if len(v) > 300}
mv = A.merval_dolares(mer, ccl)
examen = (date.today() - timedelta(days=365 * 3)).isoformat()
res = {}
for anios in (10, 15, 20, 30):
    d = (date.today() - timedelta(days=365 * anios)).isoformat()
    s_ = {tk: [x for x in f if x["fecha"] >= d] for tk, f in acc.items()}
    s_ = {k_: v for k_, v in s_.items() if len(v) > 300}
    try:
        m = A.entrenar_arg(s_, {f: v for f, v in mv.items() if f >= d}, rp, ccl, desde_prueba=examen)
        res[anios] = m
        print(f"::notice::{anios} años ({sum(len(v) for v in s_.values())} velas): activo={m.get('activo')} " + json.dumps(m.get("prueba")))
    except Exception:
        print(f"::notice::{anios} ERROR " + traceback.format_exc().replace(chr(10), " | ")[-600:])
b = (res.get(10) or {}).get("prueba") or {}
mejor = None
for anios in (15, 20, 30):
    p = (res.get(anios) or {}).get("prueba") or {}
    if res.get(anios, {}).get("activo") and p.get("top10_pct", 0) >= b.get("top10_pct", 0) and p.get("ret5_top10", 0) > b.get("ret5_top10", 0) + 0.2:
        if not mejor or p["ret5_top10"] > mejor[1]["prueba"]["ret5_top10"]:
            mejor = (anios, res[anios])
print("::notice::" + (f"GANÓ {mejor[0]} años (no se guarda todavía: el cierre usa 10)" if mejor else "Más historia no mejora el examen"))
