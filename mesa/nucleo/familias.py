"""22/11 (revisión con Clau: "revisá si se pisan"): agentes que miran lo mismo cuentan UNA sola vez.

Antes, un quiebre con volumen sumaba tres votos (Acciones, Volumen y Técnico miran variación, volumen y medias) y una
noticia podía votar dos veces con el mismo nombre (Corresponsal por tema y por papel). Ahora, por cada papel, de cada
familia vale solo el voto más fuerte. Los demás quedan a la vista ("misma familia"), pero no suman.
"""
from __future__ import annotations

FAMILIAS: dict[str, set[str]] = {
    "grafico": {"acciones", "tecnico", "volumen_flujo"},           # variación, volumen y medias del mismo gráfico
    "noticias": {"noticias", "mundo", "hechos_emisor"},             # titulares de la misma empresa o del mismo tema
    "macro": {"macro_dolar", "economista", "ministro"},             # riesgo país, dólar, brecha, tasas
}
_DE = {a: f for f, ags in FAMILIAS.items() for a in ags}


def familia(agente: str) -> str:
    """La familia del agente; el que no comparte cálculo con nadie es su propia familia."""
    return _DE.get(agente, agente)


def uno_por_familia(aportes: list[tuple[str, float]]) -> dict[str, tuple[str, float]]:
    """aportes: (agente, valor con signo). Devuelve {familia: (agente que cuenta, valor)} con el de mayor peso absoluto.
    El mismo agente con dos señales sobre el mismo papel también cuenta una sola vez."""
    out: dict[str, tuple[str, float]] = {}
    for ag, v in aportes:
        if not v:
            continue
        f = familia(ag)
        if f not in out or abs(v) > abs(out[f][1]):
            out[f] = (ag, v)
    return out
