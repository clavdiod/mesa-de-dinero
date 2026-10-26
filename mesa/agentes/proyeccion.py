"""28. Proyección de tu cartera: para cada cosa que tenés, qué se espera, qué conviene (mantener, sumar, vender)
y a qué precio apuntar.

- Acciones y CEDEARs:
  * Objetivo y stop: si la compraste por una propuesta del Jefe, los de ese plan. Si es un CEDEAR, el precio objetivo
    promedio de los analistas de Wall Street (Nasdaq), pasado a pesos con el precio del CEDEAR. Si no hay ninguno,
    el técnico: el máximo de los últimos 3 meses como objetivo y el mínimo del último mes como piso.
  * Proyección a 1 mes: rango donde suele terminar el precio 2 de cada 3 veces, según cuánto se movió en los últimos
    3 meses (no es una promesa: es la "zona normal").
  * Consejo: tocó el piso → vender; cerca del objetivo → tomar ganancia; la mesa en contra → vigilar o tomar parte;
    la mesa a favor y lejos del objetivo → mantener (o sumar si además está cerca de tu precio).
- Bonos, ONs y letras: se compran para cobrar. El consejo es mantener salvo que el Ministro o las calificadoras
  marquen un problema; la proyección es lo que vas a cobrar.
"""
from __future__ import annotations

import math
import statistics as st

RF = ("ons", "soberanos", "letras", "bonos", "cauciones", "provinciales")


def _rango(velas: list[dict], precio: float, ruedas: int = 20) -> tuple[float, float] | None:
    c = [v["cierre"] for v in velas[-64:] if v.get("cierre")]
    if len(c) < 30:
        return None
    r = [math.log(b / a) for a, b in zip(c, c[1:]) if a > 0 and b > 0 and abs(math.log(b / a)) < 0.25]
    if len(r) < 20:
        return None
    s = st.pstdev(r) * math.sqrt(ruedas)
    return precio * math.exp(-s), precio * math.exp(s)


def _tecnico(velas: list[dict], precio: float) -> tuple[float | None, float | None]:
    v3 = [v.get("maximo") or v["cierre"] for v in velas[-63:] if v.get("cierre")]
    v1 = [v.get("minimo") or v["cierre"] for v in velas[-21:] if v.get("cierre")]
    obj = max(v3) if v3 and max(v3) > precio * 1.03 else None
    piso = min(v1) if v1 and min(v1) < precio * 0.98 else None
    return obj, piso


def _m(x, d: int = 2) -> str:
    """Número a la argentina: 1.234,56."""
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _cob(c: dict) -> str:
    mon = "US$ " if c.get("moneda") in ("USD", "US$") else "$"
    return f"{c['fecha'][8:10]}/{c['fecha'][5:7]} {mon}{_m(c['total']) if c.get('total') is not None else '—'}"


def _f(x):
    return None if x is None else round(x, 2)


def _tecnico_cercano(velas: list[dict], precio: float) -> float | None:
    v1 = [v.get("maximo") or v["cierre"] for v in velas[-21:] if v.get("cierre")]
    return max(v1) if v1 and max(v1) > precio * 1.03 else None


def para_cartera(cartera: list[dict], titulo, velas_de, opinion: dict, propuestas: list[dict], consensos: dict,
                 precio_usa: dict, ministro: list[dict] | None, cobros: list[dict], penitencia: dict | None = None,
                 alertas: dict | None = None) -> dict:
    """Devuelve {ticker: {...}} para cada posición de la cartera."""
    out = {}
    min_por = {m.get("ticker"): m for m in ministro or []}
    abiertas = {p["ticker"]: p for p in propuestas if p.get("decision") == "aprobada"
                and (p.get("seguimiento") or {}).get("estado") in ("abierta", "pendiente")}
    for pos in cartera:
        tk = str(pos.get("ticker") or "").upper()
        t = titulo(tk) if tk else None
        if not tk:
            continue
        if not t or not t.get("ultimo"):
            prox = [c for c in cobros if c.get("ticker") == tk][:2]
            if prox:  # renta fija que no estuvo en los paneles de la ronda: igual se muestra lo que vas a cobrar
                out[tk] = {"ticker": tk, "grupo": "renta fija", "consejo": "Mantener", "motivo": "Renta fija: se tiene para cobrar.",
                           "proyeccion": "Próximos cobros: " + "; ".join(_cob(c) for c in prox)}
            continue
        precio, grupo = float(t["ultimo"]), t.get("grupo")
        compra = float(pos.get("precio") or 0) or None
        res = round((precio / compra - 1) * 100, 1) if compra else None
        op = opinion.get(tk) or {}
        x = {"ticker": tk, "grupo": grupo, "precio": precio, "compra": compra, "resultado_pct": res,
             "mesa": op.get("veredicto"), "favor": op.get("favor"), "contra": op.get("contra")}
        if grupo in RF:
            m = min_por.get(tk) or {}
            prox = [c for c in cobros if c.get("ticker") == tk][:2]
            x["consejo"] = "Vigilar" if (m.get("dir") or 0) < 0 else "Mantener"
            x["motivo"] = ("Renta fija: se tiene para cobrar. " + (m.get("texto") or "")).strip()
            x["proyeccion"] = ("Próximos cobros: " + "; ".join(_cob(c) for c in prox)) if prox else "Sin cobros en los próximos 60 días."
            out[tk] = x
            continue
        velas = velas_de(tk) or []
        rg = _rango(velas, precio)
        p = abiertas.get(tk)
        objetivo = piso = None
        fuente = None
        if p:
            objetivo, piso, fuente = p["plan"].get("objetivo"), p["plan"].get("stop"), "plan del Jefe"
        else:
            co = consensos.get(tk) or {}
            us = precio_usa.get(tk)
            o2, piso = _tecnico(velas, precio)
            if grupo == "cedears" and co.get("objetivo") and us:
                obj_an = float(co["objetivo"]) / us * precio
                n_an = (co.get("buy") or 0) + (co.get("hold") or 0) + (co.get("sell") or 0)
                if obj_an <= precio * 1.6:
                    objetivo, fuente = obj_an, f"promedio de {n_an} analistas de Wall Street"
                else:  # un objetivo de +60% o más es de antes de una caída grande: se usa el técnico cercano
                    oc = _tecnico_cercano(velas, precio) or o2
                    if oc:
                        objetivo = oc
                        fuente = f"técnico (máximo del último mes); los analistas apuntan a {_m(obj_an, 0)} (+{(obj_an / precio - 1) * 100:.0f}%), muy lejos"
            if objetivo is None and o2:
                objetivo, fuente = o2, "técnico (máximo de 3 meses)"
            # tu propio stop (una alerta de baja que dice "stop") manda sobre el técnico
            mio = [al for al in (alertas or {}).get(tk, []) if al.get("tipo") == "baja" and "stop" in str(al.get("nota", "")).lower()
                   and al.get("moneda", "ARS") == "ARS" and al.get("nivel")]
            if mio:
                piso = max(float(al["nivel"]) for al in mio)
            if piso is None and rg:
                piso = rg[0]
        pot = round((objetivo / precio - 1) * 100, 1) if objetivo else None
        a_piso = round((piso / precio - 1) * 100, 1) if piso else None
        mesa = op.get("veredicto")
        if penitencia and tk in penitencia:
            consejo, motivo = "Vigilar", "La mesa perdió sus 2 últimas ideas con este papel: está en penitencia."
        elif piso and precio <= piso:
            consejo, motivo = "Vender", "Perforó el piso" + (" (stop del plan)" if p else "") + ": la idea no se está dando."
        elif a_piso is not None and a_piso > -3:
            consejo, motivo = "Vigilar", f"Está a {_m(abs(a_piso), 1)}% del piso: si lo perfora, salir."
        elif pot is not None and pot <= 3:
            consejo, motivo = "Tomar ganancia", "Está a menos de 3% del objetivo: la mayor parte de la suba ya se dio."
        elif mesa == "en contra" and (res or 0) > 0:
            consejo, motivo = "Tomar parte", "La mesa hoy está en contra y vas ganando: asegurar una parte."
        elif mesa == "en contra":
            consejo, motivo = "Vigilar", "La mesa hoy está en contra: respetar el piso sin dudar."
        elif mesa == "a favor" and pot is not None and pot >= 15 and (res is None or res <= 5):
            consejo, motivo = "Mantener / se puede sumar", f"La mesa está a favor y le queda {pot:.0f}% hasta el objetivo."
        else:
            consejo, motivo = "Mantener", ("La mesa está a favor." if mesa == "a favor" else "Sin señales fuertes en ningún sentido.") + \
                (f" Le queda {pot:.0f}% hasta el objetivo." if pot and pot > 0 else "")
        x.update(consejo=consejo, motivo=motivo, objetivo=_f(objetivo), fuente_objetivo=fuente, potencial_pct=pot,
                 piso=_f(piso), a_piso_pct=a_piso, rango_1m=[_f(rg[0]), _f(rg[1])] if rg else None,
                 principal=op.get("principal"))
        out[tk] = x
    return out
