"""30. El Comité: reemplaza al Jefe. Los analistas votan y la mesa llega a una conclusión.

- Cada voto pesa según cuánto acertó DE VERDAD ese analista en vivo (no en la teoría):
  * los que anticipan (Anticipador, Anticipo NY, Corresponsal, Cazador, Herramientas de Wall Street) por su
    libreta de pronósticos: de las ideas cerradas, cuántas se dieron;
  * el resto por su estadística a 10 ruedas.
  Acertar 50% (una moneda) pesa x1; cada punto arriba o abajo suma o resta. Entre x0,4 y x2. Con pocos casos, x1.
- Se aprueba una compra si: hay al menos 2 analistas distintos a favor, el peso a favor es al menos 1,6 veces el
  peso en contra y alcanza un mínimo. Riesgo ya la aprobó antes (costos, balance, protecciones): eso no se vota.
- La conclusión sale escrita: quién votó qué, con cuánto peso, y el plazo para tenerla.
"""
from __future__ import annotations

from datetime import date

# 02/11: los que pueden PROPONER una compra (probados con años de historia o con el análisis técnico medido).
# El resto (Comprador de pánico, Economista, Corresponsal, Anticipo NY...) solo confirma o frena.
PROPONEN = {"anticipador_arg", "anticipador", "anticipador_mundo", "ganadores", "profesionales", "wallstreet", "tecnico",
            "oportunidades_mediano", "historiador"}
HISTORIA = {"anticipador_arg", "anticipador", "anticipador_mundo", "ganadores", "profesionales", "wallstreet", "tecnico"}
SOLO_CONFIRMA = {"panico": 0.5, "mundo": 0.7, "anticipo": 0.7, "adr": 0.7}  # tope de su peso

ORIGENES = ("anticipador", "anticipador_arg", "anticipador_mundo", "anticipo", "mundo", "ganadores", "profesionales")
MINIMO_FAVOR, RELACION, MIN_AGENTES = 1.0, 1.6, 2


def _peso(hit: float) -> float:
    return round(max(0.4, min(2.0, 1 + (hit - 0.5) * 4)), 2)


def pesos_vivos(libreta: list[dict], stats: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for o in ORIGENES:
        xs = [x for x in libreta or [] if x.get("origen") == o and x.get("estado") in ("se_dio", "fallo", "no_se_dio")]
        if len(xs) >= 10:
            hit = sum(1 for x in xs if x["estado"] == "se_dio") / len(xs)
            out[o] = {"peso": _peso(hit), "acierto": round(hit * 100), "casos": len(xs), "fuente": "pronósticos en vivo"}
            if hit < 0.35:  # Reglas de la mesa: dado de baja hasta que vuelva a aprobar
                out[o].update(peso=0.0, baja=True)
    for ag, d in (stats or {}).items():
        if ag in out or not isinstance(d, dict):
            continue
        h = d.get("10") or {}
        if h.get("casos", 0) >= 30:
            hit = h["aciertos"] / h["casos"]
            out[ag] = {"peso": _peso(hit), "acierto": round(hit * 100), "casos": h["casos"], "fuente": "señales en vivo a 10 ruedas"}
            if hit < 0.35:
                out[ag].update(peso=0.0, baja=True)
    return out


def votar(e: dict, pesos: dict) -> dict:
    """Un voto por analista (su señal más fuerte), multiplicado por su peso real."""
    from .revision import nombre
    mejor: dict[str, dict] = {}
    for s in e.get("senales") or []:
        if not s.get("direccion") or s.get("agente") in ("riesgo", "comite", "jefe"):
            continue
        if abs(s["direccion"] * s["fuerza"]) > abs((mejor.get(s["agente"]) or {}).get("v", 0)):
            mejor[s["agente"]] = {"v": s["direccion"] * s["fuerza"], "texto": s.get("texto", "")}
    votos = []
    for ag, m in mejor.items():
        p = min((pesos.get(ag) or {}).get("peso", 1.0), SOLO_CONFIRMA.get(ag, 9))
        votos.append({"agente": ag, "nombre": nombre(ag), "dir": 1 if m["v"] > 0 else -1, "fuerza": round(abs(m["v"]), 2),
                      "peso": p, "voto": round(m["v"] * p, 2), "acierto": (pesos.get(ag) or {}).get("acierto"),
                      "texto": m["texto"][:200]})
    favor = round(sum(v["voto"] for v in votos if v["voto"] > 0), 2)
    contra = round(-sum(v["voto"] for v in votos if v["voto"] < 0), 2)
    n_favor = sum(1 for v in votos if v["voto"] > 0)
    n_hist = sum(1 for v in votos if v["voto"] > 0 and v["agente"] in HISTORIA)
    eco_contra = any(v["agente"] == "economista" and v["voto"] < 0 for v in votos)
    est = e.get("estructura") or {}
    cayendo_arg = e.get("grupo") == "acciones" and (est.get("estado") == "cayendo" or est.get("minimo_anual") == "perforado")
    ok = (n_favor >= MIN_AGENTES + (1 if eco_contra else 0) and favor >= MINIMO_FAVOR and favor >= RELACION * contra
          and n_hist >= 1 and not cayendo_arg)
    if n_hist < 1:
        motivo = "Ningún analista probado con la historia (Anticipadores, Cazador, Wall Street, Técnico) la marca: no se propone."
    elif cayendo_arg:
        motivo = "Acción argentina que sigue cayendo (o perforó su mínimo anual): la historia dice esperar a que deje de caer."
    elif eco_contra and n_favor < MIN_AGENTES + 1:
        motivo = "El Economista está en contra del sector: hace falta un analista más a favor."
    elif n_favor < MIN_AGENTES:
        motivo = "Solo un analista a favor: hace falta que otro con otro método lo confirme."
    elif favor < MINIMO_FAVOR:
        motivo = f"Votos a favor flojos ({favor:.1f}): no alcanza el mínimo ({MINIMO_FAVOR})."
    elif favor < RELACION * contra:
        motivo = f"Demasiado en contra: {favor:.1f} a favor contra {contra:.1f} en contra."
    else:
        motivo = ""
    return {"votos": sorted(votos, key=lambda v: -abs(v["voto"])), "favor": favor, "contra": contra, "neto": round(favor - contra, 2),
            "n_favor": n_favor, "n_contra": sum(1 for v in votos if v["voto"] < 0), "aprobada": ok, "motivo": motivo}


def _x(p: float) -> str:
    return f"x{p:.1f}".replace(".", ",")


def conclusion(e: dict, v: dict) -> str:
    from .revision import nombre
    fav = [x for x in v["votos"] if x["voto"] > 0][:4]
    con = [x for x in v["votos"] if x["voto"] < 0][:3]
    pl = e.get("plan") or {}
    plazo = f" Plazo: {e.get('ruedas')} ruedas" + (f" (hasta el {pl['vence'][8:10]}/{pl['vence'][5:7]})" if pl.get("vence") else "") \
        + (f", lo marca {nombre(e['principal'])}." if e.get("principal") else ".") if e.get("ruedas") else ""
    lf = ", ".join(x["nombre"] + " " + _x(x["peso"]) for x in fav)
    lc = ", ".join(x["nombre"] + " " + _x(x["peso"]) for x in con)
    num = lambda z: f"{z:.1f}".replace(".", ",")
    return (f"Comité: {v['n_favor']} a favor ({lf})" + (f", {v['n_contra']} en contra ({lc})" if con else ", nadie en contra")
            + f". Peso {num(v['favor'])} contra {num(v['contra'])}." + plazo)


def decidir(candidatos: list[dict], pesos: dict, cupo: int) -> tuple[list[dict], list[dict]]:
    """Devuelve (elegidos, acta de todos los que se votaron)."""
    acta, aprobados = [], []
    for e in candidatos:
        v = votar(e, pesos)
        e["comite"] = v
        acta.append({"ticker": e["ticker"], "aprobada": v["aprobada"], "favor": v["favor"], "contra": v["contra"],
                     "motivo": v["motivo"], "votos": v["votos"][:8], "ruedas": e.get("ruedas"), "principal": e.get("principal")})
        if v["aprobada"]:
            aprobados.append(e)
    aprobados.sort(key=lambda e: e["comite"]["neto"], reverse=True)
    elegidos = [{**e, "confianza": "alta" if e["comite"]["favor"] >= 3 * max(e["comite"]["contra"], 0.5) else "media",
                 "resumen_jefe": conclusion(e, e["comite"])} for e in aprobados[:max(cupo, 0)]]
    return elegidos, sorted(acta, key=lambda a: (-a["aprobada"], -(a["favor"] - a["contra"])))
