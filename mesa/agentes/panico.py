"""20. Comprador de pánico: compra cuando los demás venden por miedo, no por una mala noticia de la empresa.

Nace de lo que ya mostraron nuestros datos: comprar CEDEARs con miedo en Wall Street rindió más que con calma,
e ir en contra del contexto macro argentino rindió más que ir a favor.

Cuatro situaciones (plazo: ~1 mes):
- Pánico en Wall Street: VIX ≥ 30 o el S&P 500 cae 10% desde su máximo de 3 meses → índices (SPY, QQQ).
- Capitulación de un CEDEAR bueno: cae 15% o más en 10 ruedas, pero un mes antes estaba en tendencia
  alcista (sobre su promedio de 200) → caída exagerada de un papel sano.
- Susto argentino: el riesgo país salta 80 puntos o 12% en 10 ruedas → líderes del Merval, pero recién cuando dejan de caer
  (arriba de su promedio de 20 ruedas y con ese promedio que dejó de bajar). Ver 30/10 en aprendizajes.
- Capitulación local: una acción argentina cae 15% o más en 10 ruedas, mucho más que el resto.
Riesgo y Hechos del emisor siguen pudiendo frenarlo si la caída tiene una causa grave (un veto).
"""
from __future__ import annotations

import statistics as st

from ..nucleo.modelos import Senal

INDICES_CEDEAR = ["SPY", "QQQ", "DIA", "IWM"]
LIDERES_MERVAL = ["GGAL", "YPFD", "PAMP", "BMA", "CEPU", "TGSU2", "TXAR", "ALUA"]


def _h(serie: list[list], fecha: str) -> list[float]:
    return [c for f, c in serie if f <= fecha]


def senales_cedears(precios: dict[str, list[list]], indices: dict[str, list[list]], fecha: str,
                    tickers: list[str] | None = None) -> list[Senal]:
    out = []
    spy, vix = _h(indices.get("SPY", []), fecha), _h(indices.get("^VIX", []), fecha)
    caida_spy = (spy[-1] / max(spy[-63:]) - 1) * 100 if len(spy) >= 63 else 0
    v = vix[-1] if vix else 0
    if v >= 30 or caida_spy <= -10:
        for tk in INDICES_CEDEAR:
            if tk in precios and (tickers is None or tk in tickers):
                out.append(Senal("panico", tk, +1, 0.6, f"Pánico en Wall Street (VIX {v:.0f}, S&P {caida_spy:+.1f}% desde su máximo de 3 meses): "
                                                        "históricamente, comprar índice con miedo rindió más que con calma. Tamaño prudente y escalonado.",
                                 {"tipo": "indice", "vix": v, "caida_spy": caida_spy}))
    for tk, s in precios.items():
        if tickers is not None and tk not in tickers or tk in INDICES_CEDEAR:
            continue
        x = _h(s, fecha)
        if len(x) < 230:
            continue
        r10 = (x[-1] / x[-11] - 1) * 100
        ma200_antes = sum(x[-221:-21]) / 200
        if r10 <= -15 and x[-21] > ma200_antes:
            out.append(Senal("panico", tk, +1, 0.5, f"Cayó {r10:.0f}% en 10 ruedas, pero hace un mes estaba en tendencia alcista: "
                                                    "caída exagerada de un papel sano (si no hay una mala noticia grave detrás).",
                             {"tipo": "capitulacion_cedear", "r10": r10}))
    return out


def senales_locales(velas: dict[str, list[dict]], riesgo_pais: dict[str, float], fecha: str,
                    precios_hoy: dict[str, float] | None = None, tickers: list[str] | None = None) -> list[Senal]:
    out = []
    fs = sorted(f for f in riesgo_pais if f <= fecha)
    salto = riesgo_pais[fs[-1]] - riesgo_pais[fs[-11]] if len(fs) >= 11 else 0
    # 30/10: el susto sigue "abierto" 40 ruedas (riesgo país +12% o +80 puntos en 10 ruedas). Pero NO se compra mientras el
    # papel cae: se espera que cierre arriba de su promedio de 20 ruedas y que ese promedio deje de bajar.
    # Probado en 10 años (35 sustos, líderes en dólares, 20 ruedas, stop -10%): comprar en el susto +1,6% (2016-21: -1,1%;
    # 2022-26: +4,4%); esperar así +4,3% (2016-21: +1,6%; 2022-26: +6,7%). Le gana en los dos períodos.
    susto, cuando = 0.0, None
    for k in range(max(10, len(fs) - 40), len(fs)):
        d = riesgo_pais[fs[k]] - riesgo_pais[fs[k - 10]]
        if (d >= 80 or riesgo_pais[fs[k]] / riesgo_pais[fs[k - 10]] - 1 >= 0.12) and d > susto:
            susto, cuando = d, fs[k]
    r10s, series = {}, {}
    for tk, vs in velas.items():
        x = [v["cierre"] for v in vs if v["fecha"] <= fecha]
        if precios_hoy and tk in precios_hoy and (not vs or vs[-1]["fecha"] < fecha):
            x = x + [precios_hoy[tk]]
        if len(x) >= 11:
            r10s[tk] = (x[-1] / x[-11] - 1) * 100
            series[tk] = x
    if cuando:
        for tk in LIDERES_MERVAL:
            x = series.get(tk)
            if not x or len(x) < 25 or (tickers is not None and tk not in tickers):
                continue
            m20, m20_antes = st.mean(x[-20:]), st.mean(x[-25:-5])
            if x[-1] > m20 and m20 >= m20_antes:
                out.append(Senal("panico", tk, +1, 0.5, f"Susto argentino (el riesgo país saltó {susto:.0f} puntos en 10 ruedas, el {cuando[8:10]}/{cuando[5:7]}) "
                                                        "y el papel ya dejó de caer: cerró arriba de su promedio de 20 ruedas y ese promedio dejó de bajar. "
                                                        "Comprar después de la confirmación rindió más que comprar en plena caída.",
                                 {"tipo": "susto_argentino", "salto_rp": susto, "confirmado": True}))
    if len(r10s) >= 8:
        med = st.median(r10s.values())
        for tk, r in r10s.items():
            if (tickers is None or tk in tickers) and r <= -15 and r - med <= -10 and not any(s.ticker == tk for s in out):
                out.append(Senal("panico", tk, +1, 0.4, f"Cayó {r:.0f}% en 10 ruedas contra {med:+.0f}% del resto: castigo exagerado "
                                                        "(si no hay una mala noticia grave de la empresa).", {"tipo": "capitulacion_local", "r10": r}))
    return out


def entrenar(precios_usd: dict[str, list[list]], indices: dict[str, list[list]], locales: dict[str, list[dict]],
             riesgo_pais: dict[str, float], horizonte: int = 20, paso: int = 2, registro: list | None = None) -> dict:
    """Prueba con la historia: CEDEARs en dólares (5 años) y acciones locales (el historial que haya)."""
    from ..nucleo.calibracion import _sumar, banda
    stats = {"total": {}, "bandas": {}, "por_horizonte": {"10": {}, "20": {}}, "por_tipo": {}}

    def anotar(s, serie, i, f=None):
        if registro is not None and f:
            registro.append((s.ticker, f, "panico", s.direccion * s.fuerza))
        for h in (10, 20):
            if i + h < len(serie):
                _sumar(stats["por_horizonte"][str(h)], (serie[i + h] / serie[i] - 1) * 100, s.fuerza)
        if i + horizonte < len(serie):
            r = (serie[i + horizonte] / serie[i] - 1) * 100
            _sumar(stats["total"], r, s.fuerza)
            _sumar(stats["bandas"].setdefault(banda(s.fuerza), {}), r, s.fuerza)
            _sumar(stats["por_tipo"].setdefault(s.datos.get("tipo", "otro"), {}), r, s.fuerza)

    fechas = [f for f, _ in indices.get("SPY", [])]
    pos = {tk: {f: i for i, (f, _) in enumerate(s)} for tk, s in precios_usd.items()}
    vistos = set()
    for f in fechas[230:-horizonte:paso]:
        for s in senales_cedears(precios_usd, indices, f):
            clave = (s.ticker, s.datos["tipo"], f[:7])  # una por papel, tipo y mes (no contar 10 veces el mismo pánico)
            i = pos[s.ticker].get(f)
            if i is None or clave in vistos:
                continue
            vistos.add(clave)
            anotar(s, [c for _, c in precios_usd[s.ticker]], i, f)
    fl = sorted({v["fecha"] for vs in locales.values() for v in vs})
    posl = {tk: {v["fecha"]: i for i, v in enumerate(vs)} for tk, vs in locales.items()}
    for f in fl[20:-horizonte:paso]:
        for s in senales_locales(locales, riesgo_pais, f):
            clave = (s.ticker, s.datos["tipo"], f[:7])
            i = posl[s.ticker].get(f)
            if i is None or clave in vistos:
                continue
            vistos.add(clave)
            anotar(s, [v["cierre"] for v in locales[s.ticker]], i, f)
    return stats
