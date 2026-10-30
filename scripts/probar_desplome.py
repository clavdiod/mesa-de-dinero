"""Desplomes de un día (-15% o más) en CEDEARs/acciones de EE.UU. (10 años): ¿qué pasa después? Y STNE desde el 26/10."""
import traceback
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
a = almacen_por_defecto()
try:
    f = gratis.yahoo_ohlcv("STNE", "1mo")
    print("::notice::STNE: " + " | ".join(f"{x['fecha'][5:]} o{x['o']:.2f} c{x['c']:.2f} min{x['l']:.2f}" for x in f[-10:]))
    uni = sorted(set(_universo_cedears(a)) | {"STNE", "PAGS", "NU", "MELI", "XP", "VALE", "PBR", "ITUB", "BBD"})
    with ThreadPoolExecutor(8) as ex:
        ser = {tk: s for tk, s in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "10y"), uni)) if len(s) > 300}
    res = {"todas": [], "en_minimo_anual": [], "no_minimo": []}
    d1, d5, d60 = [], [], []
    for tk, s in ser.items():
        c = np.array([x["c"] for x in s]); o = np.array([x.get("o") or x["c"] for x in s])
        for i in range(260, len(c) - 61):
            if c[i] / c[i - 1] - 1 <= -0.15:
                r20 = c[i + 20] / o[i + 1] - 1
                res["todas"].append(r20)
                (res["en_minimo_anual"] if c[i] < c[i - 250:i].min() else res["no_minimo"]).append(r20)
                d1.append(c[i + 1] / c[i] - 1); d5.append(c[i + 5] / c[i] - 1); d60.append(c[i + 60] / o[i + 1] - 1)
    def r(v):
        v = np.array(v) * 100
        return f"{len(v)} casos, {v.mean():+.1f}% (mediana {np.median(v):+.1f}%), suben 10%+ {np.mean(v >= 10) * 100:.0f}%, caen 10%+ {np.mean(v <= -10) * 100:.0f}%"
    print(f"::notice::Desplome -15% en un día, comprar al día siguiente y tener 20 ruedas: {r(res['todas'])} | si además perforó el mínimo anual: {r(res['en_minimo_anual'])} | si no: {r(res['no_minimo'])}")
    print(f"::notice::Después del desplome: día siguiente {np.mean(d1) * 100:+.1f}%, a 5 ruedas {np.mean(d5) * 100:+.1f}%, a 60 ruedas (3 meses) {r(d60)}")
except Exception:
    print("::notice::ERR " + traceback.format_exc().replace(chr(10), " | ")[-500:])
