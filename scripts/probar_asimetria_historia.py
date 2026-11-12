"""12/11: ¿funciona el agente asimétrico? Se prueba con las elecciones de 2021, 2023 y 2025.
Para cada mes desde 12 meses antes de cada elección: qué decía el agente (escenarios de paridad de salida 35/50/90%)
y qué pasó de verdad vendiendo 5 ruedas después de la elección (precio real + lo cobrado en el medio).
Precios en dólares MEP (D) sin ajustar, por 100 nominales originales (IOL). Flujos aproximados de los prospectos 2020."""
from datetime import date, timedelta
import numpy as np
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos.consumo import Consumo
from mesa.datos.iol import IOL

a = almacen_por_defecto(); iol = IOL(Consumo(a), almacen=a)


def semis(desde, hasta):
    out, y, m = [], desde[0], desde[1]
    while (y, m) <= hasta:
        out.append(date(y, m, 9)); m += 6
        if m > 12: m -= 12; y += 1
    return out


AMORT = {  # (primera, última) cuota semestral (año, mes) y cuántas
    "GD29": (semis((2025, 1), (2029, 7)), None), "GD30": (semis((2025, 1), (2030, 7)), (date(2024, 7, 9), 4.0)),
    "GD35": (semis((2031, 1), (2035, 7)), None), "GD38": (semis((2027, 7), (2038, 1)), None),
    "GD41": (semis((2028, 1), (2041, 7)), None), "GD46": (semis((2025, 1), (2046, 7)), None)}
CUPON = {  # tasa anual por tramo: (desde, tasa)
    "GD29": [(date(2020, 1, 1), 1.0)],
    "GD30": [(date(2020, 1, 1), 0.125), (date(2021, 7, 10), 0.5), (date(2023, 7, 10), 0.75), (date(2027, 7, 10), 1.75)],
    "GD35": [(date(2020, 1, 1), 0.125), (date(2021, 7, 10), 1.125), (date(2022, 7, 10), 1.5), (date(2027, 7, 10), 3.625), (date(2028, 7, 10), 4.125), (date(2029, 7, 10), 4.75), (date(2030, 7, 10), 5.0)],
    "GD38": [(date(2020, 1, 1), 0.125), (date(2021, 7, 10), 2.0), (date(2022, 7, 10), 3.875), (date(2023, 7, 10), 4.25), (date(2024, 7, 10), 5.0)],
    "GD41": [(date(2020, 1, 1), 0.125), (date(2021, 7, 10), 2.5), (date(2022, 7, 10), 3.5), (date(2029, 7, 10), 4.875)],
    "GD46": [(date(2020, 1, 1), 0.125), (date(2021, 7, 10), 1.125), (date(2022, 7, 10), 1.5), (date(2027, 7, 10), 3.625), (date(2028, 7, 10), 4.125), (date(2029, 7, 10), 4.375), (date(2030, 7, 10), 5.0)]}


def flujos(b):
    cuotas, extra = AMORT[b]
    am = {d: 100 * (1 - (extra[1] / 100 if extra else 0)) / len(cuotas) for d in cuotas}
    if extra:
        am[extra[0]] = am.get(extra[0], 0) + extra[1]
    fechas = sorted(set(semis((2021, 1), (2046, 1))) | set(am))
    res, out = 100.0, []
    for d in fechas:
        if res <= 0.001:
            break
        tasa = [t for f, t in CUPON[b] if f <= d][-1]
        out.append((d, res * tasa / 100 / 2, am.get(d, 0.0)))
        res -= am.get(d, 0.0)
    return out


def residual(fl, d):
    return 100 - sum(x for f, _, x in fl if f <= d)


ELECCIONES = {"2021 legislativa": (date(2021, 11, 14), date(2021, 11, 22)), "2023 presidencial": (date(2023, 11, 19), date(2023, 11, 27)),
              "2025 legislativa": (date(2025, 10, 26), date(2025, 11, 3))}
BONOS = {"GD29": "AL29D", "GD30": "AL30D", "GD35": "AL35D", "GD38": "AE38D", "GD41": "AL41D", "GD46": "GD46D"}
ESC = {"pesimista": 0.35, "reestructuracion": 0.50, "optimista": 0.90}
series = {}
for b, tk in BONOS.items():
    try:
        v = iol.historial(tk, date(2020, 10, 1), date(2026, 11, 11), ajustada=False)
        series[b] = {x["fecha"]: x["cierre"] for x in v if x.get("cierre")}
    except Exception as ex:
        print(f"::notice::{tk} ERR {ex}")
print("::notice::series: " + ", ".join(f"{b}:{len(s)}" for b, s in series.items()))


def precio(b, d):
    s = series.get(b) or {}
    ks = sorted(k for k in s if k <= d.isoformat())
    return s[ks[-1]] if ks else None


casos, min_par = [], {}
for nombre, (elec, salida) in ELECCIONES.items():
    for b in BONOS:
        fl = flujos(b)
        px = precio(b, salida)
        if not px:
            continue
        par_sal = px / residual(fl, salida)
        print(f"::notice::{nombre} · {b}: paridad real a la salida {par_sal * 100:.0f}%")
        for k in range(12, 0, -1):
            t = elec - timedelta(days=30 * k)
            pt = precio(b, t)
            if not pt:
                continue
            cob = sum(i + am for f, i, am in fl if t < f <= salida)
            rs = residual(fl, salida)
            esc = {e: (p * rs + cob) / pt - 1 for e, p in ESC.items()}
            ratio = esc["optimista"] / -esc["pesimista"] if esc["pesimista"] < 0 and esc["optimista"] > 0 else 9.9
            real = (px + cob) / pt - 1
            casos.append((nombre, b, k, ratio, real, esc["pesimista"], esc["optimista"], pt / residual(fl, t)))
# paridades extremas de la historia (para calibrar el escenario pesimista)
for b in BONOS:
    fl = flujos(b)
    ps = [(f, p / residual(fl, date.fromisoformat(f))) for f, p in (series.get(b) or {}).items() if residual(fl, date.fromisoformat(f)) > 0]
    if ps:
        lo = min(ps, key=lambda x: x[1]); hi = max(ps, key=lambda x: x[1])
        min_par[b] = (lo, hi)
print("::notice::paridad mínima y máxima 2020-2026: " + " | ".join(f"{b} mín {lo[1] * 100:.0f}% ({lo[0]}) máx {hi[1] * 100:.0f}% ({hi[0]})" for b, (lo, hi) in min_par.items()))
c = np.array([(x[3], x[4]) for x in casos])
for nom, sel in [("todos", c[:, 0] > -1), ("ratio < 1", c[:, 0] < 1), ("ratio 1 a 2", (c[:, 0] >= 1) & (c[:, 0] < 2)), ("ratio 2 a 3", (c[:, 0] >= 2) & (c[:, 0] < 3)), ("ratio 3 o más", c[:, 0] >= 3)]:
    r = c[sel, 1] * 100
    if len(r):
        print(f"::notice::{nom}: {len(r)} casos · resultado real {r.mean():+.1f}% (mediana {np.median(r):+.1f}%) · ganaron {np.mean(r > 0) * 100:.0f}% · peor {r.min():+.1f}% · mejor {r.max():+.1f}%")
for nombre in ELECCIONES:
    xs = [x for x in casos if x[0] == nombre]
    if xs:
        r = np.array([x[4] for x in xs]) * 100; ra = np.array([x[3] for x in xs])
        alto = [x[4] * 100 for x in xs if x[3] >= 3]
        print(f"::notice::{nombre}: {len(xs)} casos · real {r.mean():+.1f}% · ratio típico {np.median(ra):.1f} · con ratio ≥3: {len(alto)} casos, real {np.mean(alto) if alto else 0:+.1f}%")
