"""21. Anticipador: ver la suba ANTES de que aparezca en el panel argentino.

Parte 1 (minutos u horas antes): el CEDEAR copia a su acción en EE.UU. por el CCL. Nueva York se mueve
antes que BYMA (pre-market desde las 5 y, hasta el 1/11, apertura 10:30 contra 11:00 de BYMA). Si la acción
en EE.UU. ya se movió y el CEDEAR todavía no, lo que le falta es casi seguro que llegue.
   esperado = variación en EE.UU. (con pre-market) × variación del CCL;  atraso = esperado − variación del CEDEAR.
Lo mismo con los ADRs de las acciones argentinas.

Parte 2 (días antes): un modelo entrenado con 5 años que busca los "precursores" que suelen aparecer antes
de una suba de 5% o más en la semana (volumen que crece sin mover el precio, precio que se comprime,
cercanía a máximos, contexto del mercado). Se mide cuántas veces acierta con datos que no vio.
"""
from __future__ import annotations

import math

import numpy as np

from ..nucleo.modelos import Senal


# ---------- Parte 1: CEDEARs atrasados contra Nueva York ----------
def atrasos(ctx, vivo: dict[str, dict], ccl_now: float | None, ccl_ayer: float | None, minuto: int,
            umbral: float = 2.0) -> list[dict]:
    if not ccl_now or not ccl_ayer:
        return []
    byma_abierto = minuto >= 11 * 60
    out = []
    for tk, v in vivo.items():
        t = ctx.titulo(tk)
        if not t or not v.get("precio") or not v.get("anterior"):
            continue
        us = (v["precio"] / v["anterior"] - 1) * 100
        esperado = ((v["precio"] / v["anterior"]) * (ccl_now / ccl_ayer) - 1) * 100
        mov = (t.get("variacion") or 0.0) if byma_abierto else 0.0
        atraso = round(esperado - mov, 2)
        if abs(atraso) >= umbral and abs(us) >= 1.5:
            out.append({"ticker": tk, "us": round(us, 2), "esperado": round(esperado, 2), "cedear": round(mov, 2),
                        "atraso": atraso, "antes_de_abrir": not byma_abierto, "precio_cedear": t.get("ultimo"),
                        "severidad": "alta" if abs(atraso) >= 4 else "media"})
    return sorted(out, key=lambda x: -abs(x["atraso"]))


def senales_atraso(lista: list[dict]) -> list[Senal]:
    out = []
    for a in lista:
        d = 1 if a["atraso"] > 0 else -1
        cuando = "Antes de que abra BYMA" if a["antes_de_abrir"] else "Ahora"
        out.append(Senal("anticipo", a["ticker"], d, round(min(0.8, 0.3 + abs(a["atraso"]) / 10), 2),
                         f"{cuando}: en Nueva York {a['ticker']} va {a['us']:+.1f}% (con el CCL, {a['esperado']:+.1f}%) y el CEDEAR "
                         f"{a['cedear']:+.1f}%: le falta {a['atraso']:+.1f}% para acomodarse.", a))
    return out


def evaluar_dia(registro: dict, cierres: dict[str, float]) -> dict:
    """Estadística propia: desde el precio de referencia (primer precio operable) hasta el cierre."""
    from ..nucleo.calibracion import _sumar
    out = {"al_cierre": {}}
    for tk, r in registro.items():
        ref, c = r.get("ref"), cierres.get(tk)
        if ref and c:
            _sumar(out["al_cierre"], (c / ref - 1) * 100 * (1 if r["atraso"] > 0 else -1), 0.5)
    return out


# ---------- Parte 2: modelo de precursores (días antes) ----------
NOMBRES = ["sube 1 día", "sube 5 días", "sube 20 días", "volumen 3d/20d", "compresión (rango 5d/20d)",
           "distancia al máximo de 20", "distancia a la media de 50", "RSI", "S&P 5 días", "miedo (VIX)", "Bitcoin 5 días"]
HORIZONTE, META = 5, 5.0


def _rsi(c: list[float], n: int = 14) -> float:
    if len(c) <= n:
        return 50.0
    d = np.diff(c[-n - 1:])
    s, b = d[d > 0].sum(), -d[d < 0].sum()
    return 100.0 if b == 0 else 100 - 100 / (1 + s / b)


def rasgos(f: list[dict], i: int, ctx_mkt: dict) -> list[float] | None:
    """f: velas OHLCV ordenadas [{fecha, c, h, l, v}]. Rasgos al cierre del día i (sin mirar el futuro)."""
    if i < 60:
        return None
    c = [x["c"] for x in f[: i + 1]]
    v = [x.get("v") or 0 for x in f[: i + 1]]
    rng = [(x["h"] - x["l"]) / x["c"] if x["c"] else 0 for x in f[: i + 1]]
    v20 = np.mean(v[-20:]) or 1
    r20 = np.mean(rng[-20:]) or 1e-9
    return [c[-1] / c[-2] - 1, c[-1] / c[-6] - 1, c[-1] / c[-21] - 1, math.log((np.mean(v[-3:]) + 1) / (v20 + 1)),
            np.mean(rng[-5:]) / r20, c[-1] / max(c[-20:]) - 1, c[-1] / np.mean(c[-50:]) - 1, _rsi(c) / 100,
            ctx_mkt.get("spy5", 0.0), ctx_mkt.get("vix", 20.0) / 30, ctx_mkt.get("btc5", 0.0)]


def contexto_mkt(fecha: str, spy: dict[str, float], vix: dict[str, float], btc: dict[str, float]) -> dict:
    def r5(s):
        fs = [x for x in s if x <= fecha][-6:] if s else []
        return (s[fs[-1]] / s[fs[0]] - 1) if len(fs) == 6 else 0.0
    fv = [x for x in vix if x <= fecha] if vix else []
    return {"spy5": r5(spy), "vix": vix[fv[-1]] if fv else 20.0, "btc5": r5(btc)}


def entrenar(series: dict[str, list[dict]], spy: dict, vix: dict, btc: dict, paso: int = 2) -> dict:
    """Aprende con el 70% inicial del tiempo y se prueba con el 30% final.
    Objetivo: ¿sube 5% o más (en algún cierre) en las 5 ruedas siguientes?"""
    filas = []
    ctx_cache: dict[str, dict] = {}
    spy_o, vix_o, btc_o = dict(sorted(spy.items())), dict(sorted(vix.items())), dict(sorted(btc.items()))
    for tk, f in series.items():
        for i in range(60, len(f) - HORIZONTE, paso):
            fe = f[i]["fecha"]
            if fe not in ctx_cache:
                ctx_cache[fe] = contexto_mkt(fe, spy_o, vix_o, btc_o)
            x = rasgos(f, i, ctx_cache[fe])
            if x is None:
                continue
            futuro = max(y["c"] for y in f[i + 1: i + 1 + HORIZONTE]) / f[i]["c"] - 1
            filas.append((fe, tk, x, 1.0 if futuro * 100 >= META else 0.0))
    if len(filas) < 2000:
        return {"activo": False, "motivo": f"Pocos casos ({len(filas)})."}
    filas.sort(key=lambda r: r[0])
    corte = int(len(filas) * 0.7)
    tr, te = filas[:corte], filas[corte:]
    X = np.array([r[2] for r in tr]); y = np.array([r[3] for r in tr])
    mu, sd = X.mean(0), X.std(0) + 1e-9
    Z = (X - mu) / sd
    Z2 = np.hstack([Z, Z ** 2])  # curvas simples (ej. RSI muy alto o muy bajo)
    w = np.zeros(Z2.shape[1] + 1)
    Xb = np.hstack([np.ones((len(Z2), 1)), Z2])
    for _ in range(500):
        p = 1 / (1 + np.exp(-Xb @ w))
        w -= 0.5 * (Xb.T @ (p - y) / len(y) + np.r_[0, w[1:]] / len(y))
    def prob(x):
        z = (np.array(x) - mu) / sd
        zz = np.r_[1.0, z, z ** 2]
        return float(1 / (1 + math.exp(-zz @ w)))
    pt = sorted(((prob(r[2]), r[3]) for r in te), reverse=True)
    base = sum(r[3] for r in te) / len(te)
    top5 = pt[: max(20, len(pt) // 20)]
    top10 = pt[: max(20, len(pt) // 10)]
    prec5, prec10 = sum(y for _, y in top5) / len(top5), sum(y for _, y in top10) / len(top10)
    umbral = top10[-1][0]
    activo = prec10 >= base * 1.5 and prec10 >= base + 0.05
    importancia = sorted(((NOMBRES[k], round(float(w[1 + k]), 3)) for k in range(len(NOMBRES))), key=lambda t: -abs(t[1]))[:5]
    return {"activo": activo, "mu": mu.tolist(), "sd": sd.tolist(), "w": w.tolist(), "umbral": round(umbral, 4),
            "prueba": {"casos": len(te), "base_pct": round(base * 100, 1), "top5_pct": round(prec5 * 100, 1),
                       "top10_pct": round(prec10 * 100, 1), "lift10": round(prec10 / base, 2) if base else None},
            "importancia": importancia,
            "motivo": (f"Con datos que no vio: de cada 100 papeles marcados (su 10% más probable), {prec10 * 100:.0f} subieron 5% o más "
                       f"en la semana, contra {base * 100:.0f} de cada 100 al azar ({prec10 / base:.1f} veces más)." if base else "")}


def puntuar(modelo: dict, series: dict[str, list[dict]], ctx_mkt: dict, tickers: list[str] | None = None) -> list[dict]:
    if not modelo or not modelo.get("w"):
        return []
    mu, sd, w = np.array(modelo["mu"]), np.array(modelo["sd"]), np.array(modelo["w"])
    out = []
    for tk, f in series.items():
        if tickers is not None and tk not in tickers or len(f) < 61:
            continue
        x = rasgos(f, len(f) - 1, ctx_mkt)
        if x is None:
            continue
        z = (np.array(x) - mu) / sd
        p = float(1 / (1 + math.exp(-(np.r_[1.0, z, z ** 2] @ w))))
        razones = []
        if x[3] > 0.4:
            razones.append(f"volumen de 3 días {math.exp(x[3]):.1f} veces su promedio")
        if x[4] < 0.7:
            razones.append("precio comprimido (rango chico: suele anteceder un movimiento grande)")
        if x[5] > -0.03:
            razones.append("pegado a su máximo de 20 ruedas")
        if x[1] > 0.05:
            razones.append(f"viene de subir {x[1] * 100:.0f}% en 5 días")
        if x[7] < 0.35:
            razones.append("sobrevendido (RSI bajo)")
        out.append({"ticker": tk, "prob": round(p, 3), "razones": razones, "fecha": f[-1]["fecha"]})
    return sorted(out, key=lambda r: -r["prob"])
