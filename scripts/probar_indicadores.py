"""RSI, MACD, tendencia (promedios 50/200) y estructura correctiva: ¿qué rindió cada lectura a 20 ruedas? 10 años."""
import traceback
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import anticipadores as A
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
a = almacen_por_defecto()

def ema(x, n):
    k = 2 / (n + 1); out = np.empty_like(x); out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = x[i] * k + out[i - 1] * (1 - k)
    return out

def rsi(c, n=14):
    d = np.diff(c); up = np.where(d > 0, d, 0); dn = np.where(d < 0, -d, 0)
    au, ad = ema(up, 2 * n - 1), ema(dn, 2 * n - 1)
    r = 100 - 100 / (1 + au / np.where(ad == 0, 1e-9, ad))
    return np.r_[50, r]

def probar(nombre, ser):
    g = {}
    add = lambda k, r: g.setdefault(k, []).append(r)
    for tk, f in ser.items():
        c = np.array([x["c"] for x in f], dtype=float); o = np.array([x.get("o") or x["c"] for x in f], dtype=float)
        if len(c) < 260:
            continue
        R = rsi(c); m = ema(c, 12) - ema(c, 26); s = ema(m, 9); h = m - s
        for i in range(210, len(c) - 21, 3):
            r = c[i + 20] / o[i + 1] - 1
            add("todos", r)
            rr = R[i]
            add("RSI <30 (sobrevendido)" if rr < 30 else "RSI 30-50" if rr < 50 else "RSI 50-70" if rr < 70 else "RSI >70 (sobrecomprado)", r)
            if h[i] > 0 and h[i - 1] <= 0:
                add("MACD cruza hacia arriba", r)
            elif h[i] < 0 and h[i - 1] >= 0:
                add("MACD cruza hacia abajo", r)
            add("MACD positivo" if m[i] > s[i] else "MACD negativo", r)
            m50, m200 = c[i - 49:i + 1].mean(), c[i - 199:i + 1].mean()
            tend = "TENDENCIA alcista (precio>50>200)" if c[i] > m50 > m200 else "TENDENCIA bajista (precio<50<200)" if c[i] < m50 < m200 else "TENDENCIA mixta"
            add(tend, r)
            corr = c[i] / c[i - 60:i + 1].max() - 1
            if m50 > m200 and -0.20 <= corr <= -0.08:
                add("CORRECCIÓN dentro de tendencia alcista (-8 a -20%)", r)
                if rr < 40:
                    add("corrección alcista + RSI <40", r)
                if h[i] > 0 and h[i - 1] <= 0:
                    add("corrección alcista + MACD cruza arriba", r)
    print(f"::notice::{nombre} | " + " | ".join(f"{k}: {len(v)} {np.mean(v) * 100:+.2f}% (sube {np.mean(np.array(v) > 0.012) * 100:.0f}%)" for k, v in sorted(g.items())))
try:
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    acc, mer, rp, ccl = A.datos_arg(sorted(tk for tk, x in panel.items() if x and x[4] == "acciones"), 10)
    probar("ARG", acc)
except Exception:
    print("::notice::ARG ERR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
try:
    uni = _universo_cedears(a)
    with ThreadPoolExecutor(8) as ex:
        ced = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "10y"), uni)) if len(f) > 400}
    probar("CEDEARs", ced)
except Exception:
    print("::notice::CED ERR " + traceback.format_exc().replace(chr(10), " | ")[-400:])
