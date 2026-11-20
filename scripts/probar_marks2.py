"""20/11 (Marks, Lo más importante): ¿las acciones que más se mueven rinden más o solo duelen más? CEDEARs, 10 años:
cada 21 ruedas se ordenan por volatilidad del último año; rendimiento a 12 meses contra SPY y peor caída en esos 12 meses."""
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos import gratis
from mesa.agentes.posiciones import APALANCADOS
from mesa.agentes.ficha_frio import COBERTURAS
a = almacen_por_defecto(); pan = (a.get("ui/panel") or {}).get("titulos") or {}
uni = [t for t, x in pan.items() if x and len(x) > 4 and x[4] == "cedears" and t.isalpha() and not t.endswith(("D", "C")) and t not in APALANCADOS | COBERTURAS]
with ThreadPoolExecutor(8) as ex:
    ser = {t: {x["fecha"]: x["c"] for x in v} for t, v in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "10y"), uni)) if len(v) > 600}
spy = {x["fecha"]: x["c"] for x in gratis.yahoo_ohlcv("SPY", "10y")}; fs = sorted(spy)
G = {q: {"ex": [], "dd": [], "abs": []} for q in range(5)}
for k in range(252, len(fs) - 252, 21):
    f0, f1 = fs[k], fs[k + 252]; rs = spy[f1] / spy[f0] - 1; filas = []
    for t, s in ser.items():
        if not all(f in s for f in (fs[k - 252], f0, f1)): continue
        past = np.array([s[f] for f in fs[k - 252:k + 1] if f in s]); fut = np.array([s[f] for f in fs[k:k + 253] if f in s])
        if len(past) < 200 or len(fut) < 200: continue
        vol = np.std(np.diff(np.log(past))) * np.sqrt(252)
        dd = (fut / np.maximum.accumulate(fut) - 1).min()
        filas.append((vol, s[f1] / s[f0] - 1 - rs, dd, s[f1] / s[f0] - 1))
    if len(filas) < 50: continue
    filas.sort(); n = len(filas) // 5
    for q in range(5):
        for v, e, d, r in filas[q * n:(q + 1) * n]:
            G[q]["ex"].append(e); G[q]["dd"].append(d); G[q]["abs"].append(r)
nom = ["más tranquilas (20%)", "2º", "3º", "4º", "más movedizas (20%)"]
print(f"::notice::{len(ser)} CEDEARs · " + " | ".join(
    f"{nom[q]}: 12m mediana {np.median(G[q]['abs']) * 100:+.1f}% · contra SPY {np.median(G[q]['ex']) * 100:+.1f}% (le gana {np.mean(np.array(G[q]['ex']) > 0) * 100:.0f}%) · "
    f"peor caída típica {np.median(G[q]['dd']) * 100:.0f}% · cae 40%+ en {np.mean(np.array(G[q]['dd']) <= -0.4) * 100:.0f}% · pierde 30%+ en el año {np.mean(np.array(G[q]['abs']) <= -0.3) * 100:.0f}%" for q in range(5)))
