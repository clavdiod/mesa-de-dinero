"""Supervisor: arma el expediente de debate de un activo y da una opinión por reglas (sin IA, gratis).

El expediente junta lo que dijo cada analista (a favor / en contra / neutral), el plan de Riesgo,
el debate alcista/bajista (con IA si hay, si no con los argumentos de los propios agentes)
y el veredicto del supervisor. Se guarda en ui/debates para la hoja "Debate" de la web.
"""
from __future__ import annotations

from ..nucleo.config import config

UMBRAL_COMPRA = 0.6
UMBRAL_INTERES = 0.3


def _entrada_para_r(plan: dict, r_min: float, com: float) -> float | None:
    """Precio de entrada más alto (≤ entrada actual) que deja la relación neta ≥ r_min, con el mismo stop y objetivo."""
    stop, obj, e = plan["stop"], plan["objetivo"], plan["entrada"]
    paso = (e - stop) / 200
    while e > stop + paso:
        gan = (obj - e) / e * 100 - com
        per = (e - stop) / e * 100 + com
        if per > 0 and gan / per >= r_min:
            return round(e, 4)
        e -= paso
    return None


def argumentos(senales: list[dict]) -> dict:
    orden = lambda xs: sorted(xs, key=lambda s: -float(s.get("fuerza") or 0))
    return {"favor": orden([s for s in senales if (s.get("direccion") or 0) > 0]),
            "contra": orden([s for s in senales if (s.get("direccion") or 0) < 0 or s.get("veto")]),
            "neutral": [s for s in senales if not s.get("direccion") and not s.get("veto")]}


def debate_reglas(senales: list[dict], clima: str | None) -> dict:
    a = argumentos(senales)
    alc = " ".join(s["texto"] for s in a["favor"][:2] if s.get("texto")) or "Ningún analista ve motivos fuertes para comprar."
    baj = " ".join(s["texto"] for s in a["contra"][:2] if s.get("texto"))
    if not baj:
        baj = "Nadie lo ataca de frente; el riesgo es el clima general" + (f" (hoy {clima})." if clima else ".")
    return {"alcista": alc, "bajista": baj, "fuente": "reglas"}


def opinion(senales: list[dict], puntaje: float, plan: dict | None, riesgo: dict | None,
            precio: float | None) -> dict:
    """Veredicto: comprar / esperar / evitar / neutral, con explicación y precio sugerido."""
    c = config()
    com = c["capital"]["comision_ida_vuelta_pct"]
    r_min = c["riesgo"]["r_minimo_neto"]
    a = argumentos(senales)
    base = f"{len(a['favor'])} a favor, {len(a['contra'])} en contra (puntaje {puntaje:+.2f})."
    pro = a["favor"][0]["texto"] if a["favor"] else None
    con = a["contra"][0]["texto"] if a["contra"] else None
    detalle = [base] + ([f"Lo más fuerte a favor: {pro}"] if pro else []) + ([f"Lo más fuerte en contra: {con}"] if con else [])
    out = {"veredicto": "neutral", "titulo": "Sin señal clara: esperar", "precio_sugerido": None, "detalle": detalle}

    if any(s.get("veto") for s in senales):
        out.update(veredicto="evitar", titulo="Evitar: hecho grave del emisor")
        return out
    if puntaje <= -UMBRAL_INTERES:
        out.update(veredicto="evitar", titulo="Evitar: la mayoría de los analistas está en contra")
        return out
    if not plan:
        if puntaje >= UMBRAL_INTERES:
            out.update(veredicto="esperar", titulo="Interesante, pero falta historial para armar el plan")
        return out
    motivos = (riesgo or {}).get("motivos") or []
    if puntaje >= UMBRAL_COMPRA and riesgo and riesgo.get("ok"):
        lim = plan["entrada"]
        out.update(veredicto="comprar", precio_sugerido=lim,
                   titulo=(f"Comprar con límite en {lim:g}" if precio and lim < precio * 0.995 else "Comprar"))
        out["detalle"].append(f"Plan: entrada {plan['entrada']:g}, objetivo {plan['objetivo']:g}, stop {plan['stop']:g} "
                              f"({riesgo.get('r_neto')}R neto, tamaño {riesgo.get('tamano_r')}R).")
        return out
    if puntaje >= UMBRAL_INTERES or (puntaje > 0 and riesgo and riesgo.get("ok")):
        mejor = _entrada_para_r(plan, r_min, com) if any("Relación neta" in m for m in motivos) else None
        if mejor:
            out.update(veredicto="esperar", precio_sugerido=mejor, titulo=f"Esperar: entraría cerca de {mejor:g}")
            out["detalle"].append(f"A {plan['entrada']:g} no paga el riesgo; a {mejor:g} la relación llega a {r_min}R neto.")
        elif motivos:
            out.update(veredicto="esperar", titulo=f"Esperar: {motivos[0].rstrip('.')}")
        else:
            out.update(veredicto="esperar", titulo="Esperar: señal a favor, todavía débil")
        return out
    if motivos:
        out["detalle"].append(f"Riesgo: {motivos[0]}")
    return out


def expediente(tk: str, ctx, senales: list[dict], puntaje: float, evaluado: dict | None,
               elegido: dict | None, hora: str) -> dict:
    t = ctx.titulo(tk) or {}
    plan = (evaluado or {}).get("plan")
    riesgo = (evaluado or {}).get("riesgo")
    clima = ctx.extra.get("clima_estado")
    deb = (evaluado or {}).get("debate") or debate_reglas(senales, clima)
    op = opinion(senales, puntaje, plan, riesgo, t.get("ultimo"))
    jefe = None
    if elegido:
        jefe = {"decision": "propuesta", "texto": elegido.get("resumen_jefe"), "confianza": elegido.get("confianza")}
    elif evaluado and evaluado.get("motivo_descarte"):
        jefe = {"decision": "descartada", "texto": evaluado["motivo_descarte"]}
    a = argumentos(senales)
    corta = lambda xs: [{k: s.get(k) for k in ("agente", "direccion", "fuerza", "texto", "veto")} for s in xs]
    return {"ticker": tk, "fecha": ctx.fecha.isoformat(), "hora": hora, "grupo": t.get("grupo"),
            "precio": {k: t.get(k) for k in ("ultimo", "variacion", "compra", "venta")},
            "clima": clima, "puntaje": puntaje, "favor": corta(a["favor"]), "contra": corta(a["contra"]),
            "neutral": corta(a["neutral"]), "plan": plan, "riesgo": riesgo, "debate": deb,
            "supervisor": op, "jefe": jefe,
            "historiador": next((s.get("datos") for s in senales if s.get("agente") == "historiador"), None)}
