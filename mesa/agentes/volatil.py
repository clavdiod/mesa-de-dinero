"""32. Capacitación para tiempos volátiles.

¿Qué es un día volátil? Uno en que el índice de referencia se viene moviendo mucho más que lo normal:
- Acciones argentinas: el Merval en dólares, con una volatilidad de 20 ruedas en el 25% más alto de su historia,
  o el riesgo país que saltó 10% o más en 5 ruedas.
- CEDEARs: el VIX en 25 o más, o el S&P 500 con su volatilidad de 20 ruedas en el 25% más alto.

Para cada anticipador:
1. Se mide cómo le fue al modelo de siempre SOLO en los días volátiles del examen (datos que no vio).
2. Se entrena un ESPECIALISTA que aprende solo de días volátiles, y se examina en los mismos días.
3. Si el especialista gana (acierta igual o más y rinde al menos 0,3% más a 5 ruedas), en días volátiles se usa
   el especialista; si no, el de siempre. Si a ninguno le va bien en días volátiles, ese anticipador baja su voto.
"""
from __future__ import annotations

import bisect
import math
import statistics as st

PCT = 0.75


def _vol20(serie: dict) -> dict:
    fs = sorted(serie)
    out = {}
    r = []
    for a, b in zip(fs, fs[1:]):
        if serie[a] and serie[b]:
            x = math.log(serie[b] / serie[a])
            r.append(x if abs(x) < 0.3 else 0.0)
        else:
            r.append(0.0)
        if len(r) >= 20:
            out[b] = st.pstdev(r[-20:]) * math.sqrt(252)
    return out


def _salto(serie: dict, n: int = 5) -> dict:
    fs = sorted(serie)
    return {fs[i]: serie[fs[i]] / serie[fs[i - n]] - 1 for i in range(n, len(fs)) if serie[fs[i - n]]}


def umbral(serie: dict) -> float | None:
    v = sorted(_vol20(serie).values())
    return v[int(len(v) * PCT)] if len(v) > 100 else None


def dias_arg(merval_usd: dict, riesgo_pais: dict) -> tuple[set, float | None]:
    u = umbral(merval_usd)
    v = _vol20(merval_usd)
    s = _salto(riesgo_pais) if riesgo_pais else {}
    dias = {f for f, x in v.items() if u and x >= u} | {f for f, x in s.items() if x >= 0.10}
    return dias, u


def dias_mundo(spy: dict, vix: dict) -> tuple[set, float | None]:
    u = umbral(spy)
    v = _vol20(spy)
    return {f for f, x in v.items() if u and x >= u} | {f for f, x in vix.items() if x >= 25}, u


def hoy_volatil(tipo: str, indice: dict, extra: dict, u: float | None) -> tuple[bool, str]:
    """¿Hoy es día volátil? tipo 'arg' (indice=Merval USD, extra=riesgo país) o 'mundo' (indice=SPY, extra=VIX)."""
    v = _vol20(indice)
    ult = v[max(v)] if v else None
    por = []
    if u and ult and ult >= u:
        por.append(f"{'Merval' if tipo == 'arg' else 'S&P 500'} moviéndose {ult * 100:.0f}% anual (lo normal es menos de {u * 100:.0f}%)")
    if tipo == "arg" and extra:
        s = _salto(extra)
        if s and s[max(s)] >= 0.10:
            por.append(f"riesgo país +{s[max(s)] * 100:.0f}% en 5 ruedas")
    if tipo == "mundo" and extra:
        ux = extra[max(extra)]
        if ux >= 25:
            por.append(f"VIX en {ux:.0f}")
    return bool(por), "; ".join(por)


def capacitar(entrenar_fn, dias: set, u: float | None, nombre: str) -> dict:
    """entrenar_fn(**kw) entrena el anticipador. Devuelve el bloque 'volatil' para guardar dentro del modelo."""
    gen = entrenar_fn(regimen=dias)
    pv = gen.get("prueba_regimen")
    esp = entrenar_fn(solo_fechas=dias)
    pe = esp.get("prueba") if esp.get("w") else None
    usar = bool(pv and pe and pe["top10_pct"] >= pv["top10_pct"] and pe["ret5_top10"] >= pv["ret5_top10"] + 0.3)
    mejor = pe if usar else pv
    bueno = bool(mejor and mejor["top10_pct"] >= mejor["base_pct"] * 1.3 and mejor["ret5_top10"] - mejor["ret5_base"] >= 0.5)
    out = {"dias": len(dias), "umbral_vol": u, "general": pv, "especialista": pe, "usar_especialista": usar, "bueno": bueno,
           "peso": 1.0 if bueno else 0.6}
    if usar:
        out.update(mu=esp["mu"], sd=esp["sd"], w=esp["w"], umbral=esp["umbral"])
    def _t(p):
        return f"{p['top10_pct']:.0f} de cada 100 subieron 5% (al azar {p['base_pct']:.0f}), {p['ret5_top10']:+.1f}% a 5 ruedas" if p else "sin datos suficientes"
    out["texto"] = (f"{nombre} en días volátiles: el de siempre {_t(pv)}; el especialista {_t(pe)}. "
                    + ("Se usa el especialista." if usar else "Se queda el de siempre.")
                    + ("" if bueno else " En días volátiles no anticipa bien: su voto pesa menos (x0,6)."))
    return out


def modelo_del_dia(modelo: dict, volatil_hoy: bool) -> dict:
    """El modelo a usar hoy: en días volátiles, el especialista si ganó."""
    v = modelo.get("volatil") or {}
    if volatil_hoy and v.get("usar_especialista") and v.get("w"):
        return {**modelo, "mu": v["mu"], "sd": v["sd"], "w": v["w"], "umbral": v["umbral"]}
    return modelo
