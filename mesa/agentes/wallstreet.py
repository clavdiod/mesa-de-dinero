"""17. Estratega de Wall Street (CEDEARs): lo que más evidencia juntó en décadas de mercado de EE.UU.

Mira el precio en dólares del papel en EE.UU. (no el CEDEAR en pesos, que mezcla el dólar CCL):
- Tendencia: arriba o abajo de su promedio de 200 ruedas (la regla más usada por los fondos de tendencia).
- Momentum 12-1: cuánto subió en los últimos 12 meses sin contar el último (el factor con más evidencia
  académica desde 1993: los ganadores del año tienden a seguir ganando unos meses).
- Clima de Wall Street: S&P 500 contra su promedio de 200, VIX (el índice del miedo) y la tasa a 10 años.
- Rotación: qué sectores (fondos XLK, XLF, XLE...) le ganan al S&P en los últimos 3 meses.

Opina en los CEDEARs y "enseña": a las señales de los demás sobre CEDEARs se les cree más o menos según el
clima de Wall Street, pero solo si la historia muestra que eso mejora los resultados.
"""
from __future__ import annotations

import statistics as st

from ..nucleo.modelos import Senal

SECTORES = {"XLK": "tecnología", "XLF": "financieras", "XLE": "energía", "XLV": "salud", "XLY": "consumo discrecional",
            "XLP": "consumo básico", "XLI": "industria", "XLU": "servicios públicos", "XLB": "materiales", "XLC": "comunicaciones"}
INDICES = ["SPY", "^VIX", "^TNX", *SECTORES]


def _hasta(serie: list[list], fecha: str) -> list[float]:
    """Cierres hasta una fecha (incluida). serie = [[fecha, cierre], ...] ordenada."""
    return [c for f, c in serie if f <= fecha]


def _ma(x: list[float], n: int) -> float | None:
    return sum(x[-n:]) / n if len(x) >= n else None


def clima(series: dict[str, list[list]], fecha: str) -> dict:
    """Clima de Wall Street a una fecha: tendencia del S&P, miedo (VIX), tasa a 10 años y sectores líderes."""
    spy, vix, tnx = _hasta(series.get("SPY", []), fecha), _hasta(series.get("^VIX", []), fecha), _hasta(series.get("^TNX", []), fecha)
    out = {"fecha": fecha, "riesgo": 0.0, "clase": [], "ensena": [], "lideres": [], "rezagados": []}
    if len(spy) < 210:
        return out
    ma200, r20 = _ma(spy, 200), (spy[-1] / spy[-21] - 1) * 100
    arriba = spy[-1] > ma200
    out["riesgo"] += 0.5 if arriba else -0.5
    out["clase"].append(f"S&P 500 {'por encima' if arriba else 'por debajo'} de su promedio de 200 ruedas ({(spy[-1] / ma200 - 1) * 100:+.1f}%), "
                        f"{r20:+.1f}% en el último mes: Wall Street está en {'tendencia alcista' if arriba else 'tendencia bajista'}.")
    if vix:
        v = vix[-1]
        if v >= 30:
            out["riesgo"] -= 0.3
            out["clase"].append(f"VIX en {v:.0f}: hay miedo. Históricamente, los picos de miedo fueron buenos momentos para comprar índice con paciencia, "
                                "pero en el corto plazo los papeles se mueven mucho: tamaños chicos.")
            out["ensena"].append("Con miedo alto (VIX ≥ 30), preferir fondos de índice (SPY, QQQ) a papeles sueltos y achicar tamaños.")
        elif v <= 16:
            out["riesgo"] += 0.2
            out["clase"].append(f"VIX en {v:.0f}: calma. El mercado no espera sobresaltos (ojo: la calma extrema también es cuando menos se cubre la gente).")
        else:
            out["clase"].append(f"VIX en {v:.0f}: nivel normal.")
    if len(tnx) > 21:
        d = tnx[-1] - tnx[-21]
        if d >= 0.25:
            out["riesgo"] -= 0.2
            out["clase"].append(f"La tasa a 10 años de EE.UU. subió a {tnx[-1]:.2f}% ({d:+.2f} en un mes): golpea a las tecnológicas y a las de crecimiento.")
            out["ensena"].append("Con la tasa de EE.UU. subiendo rápido, desconfiar de compras en tecnológicas caras.")
        elif d <= -0.25:
            out["clase"].append(f"La tasa a 10 años bajó a {tnx[-1]:.2f}% ({d:+.2f} en un mes): alivio para tecnológicas y crecimiento.")
    rel = []
    for etf, nombre in SECTORES.items():
        x = _hasta(series.get(etf, []), fecha)
        if len(x) > 64:
            rel.append((((x[-1] / x[-64] - 1) - (spy[-1] / spy[-64] - 1)) * 100, etf, nombre))
    rel.sort(reverse=True)
    if len(rel) >= 4:
        out["lideres"], out["rezagados"] = [e for _, e, _ in rel[:3]], [e for _, e, _ in rel[-3:]]
        out["clase"].append("Sectores que le ganan al S&P en 3 meses: " + ", ".join(f"{n} ({r:+.1f}%)" for r, _, n in rel[:3])
                            + ". Los que pierden: " + ", ".join(f"{n} ({r:+.1f}%)" for r, _, n in rel[-3:]) + ".")
    out["riesgo"] = round(max(-1.0, min(1.0, out["riesgo"])), 2)
    if out["riesgo"] >= 0.5:
        out["ensena"].insert(0, "Wall Street en modo comprador: las compras de CEDEARs en tendencia valen más.")
    elif out["riesgo"] <= -0.4:
        out["ensena"].insert(0, "Wall Street en modo defensivo: desconfiar de compras de CEDEARs y preferir efectivo o fondos defensivos (XLP, XLV, XLU).")
    out["titulo"] = ("Clima comprador en Wall Street" if out["riesgo"] >= 0.5 else "Clima defensivo en Wall Street" if out["riesgo"] <= -0.4
                     else "Clima mixto en Wall Street")
    return out


def factores(serie: list[list], fecha: str) -> dict | None:
    x = _hasta(serie, fecha)
    if len(x) < 260:
        return None
    ma200 = _ma(x, 200)
    return {"precio": x[-1], "ma200": ma200, "tendencia": x[-1] > ma200, "mom_12_1": (x[-22] / x[-253] - 1) * 100,
            "dist_ma": (x[-1] / ma200 - 1) * 100}


def senales_en(precios: dict[str, list[list]], cl: dict, fecha: str, tickers: list[str] | None = None,
               balances: set[str] | None = None) -> list[Senal]:
    """Opinión sobre cada CEDEAR: tendencia + momentum 12-1 contra el resto del universo + clima."""
    fac = {tk: f for tk, s in precios.items() if (f := factores(s, fecha))}
    if len(fac) < 10:
        return []
    moms = sorted(f["mom_12_1"] for f in fac.values())
    p70, p30 = moms[int(len(moms) * 0.7)], moms[int(len(moms) * 0.3)]
    out = []
    for tk in (tickers if tickers is not None else list(fac)):
        f = fac.get(tk)
        if not f:
            continue
        sector_txt = " Su sector lidera en Wall Street." if tk in cl.get("lideres", []) else ""
        if f["tendencia"] and f["mom_12_1"] >= p70 and cl.get("riesgo", 0) > -0.4:
            fz = 0.45 + (0.15 if cl.get("riesgo", 0) >= 0.5 else 0) + (0.1 if sector_txt else 0)
            txt = (f"En EE.UU. está {f['dist_ma']:+.1f}% sobre su promedio de 200 ruedas y subió {f['mom_12_1']:+.0f}% en 12 meses "
                   f"(sin el último): entre los más fuertes de los CEDEARs. Tendencia + momentum: lo que más funcionó en Wall Street.{sector_txt}")
            if balances and tk in balances:
                fz -= 0.2
                txt += " Ojo: presenta balance en pocos días."
            out.append(Senal("wallstreet", tk, +1, round(fz, 2), txt, {**f, "riesgo_eeuu": cl.get("riesgo")}))
        elif not f["tendencia"] and f["mom_12_1"] <= p30:
            out.append(Senal("wallstreet", tk, -1, 0.5 if cl.get("riesgo", 0) < 0.5 else 0.4,
                             f"En EE.UU. está {f['dist_ma']:+.1f}% bajo su promedio de 200 ruedas y {f['mom_12_1']:+.0f}% en 12 meses: "
                             "tendencia bajista y de los más débiles. En Wall Street no se compran cuchillos que caen.", {**f, "riesgo_eeuu": cl.get("riesgo")}))
    return out


def multiplicador(cl: dict | None, grupo: str | None, direccion: int) -> float:
    """Ajuste sobre las señales de otros agentes en CEDEARs (×0,8 a ×1,2), solo si la historia lo valida."""
    modo = cl.get("ensenanza_activa") if cl else None
    if not modo or grupo != "cedears" or not direccion:
        return 1.0
    signo = 1 if modo == "a_favor" else -1  # 'contrario': con miedo (riesgo < 0) se les cree más a las compras
    return round(1 + 0.2 * cl.get("riesgo", 0) * direccion * signo, 3)


def entrenar(datos: dict, horizonte: int = 60, paso: int = 5, horizonte_clima: int = 10) -> dict:
    """Rebobina 5 años: en cada fecha opina como si fuera ese día y mide qué pasó `horizonte` ruedas después (en dólares).
    Tendencia y momentum son estrategias de meses: se miden a 60 ruedas (~3 meses), el plazo "mediano" de la mesa.
    También prueba si el clima de Wall Street sirve para "enseñar": ¿rinden más las compras de CEDEARs cuando
    el clima es comprador que cuando es defensivo?"""
    from ..nucleo.calibracion import _sumar, banda
    idx, precios = datos.get("indices") or {}, datos.get("precios") or {}
    fechas = [f for f, _ in idx.get("SPY", [])]
    pos = {tk: {f: i for i, (f, _) in enumerate(s)} for tk, s in precios.items()}
    stats = {"total": {}, "bandas": {}, "por_horizonte": {"10": {}, "20": {}, "60": {}}}
    ens = {"clima_comprador": {}, "clima_mixto": {}, "clima_defensivo": {}}
    for f in fechas[260:-max(horizonte, horizonte_clima):paso]:
        cl = clima(idx, f)
        for s in senales_en(precios, cl, f):
            i = pos[s.ticker].get(f)
            if i is None or i + horizonte >= len(precios[s.ticker]):
                continue
            ret = (precios[s.ticker][i + horizonte][1] / precios[s.ticker][i][1] - 1) * 100 * s.direccion
            _sumar(stats["total"], ret, s.fuerza)
            _sumar(stats["bandas"].setdefault(banda(s.fuerza), {}), ret, s.fuerza)
            for h in (10, 20, 60):
                if i + h < len(precios[s.ticker]):
                    _sumar(stats["por_horizonte"][str(h)], (precios[s.ticker][i + h][1] / precios[s.ticker][i][1] - 1) * 100 * s.direccion, s.fuerza)
        # el "enseñar": rendimiento de comprar cualquier CEDEAR según el clima del día
        lado = "clima_comprador" if cl["riesgo"] >= 0.5 else "clima_defensivo" if cl["riesgo"] <= -0.4 else "clima_mixto"
        for tk, s in precios.items():
            i = pos[tk].get(f)
            if i is not None and i + horizonte_clima < len(s) and i >= 1:
                _sumar(ens[lado], (s[i + horizonte_clima][1] / s[i][1] - 1) * 100, 0.6)
    return {"wallstreet": stats, "ensenanza": ens}


def ensenanza_activa(ens: dict) -> tuple[str | None, str]:
    """Qué enseñar según la evidencia: 'a_favor' (comprar con clima comprador), 'contrario' (comprar el miedo) o None."""
    a, c = ens.get("clima_comprador") or {}, ens.get("clima_defensivo") or {}
    if a.get("casos", 0) < 200 or c.get("casos", 0) < 200:
        return None, "Todavía no hay suficientes casos de clima comprador y defensivo para probar si su lectura mejora a los demás."
    pa, pc = a["suma_ret"] / a["casos"], c["suma_ret"] / c["casos"]
    if pa - pc >= 0.5:
        return "a_favor", (f"En 5 años, comprar CEDEARs con clima comprador rindió {pa:+.1f}% a 10 ruedas contra {pc:+.1f}% con clima defensivo: "
                           "a las compras de CEDEARs del resto se les cree más cuando Wall Street está comprador.")
    if pc - pa >= 0.5:
        return "contrario", (f"En 5 años, comprar CEDEARs con clima DEFENSIVO (miedo) rindió {pc:+.1f}% a 10 ruedas contra {pa:+.1f}% con clima comprador: "
                             "\"ser codicioso cuando los demás tienen miedo\". A las compras de CEDEARs del resto se les cree más cuando hay miedo "
                             "y un poco menos cuando todo es euforia.")
    return None, (f"En 5 años, el clima de Wall Street no separó bien ({pa:+.1f}% comprador contra {pc:+.1f}% defensivo, a 10 ruedas): "
                  "su ajuste sobre los demás está en pausa.")
