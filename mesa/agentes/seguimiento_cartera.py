"""29. Seguimiento diario de lo que tenés: cuántos días lleva, cuánto le queda de plazo, qué cambió hoy en la mesa
y qué opciones hay (mantener, subir el stop, vender la mitad, vender todo), con una sugerida.

La decisión es siempre tuya: la mesa sugiere, vos elegís en la app y la mesa registra lo que hiciste.
Si la opción sugerida cambia, avisa al celular.
"""
from __future__ import annotations

import math
from datetime import date, timedelta

RF = ("ons", "soberanos", "letras", "bonos", "cauciones", "provinciales", "renta fija")
NOM_URG = {"vender_todo": "vendé todo", "vender_mitad": "vendé la mitad"}
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
        return p["plan"]["vence"], "plazo del plan del Comité"
    if compra:
        ideas = [x for x in libreta if x["ticker"] == tk and x.get("origen") not in ("anticipo",) and x.get("vence")
                 and x["fecha"] <= compra.isoformat() and (compra - date.fromisoformat(x["fecha"])).days <= 7]
        if ideas:
            x = max(ideas, key=lambda y: y["fecha"])
            nom = {"anticipador": "Anticipador", "ganadores": "Cazador de ganadores", "profesionales": "Herramientas de Wall Street",
                   "mundo": "Corresponsal", "jefe": "Comité", "oportunidad": "Oportunidad de la mesa"}.get(x["origen"], x["origen"])
            return x["vence"], f"plazo de la idea que lo marcó ({nom})"
        return sumar_ruedas(compra, 20).isoformat(), "plazo general (20 ruedas)"
    return None, ""


def replantear_plazo(tk: str, vence: str | None, compra: date | None, hoy: date, x: dict, op: dict,
                     eventos: list[dict], noticias: list[dict]) -> tuple[str | None, list[str]]:
    """El plazo no es fijo: cada día se revisa con lo que dice la mesa, la estadística del papel y las noticias.
    Devuelve (nuevo vencimiento, motivos de los cambios)."""
    if not vence:
        return vence, []
    v, motivos = date.fromisoformat(vence), []
    fv = lambda d: f"{d.day:02d}/{d.month:02d}"
    tope = sumar_ruedas(compra, 60) if compra else sumar_ruedas(hoy, 60)
    # 1) balance antes del final: el plazo termina el día anterior (en el balance puede saltar para cualquier lado)
    base = tk[:-1] if tk[-1:] in ("D", "C") else tk
    bal = next((e for e in eventos or [] if e.get("tipo") == "balance" and e.get("ticker") in (tk, base)
                and hoy.isoformat() <= e.get("fecha", "") <= v.isoformat()), None)
    if bal:
        b = date.fromisoformat(bal["fecha"]) - timedelta(days=1)
        while b.weekday() >= 5:
            b -= timedelta(days=1)
        if b < v:
            v = max(b, hoy)
            motivos.append(f"Presenta balance el {bal['fecha'][8:10]}/{bal['fecha'][5:7]}: el plazo termina el {fv(v)} (decidí antes si te quedás para el balance).")
    larga = bool(compra and ruedas_entre(compra, date.fromisoformat(vence)) >= 10)
    # 2) noticia fuerte en contra: se acorta a 1 rueda. 30/10: en una idea larga, solo una noticia DE LA EMPRESA
    # (no un tema general como "la Fed sube tasas", que le pega a todo el mercado y ya lo cubre el stop).
    especifica = lambda n: not larga or str(n.get("texto") or "").startswith(("Noticias de", "Hecho relevante", "Hechos del emisor")) or n.get("agente") in ("hechos_emisor",)
    mala = next((n for n in noticias or [] if n.get("dir", 0) < 0 and (n.get("fuerza") or 0) >= 0.4 and especifica(n)), None)
    if mala and sumar_ruedas(hoy, 1) < v:
        v = sumar_ruedas(hoy, 1)
        motivos.append(f"Noticia en contra: «{(mala.get('texto') or '')[:110]}». Plazo acortado al {fv(v)}.")
    # 3) la mesa se dio vuelta: 2 ruedas para salir con calma. 30/10: solo para ideas cortas (menos de 10 ruedas).
    # En una idea de 2-4 semanas con stop, que los analistas de corto plazo se pongan en contra un día no la rompe:
    # la protege el stop (YPFD y CEPU pasaban de "hasta el 26/11" a "salir mañana" por eso).
    contra, favor = len(op.get("en_contra") or []), len(op.get("a_favor") or [])
    if not larga and (x.get("mesa") == "en contra" or contra >= favor + 2) and sumar_ruedas(hoy, 2) < v:
        v = sumar_ruedas(hoy, 2)
        motivos.append(f"La mesa se puso en contra ({contra} en contra, {favor} a favor): plazo acortado al {fv(v)}.")
    # 4) casi en el objetivo: no hace falta esperar
    pot = x.get("potencial_pct")
    if not larga and pot is not None and pot <= 5 and sumar_ruedas(hoy, 2) < v:
        v = sumar_ruedas(hoy, 2)
        motivos.append(f"Le queda solo {str(round(pot, 1)).replace('.', ',')}% hasta el objetivo: plazo acortado al {fv(v)}.")
    # 5) todo a favor y con recorrido, cerca del final: se estira (nunca más de 60 ruedas desde la compra)
    buena = next((n for n in noticias or [] if n.get("dir", 0) > 0 and (n.get("fuerza") or 0) >= 0.4), None)
    if not motivos and ruedas_entre(hoy, v) <= 2 and ((x.get("mesa") == "a favor" and (pot or 0) >= 10) or buena):
        nv = min(sumar_ruedas(v, 5), tope)
        if nv > v:
            v = nv
            motivos.append(("La mesa sigue a favor y le queda " + str(round(pot or 0)) + "% de recorrido" if not buena
                            else f"Noticia a favor: «{(buena.get('texto') or '')[:100]}»") + f": plazo estirado al {fv(v)}.")
    return v.isoformat(), motivos


def armar(cartera: list[dict], proy: dict, opinion: dict, propuestas: list[dict], libreta: list[dict],
          ayer: dict, avisados: dict, hoy: date, hora: str, eventos: list[dict] | None = None,
          noticias: dict[str, list[dict]] | None = None, marcados: set | None = None) -> tuple[dict, list[dict]]:
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
        vence_base, plazo_motivo = _vence(pos, tk, propuestas, libreta, compra_d)
        vence, cambios_plazo = replantear_plazo(tk, vence_base, compra_d, hoy, x, opinion.get(tk) or {}, eventos or [], (noticias or {}).get(tk) or [])
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
        # alarma de "estás devolviendo la ganancia": llegó a ganar 5% o más y ya devolvió la mitad
        mx = x.get("max_desde_compra")
        gan_max = (mx / compra_p - 1) * 100 if mx and compra_p else None
        # solo con al menos una rueda completa desde la compra: el mismo día no hay ganancia "devuelta"
        devolviendo = bool(gan_max is not None and gan_max >= 5 and res is not None and res <= gan_max / 2
                           and (dias or 0) >= 1)
        if devolviendo:
            sug = "vender_todo" if (res or 0) <= 1.5 else "vender_mitad"
            por_que = (f"Llegó a ganar {_m(gan_max, 1)}% (máximo {_p(mx)}) y ya devolvió más de la mitad: hoy vas {_m(res, 1)}%. "
                       + ("Salí antes de perder." if sug == "vender_todo" else "Asegurá al menos la mitad."))
        elif cons.startswith("Dejar correr") and compra_p:
            # stop que sube solo: nunca debajo de tu compra ni del objetivo cumplido, y a ~6% del máximo alcanzado
            oi = x.get("objetivo_idea") or 0
            lvl = round(max(compra_p, oi * 0.97, (mx or precio) * 0.94), 2)
            if lvl < precio and not (piso and lvl <= piso):
                nuevo_stop = lvl
                ops = [o for o in ops if o["accion"] != "subir_stop"]
                ops.insert(1, {"accion": "subir_stop", "nivel": lvl, "texto": f"Subir el stop a {_p(lvl)} y dejar correr hacia {_p(obj)}. "
                               "Si sigue subiendo, el stop sube con el máximo (6% debajo): ganás más y nunca devolvés lo ganado."})
            sug, por_que = ("subir_stop" if nuevo_stop else "mantener"), x.get("motivo")
        elif cons.startswith("Vender"):
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
        # --- antes de decir "vendé", se revisa TODO (no una sola regla) ---
        revision = []
        if sug in ("vender_mitad", "vender_todo"):
            op_tk = opinion.get(tk) or {}
            fav, con = op_tk.get("a_favor") or [], op_tk.get("en_contra") or []
            nots = (noticias or {}).get(tk) or []
            n_pos = [n for n in nots if n.get("dir", 0) > 0]
            n_neg = [n for n in nots if n.get("dir", 0) < 0]
            base_tk = tk[:-1] if tk[-1:] in ("D", "C") else tk
            bal = next((e for e in eventos or [] if e.get("tipo") == "balance" and e.get("ticker") in (tk, base_tk)
                        and hoy_s <= e.get("fecha", "") <= sumar_ruedas(hoy, 5).isoformat()), None)
            sigue = tk in (marcados or set())
            r1_ = x.get("rango_1m")
            arriba = round((r1_[1] / precio - 1) * 100, 1) if r1_ else None
            var_d = x.get("variacion")
            puntos = [  # (a favor de VENDER, texto)
                (len(con) > len(fav), f"Analistas: {len(fav)} a favor, {len(con)} en contra" + (f" ({', '.join(con[:3])})" if con else "")),
                (bool(n_neg) and not n_pos, "Noticias: " + ("en contra: «" + (n_neg[0].get("texto") or "")[:80] + "»" if n_neg else
                                                              "a favor: «" + (n_pos[0].get("texto") or "")[:80] + "»" if n_pos else "nada relevante hoy")),
                (bool(bal), f"Balance el {bal['fecha'][8:10]}/{bal['fecha'][5:7]}: puede saltar para cualquier lado" if bal else "Sin balance en los próximos días"),
                (not sigue, "Los anticipadores " + ("lo siguen marcando hoy (todavía ven suba)" if sigue else "ya no lo marcan")),
                (arriba is not None and arriba < 8, f"Recorrido normal que le queda en un mes: +{_m(arriba, 1)}%" if arriba is not None else "Sin datos de recorrido"),
                (devolviendo, f"Ya devolvió más de la mitad de lo que llegó a ganar ({_m(gan_max, 1)}%)" if devolviendo else
                 (f"Está cerca de su máximo desde la compra ({_p(mx)})" if mx else "Precio sin máximo de referencia")),
            ]
            a_vender = sum(1 for v, _ in puntos if v)
            revision = [("✔ " if v else "✖ ") + t for v, t in puntos]
            if a_vender * 2 <= len(puntos) and not devolviendo and sug == "vender_mitad":
                # la mayoría de lo que mira la mesa sigue a favor: no hace falta vender; se protege lo ganado
                lvl = round(max(compra_p or 0, (x.get("objetivo_idea") or 0) * 0.97, (mx or precio) * 0.94), 2) if compra_p else None
                if lvl and lvl < precio:
                    nuevo_stop = lvl
                    if not any(o["accion"] == "subir_stop" for o in ops):
                        ops.insert(1, {"accion": "subir_stop", "nivel": lvl, "texto": f"Subir el stop a {_p(lvl)} (asegurás lo ganado y le das aire)."})
                    else:
                        for o in ops:
                            if o["accion"] == "subir_stop":
                                o.update(nivel=lvl, texto=f"Subir el stop a {_p(lvl)} (asegurás lo ganado y le das aire).")
                    sug = "subir_stop"
                    por_que = (f"Llegó al objetivo, pero revisé todo y solo {a_vender} de {len(puntos)} cosas dicen vender: mantené y subí el stop "
                               f"a {_p(lvl)} para no devolver la ganancia.")
            else:
                por_que = (por_que or "") + f" Revisé todo: {a_vender} de {len(puntos)} cosas dicen vender."
        for o in ops:
            o["sugerida"] = o["accion"] == sug
        # --- qué cambió hoy (contra la última ronda de ayer) ---
        ahora = {"fecha": hoy_s, "vence": vence, "a_favor": sorted((opinion.get(tk) or {}).get("a_favor") or []),
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
            if ay.get("vence") and vence and ay["vence"] != vence:
                cambios.append(f"El plazo cambió: antes hasta el {ay['vence'][8:10]}/{ay['vence'][5:7]}, hoy hasta el {vence[8:10]}/{vence[5:7]}.")
            if ay.get("sugerida") and ay["sugerida"] != sug:
                cambios.append(f"La sugerencia cambió: antes «{NOMBRE_ACCION[ay['sugerida']]}», hoy «{NOMBRE_ACCION[sug]}».")
        if not cambios:
            cambios = ["Sin cambios importantes en la mesa."] if ay else ["Primer día de seguimiento."]
        if sug != "mantener" and avisados.get(tk) != f"{hoy_s}|{sug}":
            urgente = sug in ("vender_todo", "vender_mitad")
            avisos.append({"fecha": hoy_s, "hora": hora, "ticker": f"{tk} ({'VENDER' if urgente else 'decidir'})",
                           "texto": (f"🚨 {tk}: {NOM_URG.get(sug, NOMBRE_ACCION[sug]).upper()} AHORA. " if urgente else f"{tk}: la mesa sugiere «{NOMBRE_ACCION[sug]}». ")
                                    + f"{por_que or ''} Precio {_p(precio)}" + (f", compraste a {_p(compra_p)}" if compra_p else "") + "."
                                    + (" Lo que miré: " + " · ".join(revision) if revision else "")})
            avisados[tk] = f"{hoy_s}|{sug}"
        # el cartel: lo que hay que hacer, en una línea
        fv = (lambda f: f"{f[8:10]}/{f[5:7]}") if vence else None
        resto = (total - dias) if (total is not None and dias is not None) else None
        stop_txt = next((o for o in ops if o["accion"] == "subir_stop"), None)
        if sug == "vender_todo":
            titular, color = ("VENDER HOY · estás devolviendo la ganancia" if devolviendo else "SALIR HOY"), "rojo"
        elif sug == "vender_mitad":
            titular, color = ("VENDER LA MITAD HOY · " + ("estás devolviendo la ganancia" if devolviendo else "llegó al objetivo" if cons.startswith("Tomar") else "")).rstrip(" ·"), "amar"
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
                   "compra_punta": x.get("aviso_spread"), "estructura": (x.get("estructura") or {}).get("frase"), "ahora": ahora, "revision": revision, "vence_base": vence_base, "cambios_plazo": cambios_plazo}
    return out, avisos
