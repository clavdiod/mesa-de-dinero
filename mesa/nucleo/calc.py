"""Cálculos de mercado puros (sin red): indicadores, soportes, patrones parecidos, TIR y flujos."""
from __future__ import annotations

from datetime import date

import numpy as np


def sma(x: list[float], n: int) -> float | None:
    return float(np.mean(x[-n:])) if len(x) >= n else None


def rsi(x: list[float], n: int = 14) -> float | None:
    if len(x) < n + 1:
        return None
    d = np.diff(np.array(x[-(n + 1):], dtype=float))
    sub = d[d > 0].sum() / n
    baj = -d[d < 0].sum() / n
    if baj == 0:
        return 100.0
    return float(100 - 100 / (1 + sub / baj))


def atr(velas: list[dict], n: int = 14) -> float | None:
    if len(velas) < n + 1:
        return None
    trs = []
    for prev, v in zip(velas[-(n + 1):-1], velas[-n:]):
        trs.append(max(v["maximo"] - v["minimo"], abs(v["maximo"] - prev["cierre"]), abs(v["minimo"] - prev["cierre"])))
    return float(np.mean(trs))


def pivotes(velas: list[dict], lado: str = "min", ancho: int = 2) -> list[float]:
    """Mínimos (o máximos) locales: más bajos que `ancho` ruedas a cada lado."""
    campo = "minimo" if lado == "min" else "maximo"
    vals = [v[campo] for v in velas]
    out = []
    for i in range(ancho, len(vals) - ancho):
        ventana = vals[i - ancho:i + ancho + 1]
        if (lado == "min" and vals[i] == min(ventana)) or (lado == "max" and vals[i] == max(ventana)):
            out.append(vals[i])
    return out


def niveles(velas: list[dict], lado: str = "min", tolerancia_pct: float = 1.5, ultimas: int = 120) -> list[dict]:
    """Agrupa pivotes cercanos en zonas. Cada zona: nivel promedio, cuántas veces tocó, rango."""
    pts = sorted(pivotes(velas[-ultimas:], lado))
    zonas: list[list[float]] = []
    for p in pts:
        if zonas and abs(p / np.mean(zonas[-1]) - 1) * 100 <= tolerancia_pct:
            zonas[-1].append(p)
        else:
            zonas.append([p])
    return [{"nivel": float(np.mean(z)), "toques": len(z), "desde": min(z), "hasta": max(z)} for z in zonas]


def soporte_cercano(velas: list[dict], precio: float) -> dict | None:
    zs = [z for z in niveles(velas, "min") if z["nivel"] <= precio * 1.005]
    return max(zs, key=lambda z: z["nivel"]) if zs else None


def resistencia_cercana(velas: list[dict], precio: float) -> dict | None:
    zs = [z for z in niveles(velas, "max") if z["nivel"] >= precio * 1.01]
    return min(zs, key=lambda z: z["nivel"]) if zs else None


def patrones_parecidos(cierres: list[float], ventana: int = 20, corr_min: float = 0.85,
                       horizontes: tuple[int, ...] = (5, 10, 20), fechas: list[str] | None = None) -> dict:
    """Busca en la historia tramos con forma parecida a las últimas `ventana` ruedas (correlación de
    precios normalizados) y mide qué pasó después. Devuelve casos, % de subas y rendimiento promedio.
    Si se pasan las fechas de cada cierre, también devuelve `detalle`: cuándo fue cada caso y qué pasó."""
    x = np.array(cierres, dtype=float)
    hmax = max(horizontes)
    if len(x) < ventana * 2 + hmax:
        return {"casos": 0, "horizontes": {}}
    actual = x[-ventana:]
    a = (actual - actual.mean()) / (actual.std() or 1)
    casos, corrs = [], {}
    ultimo_fin = -10 ** 9
    for fin in range(ventana, len(x) - hmax - ventana):  # no solapar con el tramo actual
        tramo = x[fin - ventana:fin]
        s = tramo.std()
        if s == 0:
            continue
        b = (tramo - tramo.mean()) / s
        c = float(np.dot(a, b) / ventana)
        if c >= corr_min and fin - ultimo_fin >= ventana // 2:  # evita contar el mismo episodio varias veces
            casos.append(fin)
            corrs[fin] = c
            ultimo_fin = fin
    res = {}
    for h in horizontes:
        rets = [(x[f - 1 + h] / x[f - 1] - 1) * 100 for f in casos]
        if rets:
            res[h] = {"subas": int(sum(r > 0 for r in rets)), "promedio_pct": round(float(np.mean(rets)), 2),
                      "mediana_pct": round(float(np.median(rets)), 2)}
    out = {"casos": len(casos), "horizontes": res}
    if fechas and len(fechas) == len(x):
        out["detalle"] = [{"desde": fechas[f - ventana], "hasta": fechas[f - 1], "correlacion": round(corrs[f], 2),
                           "precio": round(float(x[f - 1]), 4),
                           "despues": {str(h): round(float((x[f - 1 + h] / x[f - 1] - 1) * 100), 2) for h in horizontes}}
                          for f in casos]
    return out


# ---------- renta fija ----------
def flujo_por_nominales(on: dict, nominales: float, desde: date) -> list[dict]:
    """Flujo futuro (desde la fecha dada) para una cantidad de nominales, según ons.yaml."""
    out = []
    for f in on.get("flujos", []):
        fd = date.fromisoformat(str(f["fecha"]))
        if fd <= desde:
            continue
        interes = nominales * float(f.get("interes", 0)) / 100
        amort = nominales * float(f.get("amortizacion", 0)) / 100
        out.append({"fecha": fd.isoformat(), "interes": round(interes, 2), "amortizacion": round(amort, 2),
                    "total": round(interes + amort, 2)})
    return out


def tir(precio_por_100: float, flujo_por_100: list[dict], hoy: date) -> float | None:
    """TIR efectiva anual (%) por bisección. Flujos por cada 100 nominales."""
    if not flujo_por_100:
        return None
    pts = [((date.fromisoformat(f["fecha"]) - hoy).days / 365.0, f["total"]) for f in flujo_por_100]

    def vpn(r):
        return sum(c / (1 + r) ** t for t, c in pts) - precio_por_100

    lo, hi = -0.9, 5.0
    if vpn(lo) * vpn(hi) > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        if vpn(lo) * vpn(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return round((lo + hi) / 2 * 100, 2)


def simular_on(on: dict, precio_por_100: float, hoy: date, capital: float | None = None,
               nominales: float | None = None) -> dict:
    """Simulador: con capital calcula nominales (respetando lámina mínima); con nominales, el costo."""
    lamina = float(on.get("lamina_minima", 1) or 1)
    if nominales is None:
        if capital is None:
            raise ValueError("Indicar capital o nominales")
        nominales = (capital / (precio_por_100 / 100)) // lamina * lamina
    costo = nominales * precio_por_100 / 100
    flujo = flujo_por_nominales(on, nominales, hoy)
    total = sum(f["total"] for f in flujo)
    return {"nominales": nominales, "costo": round(costo, 2), "flujo": flujo, "total_cobrar": round(total, 2),
            "ganancia": round(total - costo, 2),
            "tir_pct": tir(precio_por_100, flujo_por_nominales(on, 100, hoy), hoy)}


SPREAD_MAX_CREIBLE = 8.0  # más que esto casi siempre es un libro vacío (fuera de horario o sin operadores), no un costo real


def spread_pct(t: dict | None, hora: str | None = None) -> float | None:
    """Diferencia entre la punta vendedora y la compradora, en % (lo que se pierde por entrar y salir enseguida).
    None si no hay puntas, el libro está cruzado (pre-apertura), es fuera del horario de BYMA (11 a 17: después del
    cierre las puntas que quedan son ofertas sueltas, no precios reales) o la diferencia es absurda."""
    t = t or {}
    if hora and not ("11:00" <= hora < "17:00"):
        return None
    c, v = t.get("compra"), t.get("venta")
    if not c or not v or v < c:
        return None
    sp = round((v / c - 1) * 100, 2)
    return sp if sp <= SPREAD_MAX_CREIBLE else None
