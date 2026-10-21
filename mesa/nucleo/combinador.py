"""El Jefe que aprende combinaciones.

En vez de sumar votos con pesos fijos, aprende con la historia qué COMBINACIONES de agentes y contextos
terminaron en ganancia (más que la comisión) a 20 ruedas. Ejemplo: "Wall Street a favor + Bitcoin alcista"
puede ganar más seguido que "Wall Street a favor" solo.

Modelo: regresión logística chica (con numpy), sobre la opinión de cada agente (dirección × fuerza), el
contexto (Bitcoin alcista, miedo en Wall Street, riesgo país subiendo) y los cruces más útiles.
Validación honesta: aprende con el primer 70% del tiempo y se evalúa con el 30% final, que nunca vio.
Solo se activa si sus elegidas rinden más que las que elige la suma de votos y más que la comisión.
"""
from __future__ import annotations

import math

import numpy as np

AGENTES = ["tecnico", "historiador", "fuerza_relativa", "economista", "wallstreet", "cripto", "panico"]
CONTEXTO = ["btc_alcista", "miedo_eeuu", "rp_subiendo"]
CRUCES = [("wallstreet", "btc_alcista"), ("wallstreet", "miedo_eeuu"), ("cripto", "btc_alcista"),
          ("panico", "miedo_eeuu"), ("tecnico", "rp_subiendo"), ("economista", "rp_subiendo")]
NOMBRES = AGENTES + CONTEXTO + [f"{a}×{b}" for a, b in CRUCES]
HORIZONTE = 20


def contexto(fecha: str, btc: list[list] | None, vix: list[list] | None, rp: dict[str, float] | None) -> dict:
    out = {k: 0.0 for k in CONTEXTO}
    if btc:
        x = [c for f, c in btc if f <= fecha]
        if len(x) >= 200:
            out["btc_alcista"] = 1.0 if x[-1] > sum(x[-200:]) / 200 else -1.0
    if vix:
        v = [c for f, c in vix if f <= fecha]
        if v:
            out["miedo_eeuu"] = 1.0 if v[-1] >= 25 else 0.0
    if rp:
        fs = [f for f in sorted(rp) if f <= fecha]
        if len(fs) >= 21:
            out["rp_subiendo"] = 1.0 if rp[fs[-1]] - rp[fs[-21]] >= 30 else -1.0 if rp[fs[-1]] - rp[fs[-21]] <= -30 else 0.0
    return out


def vector(senales: dict[str, float], ctx: dict) -> list[float]:
    base = [senales.get(a, 0.0) for a in AGENTES] + [ctx.get(c, 0.0) for c in CONTEXTO]
    return base + [senales.get(a, 0.0) * ctx.get(b, 0.0) for a, b in CRUCES]


def armar_datos(registro: list[tuple], series: dict[str, list[float]], fechas_serie: dict[str, dict[str, int]],
                ctx_de) -> list[dict]:
    """registro: (ticker, fecha, agente, dirección×fuerza). series: precios por ticker (para medir lo que pasó)."""
    from datetime import date as _d
    filas: dict[tuple, dict] = {}
    primera: dict[tuple, str] = {}
    for tk, f, ag, v in registro:
        if ag in AGENTES and v:
            sem = _d.fromisoformat(f).isocalendar()[:2]  # misma semana = misma "foto" de la mesa
            filas.setdefault((tk, sem), {})[ag] = v
            primera[(tk, sem)] = min(primera.get((tk, sem), f), f)
    datos = []
    for (tk, sem), sen in filas.items():
        f = primera[(tk, sem)]
        if f not in (fechas_serie.get(tk) or {}):  # primera rueda de la serie en o después de esa fecha
            fs = sorted(x for x in (fechas_serie.get(tk) or {}) if x >= f)
            if not fs:
                continue
            f = fs[0]
        i = (fechas_serie.get(tk) or {}).get(f)
        s = series.get(tk)
        if i is None or not s or i + HORIZONTE >= len(s):
            continue
        ret = (s[i + HORIZONTE] / s[i] - 1) * 100
        c = ctx_de(f)
        datos.append({"ticker": tk, "fecha": f, "x": vector(sen, c), "ret": ret, "suma": sum(sen.values())})
    return sorted(datos, key=lambda d: d["fecha"])


def _logistica(X: np.ndarray, y: np.ndarray, l2: float = 1.0, iters: int = 400) -> np.ndarray:
    w = np.zeros(X.shape[1] + 1)
    Xb = np.hstack([np.ones((len(X), 1)), X])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Xb @ w))
        g = Xb.T @ (p - y) / len(y) + l2 * np.r_[0, w[1:]] / len(y)
        w -= 0.5 * g
    return w


def entrenar(datos: list[dict], comision: float = 1.2) -> dict:
    """Aprende con el 70% inicial y se prueba con el 30% final. Compara contra la suma de votos."""
    if len(datos) < 300:
        return {"activo": False, "motivo": f"Pocos casos para aprender combinaciones ({len(datos)}).", "casos": len(datos)}
    corte = int(len(datos) * 0.7)
    tr, te = datos[:corte], datos[corte:]
    X, y = np.array([d["x"] for d in tr]), np.array([1.0 if d["ret"] > comision else 0.0 for d in tr])
    w = _logistica(X, y)
    prob = lambda d: 1 / (1 + math.exp(-(w[0] + float(np.dot(w[1:], d["x"])))))
    k = max(30, len(te) // 4)
    elegidas_modelo = sorted(te, key=prob, reverse=True)[:k]
    elegidas_suma = sorted(te, key=lambda d: d["suma"], reverse=True)[:k]
    prom = lambda xs: sum(d["ret"] for d in xs) / len(xs) if xs else 0.0
    gana = lambda xs: sum(1 for d in xs if d["ret"] > comision) / len(xs) * 100 if xs else 0.0
    m, s_, todas = prom(elegidas_modelo), prom(elegidas_suma), prom(te)
    activo = m > s_ + 0.3 and m > comision
    pesos = sorted(((NOMBRES[i], round(float(w[i + 1]), 3)) for i in range(len(NOMBRES))), key=lambda x: -abs(x[1]))
    umbral = sorted((prob(d) for d in tr), reverse=True)[max(0, len(tr) // 4 - 1)]
    return {"activo": activo, "pesos_w": [float(x) for x in w], "nombres": NOMBRES, "umbral": round(umbral, 3),
            "casos": len(datos), "prueba": {"casos": len(te), "elegidas": k,
                                            "modelo": {"prom": round(m, 2), "gana_pct": round(gana(elegidas_modelo), 1)},
                                            "suma_votos": {"prom": round(s_, 2), "gana_pct": round(gana(elegidas_suma), 1)},
                                            "todas": {"prom": round(todas, 2), "gana_pct": round(gana(te), 1)}},
            "lo_que_aprendio": pesos[:6],
            "motivo": (f"Fuera de muestra, sus elegidas rindieron {m:+.2f}% a 20 ruedas contra {s_:+.2f}% de la suma de votos: se activa." if activo else
                       f"Fuera de muestra, sus elegidas rindieron {m:+.2f}% a 20 ruedas contra {s_:+.2f}% de la suma de votos: "
                       "no alcanza, el Jefe sigue con la suma de votos.")}


def probabilidad(modelo: dict | None, senales: dict[str, float], ctx: dict) -> float | None:
    if not modelo or not modelo.get("pesos_w"):
        return None
    w = modelo["pesos_w"]
    z = w[0] + sum(wi * xi for wi, xi in zip(w[1:], vector(senales, ctx)))
    return round(1 / (1 + math.exp(-z)), 3)
