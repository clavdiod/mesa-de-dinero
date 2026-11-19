"""19/11: ¿la revisión en frío es muy severa? Pregunta de Clau.

Se reproducen las reglas de 'entrada cara' de ficha_frio con 10 años de historia (solo datos del pasado en cada fecha):
  E: 6% o más arriba del promedio de 20 ruedas      R: en el 15% más alto del rango de 3 meses
  P: lo típico que sube en un mes no paga 1,5 veces el riesgo hasta el stop
  M: hasta el máximo del año no hay 2 veces el riesgo  T: (solo CEDEARs) en el 20% más alto de los precios del año
Cada caso se opera como la mesa: entra a la apertura siguiente, stop a 2 veces el movimiento diario normal (3% a 10%),
objetivo 2 veces el riesgo, máximo 20 ruedas. Se descuenta 1,2% de comisiones (ida y vuelta, como COST).
Se mira sobre todo los papeles que vienen subiendo (lo que votan los analistas) y se compara pasa / no pasa.
"""
import traceback
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipadores as A
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears

a = almacen_por_defecto()
COM = 0.012


def sma(x, n):
    cs = np.cumsum(np.r_[0, x]); out = np.full(len(x), np.nan); out[n - 1:] = (cs[n:] - cs[:-n]) / n
    return out


def probar(nombre, ser, cedear):
    filas = []
    for tk, f in ser.items():
        c = np.array([x["c"] for x in f], float); o = np.array([x.get("o") or x["c"] for x in f], float)
        h = np.array([x.get("h") or x["c"] for x in f], float); l = np.array([x.get("l") or x["c"] for x in f], float)
        n = len(c)
        if n < 520 or (c <= 0).any():
            continue
        m20 = sma(c, 20); d = c / m20 - 1
        r20 = np.full(n, np.nan); r20[20:] = c[20:] / c[:-20] - 1
        mxf = np.full(n, np.nan)
        for i in range(n - 20):
            mxf[i] = c[i + 1:i + 21].max() / c[i] - 1
        tr = np.maximum(h - l, np.abs(np.r_[0, h[1:] - c[:-1]]))
        atr = sma(tr, 14)
        for i in range(400, n - 21, 2):
            ent = o[i + 1]
            if not ent or np.isnan(d[i]):
                continue
            riesgo = float(np.clip(2 * atr[i] / c[i], 0.03, 0.10))
            # reglas (con datos hasta i)
            hi60, lo60 = c[i - 59:i + 1].max(), c[i - 59:i + 1].min()
            pos60 = (c[i] - lo60) / (hi60 - lo60) if hi60 > lo60 else 0.5
            lo_w = max(40, i - 400)
            idx = np.arange(lo_w, i - 20)
            sel = idx[(np.abs(d[idx] - d[i]) <= 0.03) & (np.abs(r20[idx] - r20[i]) <= 0.06)]
            tip = np.median(mxf[sel]) if len(sel) >= 8 else None
            mx1 = c[i - 249:i + 1].max()
            pct1 = (c[i - 249:i + 1] < c[i]).mean()
            reglas = {"E": d[i] >= 0.06, "R": pos60 >= 0.85, "P": tip is not None and tip < 1.5 * riesgo,
                      "M": mx1 / c[i] - 1 < 2 * riesgo, "T": cedear and pct1 >= 0.80}
            # operación como la mesa
            st_, ob = ent * (1 - riesgo), ent * (1 + 2 * riesgo)
            res = None
            for j in range(i + 1, i + 21):
                if l[j] <= st_:
                    res = -riesgo; break
                if h[j] >= ob:
                    res = 2 * riesgo; break
            if res is None:
                res = c[i + 20] / ent - 1
            subiendo = r20[i] >= 0.05 and c[i] > m20[i]
            filas.append((reglas, res - COM, res, subiendo, riesgo))
    if not filas:
        print(f"::notice::{nombre}: sin datos"); return

    def linea(etq, xs):
        if len(xs) < 30:
            return f"{etq}: {len(xs)} casos (pocos)"
        r = np.array([x[1] for x in xs]); rr = np.array([x[1] / x[4] for x in xs])
        return (f"{etq}: {len(xs)} casos · neto {r.mean() * 100:+.2f}% · gana {np.mean(r > 0) * 100:.0f}% · "
                f"en R {rr.mean():+.2f} · peor 10% {np.percentile(r, 10) * 100:+.1f}%")

    for grupo, xs in (("TODOS", filas), ("SUBIENDO (+5% en un mes, arriba del promedio)", [x for x in filas if x[3]])):
        cara = [x for x in xs if any(x[0].values())]
        pasa = [x for x in xs if not any(x[0].values())]
        out = [linea("todos", xs), linea("PASA el frío", pasa), linea("CARA (no pasa)", cara)]
        for k, nom in (("E", "estirada 6%"), ("R", "techo 3 meses"), ("P", "no paga 1,5x"), ("M", "sin lugar hasta máx año"), ("T", "20% alto del año")):
            solo = [x for x in xs if x[0][k] and sum(x[0].values()) == 1]
            out.append(linea(f"frenada SOLO por {nom}", solo))
        # versión más suave: solo las reglas de 'paga o no paga' (P y M), sin E, R ni T
        suave_pasa = [x for x in xs if not (x[0]["P"] or x[0]["M"])]
        out.append(linea("versión suave (solo P y M) — pasa", suave_pasa))
        out.append(linea("frenadas por E/R/T pero pasarían la suave", [x for x in cara if not (x[0]["P"] or x[0]["M"])]))
        print(f"::notice::{nombre} {grupo} | " + " | ".join(out))


try:
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    acc, mer, rp, ccl = A.datos_arg(sorted(tk for tk, x in panel.items() if x and x[4] == "acciones"), 10)
    probar("ARG", acc, False)
except Exception:
    print("::notice::ARG ERR " + traceback.format_exc().replace(chr(10), " | ")[-500:])
try:
    uni = _universo_cedears(a)
    with ThreadPoolExecutor(8) as ex:
        ced = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "10y"), uni)) if len(f) > 520}
    probar("CEDEARs", ced, True)
except Exception:
    print("::notice::CED ERR " + traceback.format_exc().replace(chr(10), " | ")[-500:])
