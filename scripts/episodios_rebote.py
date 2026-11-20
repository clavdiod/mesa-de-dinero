"""20/11: los casos parecidos de YPFD/TGSU2/CEPU (caídas fuertes en dólares): ¿en cuántos episodios distintos? y la tesis
de Nacho (Merval USD contra riesgo país), con las fechas alineadas a la rueda más cercana."""
import bisect, traceback
import numpy as np
from mesa.datos import gratis
ccl = gratis.ccl_historico(); fc = sorted(ccl)
usd = lambda f, p: p / ccl[fc[bisect.bisect_right(fc, f) - 1]] if fc and f >= fc[0] else None
for tk, dd, r20 in (("YPFD", -0.37, -0.29), ("TGSU2", -0.29, -0.17), ("CEPU", -0.24, -0.12)):
    h = [(f, usd(f, p)) for f, p in gratis.yahoo(tk + ".BA", "10y") if usd(f, p)]
    fs = [f for f, _ in h]; s = np.array([u for _, u in h]); ep = {}
    for i in range(60, len(s) - 60):
        if abs(s[i] / s[i - 59:i + 1].max() - 1 - dd) <= 0.05 and abs(s[i] / s[i - 20] - 1 - r20) <= 0.07:
            ep.setdefault(fs[i][:7], []).append(s[i + 60] / s[i] - 1)
    print(f"::notice::{tk}: episodios (mes: casos, mediana 3m) " + " | ".join(f"{k}: {len(v)}, {np.median(v) * 100:+.0f}%" for k, v in ep.items()))
try:
    rp = gratis.series_macro(10).get("riesgo_pais") or {}
    mer = gratis.yahoo("^MERV", "10y")
    rf = sorted(rp)
    pares = []
    for f, v in mer:
        u = usd(f, v); j = bisect.bisect_right(rf, f) - 1
        if u and j >= 0:
            pares.append((f, u, rp[rf[j]]))
    print(f"::notice::series: merval {len(mer)} riesgo país {len(rp)} ({rf[0] if rf else None} a {rf[-1] if rf else None}) pares {len(pares)}")
    fs = [p[0] for p in pares]; m = np.array([p[1] for p in pares]); r = np.array([p[2] for p in pares])
    casos, todos = [], []
    for i in range(60, len(fs) - 60, 5):
        dr = r[i] / r[i - 60] - 1; dm = m[i] / m[i - 60] - 1; fw = m[i + 60] / m[i] - 1
        todos.append(fw)
        if dr <= -0.15 and dm <= 0.05:
            casos.append((fs[i], fw))
    i = len(fs) - 1
    print(f"::notice::HOY riesgo país {r[i]:.0f} ({(r[i] / r[i - 60] - 1) * 100:+.0f}% en 3 meses) · Merval USD {(m[i] / m[i - 60] - 1) * 100:+.0f}% en 3 meses")
    if casos:
        fw = np.array([c[1] for c in casos])
        print(f"::notice::DESARBITRAJE {len(casos)} momentos en {sorted({c[0][:7] for c in casos})} → Merval USD 3 meses después mediana {np.median(fw) * 100:+.1f}%, sube {np.mean(fw > 0) * 100:.0f}% · cualquier momento {np.median(todos) * 100:+.1f}% (sube {np.mean(np.array(todos) > 0) * 100:.0f}%)")
except Exception:
    print("::notice::ERR " + traceback.format_exc().replace(chr(10), ' | ')[-400:])
