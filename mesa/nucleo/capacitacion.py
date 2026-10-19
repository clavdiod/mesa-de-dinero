"""Capacitación mensual de los agentes por reglas (Técnico e Historiador).

Prueba combinaciones de parámetros en el 70% más viejo de la historia y valida en el 30% más nuevo,
datos que no se usaron para elegir. Solo propone un cambio si mejora fuera de muestra; el cambio queda
pendiente hasta que lo apruebes en la web (antes y después a la vista).
"""
from __future__ import annotations

import itertools
import statistics as st

from . import calc


def _senales_tecnico(velas: list[dict], prm: dict, h: int = 10) -> list[float]:
    rets = []
    w = prm["ventana_quiebre"]
    for i in range(max(60, w + 1), len(velas) - h):
        hist = velas[:i]
        ult = velas[i]["cierre"]
        cierres = [v["cierre"] for v in hist] + [ult]
        r, m20, m50 = calc.rsi(cierres), calc.sma(cierres, 20), calc.sma(cierres, 50)
        mx = max(v["maximo"] for v in hist[-w:])
        mn = min(v["minimo"] for v in hist[-w:])
        d = 0
        if ult > mx and m20 and m50 and m20 > m50:
            d = 1
        elif ult < mn:
            d = -1
        elif r is not None and r <= prm["rsi_bajo"]:
            d = 1
        elif r is not None and r >= prm["rsi_alto"]:
            d = -1
        if d:
            rets.append((velas[i + h]["cierre"] / ult - 1) * 100 * d)
    return rets


def _puntaje(series: list[list[dict]], prm: dict, desde: float, hasta: float) -> tuple[float, int]:
    todos = []
    for velas in series:
        n = len(velas)
        tramo = velas[int(n * desde):int(n * hasta)]
        if len(tramo) > 80:
            todos += _senales_tecnico(tramo, prm)
    return (st.mean(todos) if todos else 0.0, len(todos))


def entrenar_tecnico(series: list[list[dict]], actuales: dict) -> dict | None:
    grilla = {"rsi_bajo": [28, 30, 32, 35], "rsi_alto": [68, 72, 76], "ventana_quiebre": [15, 20, 30]}
    actuales = {"rsi_bajo": 32, "rsi_alto": 72, "ventana_quiebre": 20, **actuales}
    mejor, mejor_train = None, -1e9
    for combo in itertools.product(*grilla.values()):
        prm = dict(zip(grilla.keys(), combo))
        p, n = _puntaje(series, prm, 0.0, 0.7)
        if n >= 30 and p > mejor_train:
            mejor, mejor_train = prm, p
    if not mejor or mejor == actuales:
        return None
    test_nuevo, n_nuevo = _puntaje(series, mejor, 0.7, 1.0)
    test_actual, n_actual = _puntaje(series, actuales, 0.7, 1.0)
    if n_nuevo >= 20 and test_nuevo > test_actual + 0.1:
        return {"agente": "tecnico", "antes": actuales, "despues": mejor,
                "fuera_de_muestra": {"antes_pct": round(test_actual, 3), "despues_pct": round(test_nuevo, 3),
                                     "casos_antes": n_actual, "casos_despues": n_nuevo}}
    return None


def entrenar_historiador(series: list[list[dict]], actuales: dict) -> dict | None:
    actuales = {"correlacion_min": 0.85, "ventana": 20, **actuales}

    def puntaje(prm, desde, hasta):
        rets = []
        for velas in series:
            c = [v["cierre"] for v in velas]
            n = len(c)
            tramo = c[int(n * desde):int(n * hasta)]
            for fin in range(160, len(tramo) - 10, 5):
                r = calc.patrones_parecidos(tramo[:fin], prm["ventana"], prm["correlacion_min"], (10,))
                h = r["horizontes"].get(10)
                if not h or r["casos"] < 8:
                    continue
                d = 1 if h["promedio_pct"] > 0 else -1
                rets.append((tramo[fin - 1 + 10] / tramo[fin - 1] - 1) * 100 * d)
        return (st.mean(rets) if rets else 0.0, len(rets))

    mejor, mejor_p = None, -1e9
    for corr, ven in itertools.product([0.80, 0.85, 0.90], [15, 20, 30]):
        prm = {"correlacion_min": corr, "ventana": ven}
        p, n = puntaje(prm, 0.0, 0.7)
        if n >= 20 and p > mejor_p:
            mejor, mejor_p = prm, p
    if not mejor or mejor == actuales:
        return None
    tn, nn = puntaje(mejor, 0.7, 1.0)
    ta, na = puntaje(actuales, 0.7, 1.0)
    if nn >= 15 and tn > ta + 0.1:
        return {"agente": "historiador", "antes": actuales, "despues": mejor,
                "fuera_de_muestra": {"antes_pct": round(ta, 3), "despues_pct": round(tn, 3),
                                     "casos_antes": na, "casos_despues": nn}}
    return None
