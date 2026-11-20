"""20/11: ¿el termómetro del ciclo (Marks) sirve? 10+ años, gratis.
Argentina: riesgo país contra sus últimos 3 años (alto = miedo) → rendimiento de ARGT (acciones argentinas en dólares) a 6 y 12 meses.
EE.UU.: VIX contra su último año (alto = miedo) y S&P cerca del máximo con VIX bajo (euforia) → SPY a 6 y 12 meses."""
import bisect
import numpy as np
from mesa.datos import gratis
def serie(sym): return {x["fecha"]: x["c"] for x in gratis.yahoo_ohlcv(sym, "max")}
argt, spy, vix = serie("ARGT"), serie("SPY"), serie("^VIX")
rp = gratis.series_macro(12).get("riesgo_pais") or {}
def fw(s, fs, i, d): return s[fs[i + d]] / s[fs[i]] - 1 if i + d < len(fs) else None
def tabla(nom, grupos):
    out = []
    for k, xs in grupos.items():
        for h in (126, 252):
            v = np.array([x[h] for x in xs if x.get(h) is not None])
            if len(v) >= 20:
                out.append(f"{k} {h // 21}m: mediana {np.median(v) * 100:+.1f}% sube {np.mean(v > 0) * 100:.0f}% peor10 {np.percentile(v, 10) * 100:+.0f}% (n {len(v)})")
    print(f"::notice::{nom} | " + " | ".join(out))
# Argentina
fs = sorted(argt); rf = sorted(rp); g = {"miedo (riesgo país en el 30% más alto de 3 años)": [], "medio": [], "calma (30% más bajo)": []}
for i in range(0, len(fs) - 1, 5):
    f = fs[i]; j = bisect.bisect_right(rf, f) - 1
    if j < 756: continue
    w = [rp[x] for x in rf[j - 756:j + 1]]; pct = np.mean(np.array(w) < rp[rf[j]])
    k = "miedo (riesgo país en el 30% más alto de 3 años)" if pct >= 0.7 else "calma (30% más bajo)" if pct <= 0.3 else "medio"
    g[k].append({126: fw(argt, fs, i, 126), 252: fw(argt, fs, i, 252)})
tabla(f"ARGENTINA ARGT {fs[0][:4]}-{fs[-1][:4]}", g)
j = len(rf) - 1; w = [rp[x] for x in rf[j - 756:j + 1]]
print(f"::notice::HOY riesgo país {rp[rf[-1]]:.0f}: percentil {np.mean(np.array(w) < rp[rf[-1]]) * 100:.0f} de 3 años")
# EE.UU.
fs = sorted(set(spy) & set(vix)); g = {"miedo (VIX en el 20% más alto del año)": [], "euforia (VIX 20% más bajo y S&P a 2% del máximo)": [], "resto": []}
for i in range(252, len(fs) - 1, 5):
    f = fs[i]; w = np.array([vix[x] for x in fs[i - 251:i + 1]]); pv = np.mean(w < vix[f])
    mx = max(spy[x] for x in fs[i - 251:i + 1])
    k = ("miedo (VIX en el 20% más alto del año)" if pv >= 0.8 else
         "euforia (VIX 20% más bajo y S&P a 2% del máximo)" if pv <= 0.2 and spy[f] >= mx * 0.98 else "resto")
    g[k].append({126: fw(spy, fs, i, 126), 252: fw(spy, fs, i, 252)})
tabla(f"EEUU SPY {fs[252][:4]}-{fs[-1][:4]}", g)
w = np.array([vix[x] for x in fs[-252:]])
print(f"::notice::HOY VIX {vix[fs[-1]]:.1f}: percentil {np.mean(w < vix[fs[-1]]) * 100:.0f} del año · S&P a {(spy[fs[-1]] / max(spy[x] for x in fs[-252:]) - 1) * 100:+.1f}% del máximo")
