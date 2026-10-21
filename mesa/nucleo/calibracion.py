"""Calibración de los agentes: que la fuerza con la que opinan coincida con lo que aciertan de verdad.

Dos fuentes:
1. Entrenamiento con la historia: se "rebobina" el mercado día por día con el historial guardado
   (unos 400 días) y se hace opinar a los agentes que trabajan con precios (Técnico, Historiador,
   Fuerza relativa) como si fuera ese día; después se mira qué pasó 10 ruedas más tarde.
2. Lo que van acertando en vivo (ranking/stats), que reemplaza a lo histórico cuando hay casos suficientes.

Resultado por agente: un factor que multiplica su voto. Si dice "fuerte" y acierta como una moneda,
su voto vale mucho menos; si acierta más de lo que promete, vale un poco más (tope 1,5).
"""
from __future__ import annotations

from datetime import date

from .config import config
from .contexto import Contexto

BANDAS = (("debil", 0.0, 0.4), ("media", 0.4, 0.7), ("fuerte", 0.7, 1.01))
HORIZONTE = 10


def banda(fuerza: float) -> str:
    return next(n for n, a, b in BANDAS if a <= fuerza < b)


def _sumar(d: dict, ret: float, fuerza: float) -> None:
    d["casos"] = d.get("casos", 0) + 1
    d["aciertos"] = d.get("aciertos", 0) + int(ret > 0)
    d["suma_ret"] = round(d.get("suma_ret", 0.0) + ret, 4)
    d["suma_fuerza"] = round(d.get("suma_fuerza", 0.0) + fuerza, 4)


class _CacheHasta:
    """Historial visto desde una fecha del pasado (sin mirar el futuro)."""

    def __init__(self, series: dict[str, list[dict]], hasta: dict[str, int]):
        self.s, self.h = series, hasta
        self.indice = {tk: 1 for tk in hasta}

    def velas(self, tk: str) -> list[dict]:
        i = self.h.get(tk)
        return self.s[tk][:i] if i else []


def entrenar_con_historia(series: dict[str, list[dict]], grupos: dict[str, str], params: dict,
                          paso: int = 2, desde: int = 100) -> dict:
    """Devuelve estadística por agente y banda de fuerza, a HORIZONTE ruedas."""
    from ..agentes import analistas

    series = {tk: v for tk, v in series.items() if len(v) >= desde + HORIZONTE + 5 and grupos.get(tk) in ("acciones", "cedears")}
    if not series:
        return {}
    pos = {tk: {v["fecha"]: i for i, v in enumerate(vs)} for tk, vs in series.items()}
    fechas = sorted({v["fecha"] for vs in series.values() for v in vs})
    stats: dict = {}
    for f in fechas[desde:-HORIZONTE:paso]:
        hasta, paneles = {}, {}
        for tk, vs in series.items():
            i = pos[tk].get(f)
            if i is None or i < 80 or i + HORIZONTE >= len(vs):
                continue
            hasta[tk] = i
            v = vs[i]
            paneles.setdefault(grupos[tk], []).append({"simbolo": tk, "ultimo": v["cierre"], "maximo": v["maximo"],
                                                       "minimo": v["minimo"], "volumen": v.get("volumen")})
        if len(hasta) < 5:
            continue
        ctx = Contexto(date.fromisoformat(f), "17:00", paneles, cache=_CacheHasta(series, hasta), params=params)
        tks = list(hasta)
        sen = analistas.tecnico(ctx, tks) + analistas.historiador(ctx, tks) + analistas.fuerza_relativa(ctx, tks)
        for s in sen:
            if not s.direccion:
                continue
            vs, i = series[s.ticker], hasta[s.ticker]
            ret = (vs[i + HORIZONTE]["cierre"] / vs[i]["cierre"] - 1) * 100 * s.direccion
            ag = stats.setdefault(s.agente, {"total": {}, "bandas": {}})
            _sumar(ag["total"], ret, s.fuerza)
            _sumar(ag["bandas"].setdefault(banda(s.fuerza), {}), ret, s.fuerza)
    return stats


def factor(d: dict) -> float | None:
    """Acierto real contra lo que el agente "promete" con su fuerza (50% + 30% × fuerza)."""
    casos = d.get("casos", 0)
    if not casos:
        return None
    hit = d["aciertos"] / casos
    esperanza = d["suma_ret"] / casos
    f_media = d.get("suma_fuerza", 0.6 * casos) / casos
    if esperanza <= 0 or hit <= 0.5:
        return 0.3
    return round(max(0.3, min(1.5, (hit - 0.5) / (0.3 * f_media))), 2)


def calibrar(vivo: dict, historico: dict) -> dict:
    """agente -> {factor, fuente, casos, acierto_pct, esperanza_pct, bandas}. Vivo manda si tiene casos suficientes."""
    minimo = config()["ranking"]["minimo_casos"]
    out = {}
    for ag in set(vivo) | set(historico):
        v = (vivo.get(ag) or {}).get(str(HORIZONTE)) or {}
        h = (historico.get(ag) or {}).get("total") or {}
        if v.get("casos", 0) >= minimo:
            d, fuente, bandas = v, "en vivo", (vivo.get(ag) or {}).get("bandas", {}).get(str(HORIZONTE), {})
        elif h.get("casos", 0) >= 30:
            d, fuente, bandas = h, "historia", (historico.get(ag) or {}).get("bandas", {})
        else:
            continue
        out[ag] = {"factor": factor(d), "fuente": fuente, "casos": d["casos"],
                   "acierto_pct": round(d["aciertos"] / d["casos"] * 100, 1),
                   "esperanza_pct": round(d["suma_ret"] / d["casos"], 2),
                   # cada banda (débil / media / fuerte) con su propio factor: un agente puede acertar en un tipo
                   # de señal y errar en otro (ej. Técnico: acierta rebotes, falla quiebres)
                   "bandas": {b: {"casos": x["casos"], "acierto_pct": round(x["aciertos"] / x["casos"] * 100, 1),
                                  "esperanza_pct": round(x["suma_ret"] / x["casos"], 2),
                                  "factor": factor(x) if x["casos"] >= 30 else None}
                              for b, x in bandas.items() if x.get("casos")}}
    return out
