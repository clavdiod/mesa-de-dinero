"""29. Seguimiento diario de lo que tenés: cuántos días lleva, cuánto le queda de plazo, qué cambió hoy en la mesa
y qué opciones hay (mantener, subir el stop, vender la mitad, vender todo), con una sugerida.

La decisión es siempre tuya: la mesa sugiere, vos elegís en la app y la mesa registra lo que hiciste.
Si la opción sugerida cambia, avisa al celular.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

RF = ("ons", "soberanos", "letras", "bonos", "cauciones", "provinciales", "renta fija")
NOMBRE_ACCION = {"mantener": "Mantener", "subir_stop": "Subir el stop", "vender_mitad": "Vender la mitad", "vender_todo": "Vender todo"}


def _p(x) -> str:
    """Precio: sin decimales si es grande."""
    return _m(x, 0 if abs(x) >= 100 else 2)


def _m(x, d: int = 2) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def ruedas_entre(a: date, b: date) -> int:
    n, d = 0, a
    while d < b:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def sumar_ruedas(a: date, n: int) -> date:
    d = a
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def _vence(pos: dict, tk: str, propuestas: list[dict], libreta: list[dict], compra: date | None) -> tuple[str | None, str]:
    """Hasta cuándo tenerla: lo que diga la posición, el plan del Jefe o la idea que la marcó; si no, 20 ruedas."""
    if pos.get("vence"):
        return pos["vence"], pos.get("plazo_motivo") or "plazo que cargaste"
    p = next((x for x in reversed(propuestas) if x["ticker"] == tk and x.get("decision") == "aprobada"
              and (x.get("seguimiento") or {}).get("estado") in ("abierta", "pendiente")), None)
    if p and (p.get("plan") or {}).get("vence"):
        return p["plan"]["vence"], "plazo del plan del Jefe"
    if compra:
        ideas = [x for x in libreta if x["ticker"] == tk and x.get("origen") not in ("anticipo",) and x.get("vence")
                 and x["fecha"] <= compra.isoformat() and (compra - date.fromisoformat(x["fecha"])).days <= 7]
        if ideas:
            x = max(ideas, key=lambda y: y["fecha"])
            nom = {"anticipador": "Anticipador", "ganadores": "Cazador de ganadores", "profesionales": "Herramientas de Wall Street",
                   "mundo": "Corresponsal", "jefe": "Jefe", "oportunidad": "Oportunidad"}.get(x["origen"], x["origen"])
            return x["vence"], f"plazo de la idea del {nom}"
        return sumar_ruedas(compra, 20).isoformat(), "plazo general (20 ruedas)"
    return None, ""


def armar(cartera: list[dict], proy: dict, opinion: dict, propuestas: list[dict], libreta: list[dict],
          ayer: dict, avisados: dict, hoy: date, hora: str) -> tuple[dict, list[dict]]:
    """ayer: la foto que guardó el cierre de ayer ({tk: {...}}). avisados: {tk: "fecha|sugerida"} (se modifica).
    Devuelve (seguimiento por ticker, avisos para el celular)."""
    out, avisos = {}, []
    hoy_s = hoy.isoformat()
    for pos in cartera:
        tk = str(pos.get("ticker") or "").upper()
        x = proy.get(tk)
        if not tk or not x or x.get("grupo") in RF or not x.get("precio") or not pos.get("cantidad"):
            continue
        precio, compra_p, cant = float(x["precio"]), float(pos.get("precio") or 0) or None, int(float(pos["cantidad"]))
        f_compra = pos.get("fecha")
        p_jefe = next((p for p in reversed(propuestas) if p["ticker"] == tk and p.get("decision") == "aprobada"
                       and (p.get("seguimiento") or {}).get("fecha_entrada")), None)
        if not f_compra and p_jefe:
            f_compra = p_jefe["seguimiento"]["fecha_entrada"]
        compra_d = date.fromisoformat(f_compra) if f_compra else None
        vence, plazo_motivo = _vence(pos, tk, propuestas, libreta, compra_d)
        dias = ruedas_entre(compra_d, hoy) if compra_d else None
        total = ruedas_entre(compra_d, date.fromisoformat(vence)) if compra_d and vence else None
        res = x.get("resultado_pct")
        piso, obj = x.get("piso"), x.get("objetivo")
        # cuánto puede subir en los próximos días: el techo normal a 5 ruedas (raíz del tiempo sobre el de 1 mes)
        r1 = x.get("rango_1m")
        techo5 = round(((r1[1] / precio) ** 0.5 - 1) * 100, 1) if r1 and r1[1] else None
        riesgo_u = (compra_p - piso) if compra_p and piso and compra_p > piso else None
        # --- opciones ---
        ops = [{"accion": "mantener", "texto": "Mantener" + (f": en los próximos días lo normal es que pueda subir hasta +{_m(techo5, 1)}%" if techo5 else "")
                + (f" (objetivo {_p(obj)})" if obj else "") + "."}]
        nuevo_stop = None
        if compra_p and riesgo_u and precio >= compra_p + 2 * riesgo_u:
            nuevo_stop = round(compra_p + riesgo_u, 2)
        elif compra_p and riesgo_u and precio >= compra_p + riesgo_u:
            nuevo_stop = round(compra_p, 2)
        elif compra_p and res is not None and res >= 6:
            nuevo_stop = round(compra_p, 2)
        if compra_p and piso and piso >= compra_p and res is not None and res >= 8:
            nuevo_stop = round(compra_p + (precio - compra_p) / 2, 2)  # ya no pierde: ahora se asegura la mitad de lo ganado
        if nuevo_stop and piso and nuevo_stop <= piso:
            nuevo_stop = None  # el stop que tenés ya protege eso
        if nuevo_stop:
            ops.append({"accion": "subir_stop", "nivel": nuevo_stop,
                        "texto": f"Subir el stop a {_p(nuevo_stop)}" + (" (tu precio de compra: ya no podés perder)." if nuevo_stop == round(compra_p, 2)
                                                                     else " (asegurás parte de la ganancia).")})
        if cant >= 2:
            ops.append({"accion": "vender_mitad", "cantidad": cant // 2, "texto": f"Vender la mitad ({cant // 2}) y dejar correr el resto."})
        ops.append({"accion": "vender_todo", "cantidad": cant, "texto": f"Vender todo ({cant})."})
        # --- la sugerida ---
        cons = x.get("consejo") or ""
        plazo_cumplido = bool(dias is not None and total and dias >= total)
        if cons.startswith("Vender"):
            sug, por_que = "vender_todo", x.get("motivo")
        elif cons.startswith("Tomar"):
            sug, por_que = "vender_mitad", x.get("motivo")
        elif plazo_cumplido:
            sug = "vender_mitad" if (res or 0) > 1.2 else "vender_todo"
            por_que = f"Se cumplió el plazo ({total} ruedas): " + ("asegurá ganancia." if sug == "vender_mitad" else "la idea no se dio en su tiempo.")
        elif nuevo_stop:
            sug, por_que = "subir_stop", "Ya va bien a favor: proteger lo ganado."
        else:
            sug, por_que = "mantener", x.get("motivo")
        for o in ops:
            o["sugerida"] = o["accion"] == sug
        # --- qué cambió hoy (contra la última ronda de ayer) ---
        ahora = {"fecha": hoy_s, "a_favor": sorted((opinion.get(tk) or {}).get("a_favor") or []),
                 "en_contra": sorted((opinion.get(tk) or {}).get("en_contra") or []), "precio": precio, "sugerida": sug}
        ay = ayer.get(tk) or {}
        cambios = []
        if ay:
            if ay.get("precio"):
                cambios.append(f"Precio {'+' if precio >= ay['precio'] else ''}{_m((precio / ay['precio'] - 1) * 100, 1)}% desde ayer.")
            nuevos_f = [a for a in ahora["a_favor"] if a not in (ay.get("a_favor") or [])]
            nuevos_c = [a for a in ahora["en_contra"] if a not in (ay.get("en_contra") or [])]
            se_fueron = [a for a in (ay.get("a_favor") or []) if a not in ahora["a_favor"]]
            if nuevos_f:
                cambios.append("Ahora a favor: " + ", ".join(nuevos_f) + ".")
            if nuevos_c:
                cambios.append("Ahora en contra: " + ", ".join(nuevos_c) + ".")
            if se_fueron:
                cambios.append("Dejaron de estar a favor: " + ", ".join(se_fueron) + ".")
            if ay.get("sugerida") and ay["sugerida"] != sug:
                cambios.append(f"La sugerencia cambió: antes «{NOMBRE_ACCION[ay['sugerida']]}», hoy «{NOMBRE_ACCION[sug]}».")
        if not cambios:
            cambios = ["Sin cambios importantes en la mesa."] if ay else ["Primer día de seguimiento."]
        if sug != "mantener" and avisados.get(tk) != f"{hoy_s}|{sug}":
            avisos.append({"fecha": hoy_s, "hora": hora, "ticker": f"{tk} (decidir)",
                           "texto": f"{tk}: la mesa sugiere «{NOMBRE_ACCION[sug]}». {por_que or ''} Entrá a Mi cartera y decidí."})
            avisados[tk] = f"{hoy_s}|{sug}"
        # el cartel: lo que hay que hacer, en una línea
        fv = (lambda f: f"{f[8:10]}/{f[5:7]}") if vence else None
        resto = (total - dias) if (total is not None and dias is not None) else None
        stop_txt = next((o for o in ops if o["accion"] == "subir_stop"), None)
        if sug == "vender_todo":
            titular, color = "SALIR HOY", "rojo"
        elif sug == "vender_mitad":
            titular, color = "VENDER LA MITAD HOY", "amar"
        elif resto == 1:
            titular, color = "SALIR MAÑANA · vence el plazo", "amar"
        elif piso and precio <= piso * 1.03:
            titular, color = f"ATENTO · a menos de 3% del stop ({_p(piso)})", "amar"
        elif sug == "subir_stop" and stop_txt:
            titular, color = f"MANTENER{' hasta el ' + fv(vence) if vence else ''} · subí el stop a {_p(stop_txt['nivel'])}", "verde"
        else:
            titular, color = f"MANTENER{' hasta el ' + fv(vence) if vence else ''}", "verde"
        out[tk] = {"ticker": tk, "titular": titular, "color": color, "fecha_compra": f_compra, "vence": vence, "plazo_motivo": plazo_motivo, "dias": dias, "total": total,
                   "plazo_cumplido": plazo_cumplido, "cantidad": cant, "precio": precio, "compra": compra_p, "resultado_pct": res,
                   "sugerida": sug, "por_que": por_que, "opciones": ops, "cambios": cambios, "techo5": techo5, "piso": piso, "objetivo": obj,
                   "compra_punta": x.get("aviso_spread"), "ahora": ahora}
    return out, avisos
