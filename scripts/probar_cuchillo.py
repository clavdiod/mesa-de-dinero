"""¿Comprar líderes del Merval en el susto (riesgo país +80 pb en 10 ruedas) o esperar a que dejen de caer?
10 años, en dólares CCL. Entrada a la apertura del día siguiente a la señal; salida a 20 ruedas (o stop -10%).
A: comprar ya (lo que hace hoy el Comprador de pánico).
B1: esperar (hasta 40 ruedas) a que cierre arriba de su máximo de las últimas 10 ruedas (deja de hacer máximos más bajos).
B2: esperar a que cierre arriba de su promedio de 20 ruedas y el promedio deje de bajar.
B3: esperar a que el riesgo país baje 5% desde su pico del susto (el miedo cede)."""
import json, traceback, bisect
import numpy as np
from mesa.agentes import anticipadores as A, panico as P
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
H, STOP, ESPERA = 20, -0.10, 40
try:
    acc, mer, rp, ccl = A.datos_arg(P.LIDERES_MERVAL + ["PAMP", "BBAR", "SUPV", "TECO2", "TGNO4", "CRES", "EDN", "COME"], 10)
    fr = sorted(rp)
    sustos = []
    ult = "0000"
    for i in range(10, len(fr)):
        if rp[fr[i]] / rp[fr[i - 10]] - 1 >= 0.12 and fr[i] > ult:  # relativo: +80 pb a 700 es +12%
            sustos.append(fr[i]); 
            ult = fr[min(len(fr) - 1, i + 20)]  # un susto por mes como mucho
    print(f"::notice::{len(sustos)} sustos en 10 años: " + ", ".join(sustos))
    def salida(f, j):
        p0 = f[j].get("o") or f[j]["c"]
        for k in range(j, min(len(f), j + H)):
            if f[k]["l"] / p0 - 1 <= STOP:
                return STOP
        k = min(len(f) - 1, j + H - 1)
        return f[k]["c"] / p0 - 1
    res = {"A": [], "B1": [], "B2": [], "B3": []}
    perdidas = {"B1": 0, "B2": 0, "B3": 0}
    for s in sustos:
        pico_i = bisect.bisect_left(fr, s)
        for tk, f in acc.items():
            fs = [x["fecha"] for x in f]
            i = bisect.bisect_right(fs, s) - 1
            if i < 30 or i + 1 + ESPERA + H >= len(f):
                continue
            res["A"].append((s, tk, salida(f, i + 1)))
            c = [x["c"] for x in f]
            for key in ("B1", "B2", "B3"):
                hit = None
                for j in range(i, i + ESPERA):
                    if key == "B1" and c[j] > max(c[j - 10:j]):
                        hit = j
                    elif key == "B2":
                        m = np.mean(c[j - 19:j + 1]); m_ant = np.mean(c[j - 24:j - 4])
                        if c[j] > m and m >= m_ant:
                            hit = j
                    elif key == "B3":
                        k = bisect.bisect_right(fr, f[j]["fecha"]) - 1
                        pico = max(rp[x] for x in fr[pico_i:k + 1]) if k >= pico_i else rp[fr[pico_i]]
                        if rp[fr[k]] <= pico * 0.95:
                            hit = j
                    if hit:
                        break
                if hit:
                    res[key].append((s, tk, salida(f, hit + 1), (c[hit] / c[i] - 1)))
                else:
                    perdidas[key] += 1
    # base: cualquier día, mismas acciones
    base = []
    for tk, f in acc.items():
        for j in range(30, len(f) - H, 7):
            base.append(salida(f, j))
    def r(xs):
        v = np.array([x[2] for x in xs]) * 100
        return f"{len(v)} compras, promedio {v.mean():+.2f}%, mediana {np.median(v):+.2f}%, ganan {np.mean(v > 1.2) * 100:.0f}%, neto {v.mean() - 1.2:+.2f}%, stop {np.mean(v <= STOP * 100 + 0.01) * 100:.0f}%"
    b = np.array(base) * 100
    print(f"::notice::Base (cualquier día): promedio {b.mean():+.2f}%, ganan {np.mean(b > 1.2) * 100:.0f}%")
    for k, nom in (("A", "A comprar en el susto"), ("B1", "B1 esperar máximo de 10 ruedas"), ("B2", "B2 esperar promedio 20 que deja de bajar"), ("B3", "B3 esperar que el riesgo país baje 5%")):
        extra = ""
        if k != "A":
            extra = f" | sin señal en 40 ruedas: {perdidas[k]} | pagaste {np.mean([x[3] for x in res[k]]) * 100:+.1f}% más que en el susto"
        print(f"::notice::{nom}: {r(res[k])}{extra}")
    for k in ("A", "B2"):
        for desde, hasta in (("2000", "2021-12-31"), ("2022-01-01", "2099")):
            v = np.array([x[2] for x in res[k] if desde <= x[0] <= hasta]) * 100
            if len(v):
                print(f"::notice::{k} {desde[:4]}-{hasta[:4]}: {len(v)} compras, promedio {v.mean():+.2f}%, ganan {np.mean(v > 1.2) * 100:.0f}%")
    sustos_ = []
    for s in sustos_:
        va = [x[2] for x in res["A"] if x[0] == s]; vb = [x[2] for x in res["B1"] if x[0] == s]
        if va:
            print(f"::notice::susto {s} (rp {rp[s]:.0f}): A {np.mean(va) * 100:+.1f}% | B1 {np.mean(vb) * 100 if vb else float('nan'):+.1f}% ({len(vb)}/{len(va)})")
except Exception:
    print("::notice::ERR " + traceback.format_exc().replace(chr(10), " | ")[-700:])
