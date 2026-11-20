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


def max_posiciones_dia(almacen, default: int = 2) -> int:
    t = (almacen.get(CLAVE) or {}).get("argentina") or {}
    return {"agresiva": 2, "neutral": 2, "prudente": 1}.get(t.get("postura"), default)
