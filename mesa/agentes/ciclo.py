"""Termómetro del ciclo (20/11, del libro de Howard Marks que pasó Clau). Mide en qué parte del péndulo estamos:
- Argentina: riesgo país contra sus últimos 3 años. PROBADO (ARGT 2011-2026): con miedo (30% más alto) las acciones
  argentinas en dólares rindieron a 12 meses +21,4% típico (suben 73 de cada 100) contra +9,9% en calma. → Con miedo,
  la línea de posiciones se anima más (2 por día); en calma, más prudente (1 por día).
- EE.UU.: VIX contra su último año y S&P contra su máximo. NO se cumplió como dice el libro (SPY 2001-2026): la calma con
  el S&P en máximos fue lo más seguro (sube 90 de cada 100 a 12 meses) y con miedo hubo caídas más fuertes. Se muestra
  como dato, sin cambiar nada.
Se calcula una vez por día en el cierre (gratis: argentinadatos y Yahoo)."""
from __future__ import annotations

import numpy as np

CLAVE = "ciclo/termometro"


def medir(hoy) -> dict:
    from ..datos import gratis
    out = {"fecha": hoy.isoformat()}
    try:
        rp = gratis.series_macro(4).get("riesgo_pais") or {}
        fs = sorted(rp)[-757:]
        w = np.array([rp[f] for f in fs])
        pct = float(np.mean(w < w[-1]))
        out["argentina"] = {"riesgo_pais": round(w[-1]), "percentil": round(pct * 100),
                            "postura": "agresiva" if pct >= 0.7 else "prudente" if pct <= 0.3 else "neutral",
                            "texto": (f"Riesgo país {w[-1]:.0f}: más alto que el {pct * 100:.0f}% de los últimos 3 años. "
                                      + ("Hay miedo con Argentina: según Marks (y la historia de 2011 a hoy) es cuando más rindieron las acciones argentinas a un año."
                                         if pct >= 0.7 else "Hay calma con Argentina: las acciones rindieron menos después de momentos así; más prudencia."
                                         if pct <= 0.3 else "Ni miedo ni calma con Argentina."))}
    except Exception as ex:
        print(f"[ciclo] argentina: {ex}")
    try:
        vix = {x["fecha"]: x["c"] for x in gratis.yahoo_ohlcv("^VIX", "2y")}
        spy = {x["fecha"]: x["c"] for x in gratis.yahoo_ohlcv("SPY", "2y")}
        fs = sorted(set(vix) & set(spy))[-252:]
        v = np.array([vix[f] for f in fs]); s = np.array([spy[f] for f in fs])
        pv = float(np.mean(v < v[-1])); dmx = s[-1] / s.max() - 1
        est = "miedo" if pv >= 0.8 else "euforia" if pv <= 0.2 and dmx >= -0.02 else "normal"
        out["eeuu"] = {"vix": round(float(v[-1]), 1), "percentil": round(pv * 100), "sp_vs_max_pct": round(float(dmx) * 100, 1), "estado": est,
                       "texto": f"VIX {v[-1]:.1f} (más alto que el {pv * 100:.0f}% del año), S&P {dmx * 100:+.1f}% de su máximo: {est}. ".replace(".", ",", 2)
                                + ("Con miedo en EE.UU. la historia muestra caídas más fuertes antes de recuperar: dato, no cambia nada."
                                   if est == "miedo" else "")}
    except Exception as ex:
        print(f"[ciclo] eeuu: {ex}")
    return out


def forward_politico(almacen, hoy) -> dict | None:
    """20/11 (Nacho, IEB): tasa forward entre el AO27 y el AO28 valuados a dólar cable. El AO27 vence justo después de la
    elección de octubre de 2027 y el AO28 un año más tarde: la tasa implícita para ese año mide cuánto riesgo político
    percibe el mercado para después de la elección, mejor que el riesgo país. Se guarda la serie diaria para ver su historia."""
    from datetime import date as _d
    from ..datos.eventos import flujos_bonos
    pan = (almacen.get("ui/panel") or {}).get("titulos") or {}
    fl = flujos_bonos(almacen)

    def tir(tk, px):
        fs = [(_d.fromisoformat(str(f["fecha"])[:10]), float(f.get("interes") or 0) + float(f.get("amortizacion") or 0))
              for f in ((fl.get(tk) or {}).get("flujos") or []) if str(f["fecha"])[:10] > hoy.isoformat()]
        if not fs or not px:
            return None, None
        lo, hi = -0.5, 3.0
        for _ in range(200):
            m = (lo + hi) / 2
            v = sum(c / (1 + m) ** ((d - hoy).days / 365) for d, c in fs)
            lo, hi = (m, hi) if v > px else (lo, m)
        return m, (fs[-1][0] - hoy).days / 365
    p27, p28 = (pan.get("AO27C") or [None])[0], (pan.get("AO28C") or [None])[0]
    (y1, t1), (y2, t2) = tir("AO27", p27), tir("AO28", p28)
    if y1 is None or y2 is None or not t2 or t2 <= t1:
        return None
    fw = ((1 + y2) ** t2 / (1 + y1) ** t1) ** (1 / (t2 - t1)) - 1
    hist = almacen.get("ciclo/forward_hist") or {}
    hist[hoy.isoformat()] = round(fw * 100, 1)
    hist = dict(sorted(hist.items())[-800:])
    almacen.put("ciclo/forward_hist", hist)
    vals = list(hist.values())
    pct = round(sum(1 for v in vals if v < fw * 100) / len(vals) * 100) if len(vals) >= 60 else None
    return {"ao27_tir": round(y1 * 100, 1), "ao28_tir": round(y2 * 100, 1), "forward": round(fw * 100, 1), "percentil": pct,
            "texto": f"Riesgo político (tasa forward AO27-AO28 a cable): {str(round(fw * 100, 1)).replace('.', ',')}% "
                     f"(AO27 {str(round(y1 * 100, 1)).replace('.', ',')}%, AO28 {str(round(y2 * 100, 1)).replace('.', ',')}%). "
                     "Es lo que el mercado le cobra a Argentina por el año después de la elección de 2027"
                     + (f"; más alto que el {pct}% de los días registrados." if pct is not None else
                        "; en abril-julio de 2026 estaba entre 10% y 16% (IEB). La mesa empieza a guardar la serie para medirla.")}


def max_posiciones_dia(almacen, default: int = 2) -> int:
    t = (almacen.get(CLAVE) or {}).get("argentina") or {}
    return {"agresiva": 2, "neutral": 2, "prudente": 1}.get(t.get("postura"), default)
