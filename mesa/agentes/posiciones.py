"""Posiciones de 1 a 12 meses (20/11, "probemos y vamos viendo"). Clau: "necesito que agarremos oportunidades".

Por qué existe: la simulación en papel de las operaciones de 2 semanas dio 600 cerradas con 12% ganadoras (los stops
quedaban dentro del ruido y saltaban antes de que la idea funcionara; auditado 20/11). Las ventajas que la historia sí
confirma son de meses, no de semanas. Esta línea propone solo esas, cada una con su prueba:

1. REBOTE EN DÓLARES (acciones argentinas, 3 meses). Cae 30%+ desde el máximo de 3 meses y 15%+ en el mes (en dólares
   CCL). 10 años, 64 acciones: mediana +4,4% (promedio +10,1%, suben 56%) contra -4,4% de cualquier día. Una alarma
   cercana (13%) saltaba antes del rebote 58% de las veces: el riesgo se maneja con el MONTO (que se banque -30%) y la
   alarma va lejos (debajo del mínimo del año o -25%).
2. GRAHAM (CEDEARs, 12 meses). Cumple 5+ de los 7 criterios del inversor defensivo y el precio está debajo de su valor
   según Graham (margen de seguridad). 576 balances 2010-2025: las de 5+ criterios le ganaron al S&P 60 de cada 100 años (+3,3%).

El riesgo se maneja con el tamaño: cantidad = riesgo por operación (1R de la configuración) / distancia a la alarma.
Cada propuesta dice de dónde puede salir la plata (lo que vence pronto en la cartera). Se mide sola en la simulación.
"""
from __future__ import annotations

import bisect
from datetime import date, timedelta

CLAVE_CAND = "posiciones/candidatas"
MAX_DIA = 2
SPREAD_MAX = 1.5
MONTO_MIN = 20_000_000


def _usd(ccl_f: list[str], ccl: dict, f: str, p: float) -> float | None:
    i = bisect.bisect_right(ccl_f, f) - 1
    return p / ccl[ccl_f[i]] if i >= 0 else None


def rebotes(ctx, velas_de, ccl: dict, precio_de) -> list[dict]:
    """Acciones argentinas que hoy cumplen la regla del rebote en dólares."""
    fs = sorted(ccl)
    hoy = ctx.fecha.isoformat()
    out = []
    for tk, t in (ctx.por_simbolo or {}).items():
        if (t or {}).get("grupo") != "acciones":
            continue
        pr = precio_de(tk)
        v = velas_de(tk)
        if not pr or len(v) < 80:
            continue
        s = [u for u in (_usd(fs, ccl, x["fecha"], x["cierre"]) for x in v[-61:] if x.get("cierre")) if u]
        hoy_u = _usd(fs, ccl, hoy, pr)
        if len(s) < 40 or not hoy_u:
            continue
        s.append(hoy_u)
        dd, r20 = hoy_u / max(s[-60:]) - 1, hoy_u / s[-21] - 1
        if dd <= -0.30 and r20 <= -0.15:
            mn = min(x["minimo"] for x in v[-250:] if x.get("minimo"))
            out.append({"ticker": tk, "tipo": "rebote", "dd": round(dd * 100, 1), "r20": round(r20 * 100, 1), "min_1a": mn})
    return out


CLAVE_KOST = "posiciones/kostolany"
# ETFs apalancados: pierden valor solos con la volatilidad; no son para posiciones de meses (20/11)
APALANCADOS = {"TQQQ", "SQQQ", "SPXL", "SPXU", "UPRO", "SOXL", "SOXS", "TNA", "TZA", "LABU", "FAS", "TECL", "NUGT", "UVXY", "SDS", "SSO", "QLD"}


def preparar_kostolany(almacen, cache, hoy: date) -> dict:
    """En el cierre (20/11, Kostolany probado): la fase de PÁNICO del huevo = cae 10%+ en 20 ruedas con volumen 1,5 veces
    o más el normal. A 3 meses: CEDEARs +6,8% típico (suben 64 de cada 100) contra +1,2% de cualquier momento; acciones
    argentinas en dólares +3,9% (55 de cada 100) contra -4,2%. CEDEARs: precio y volumen de EE.UU. (Yahoo);
    acciones argentinas: las velas de la mesa en dólares CCL."""
    from concurrent.futures import ThreadPoolExecutor
    from ..datos import gratis
    pan = (almacen.get("ui/panel") or {}).get("titulos") or {}

    def fase(c, v):
        if len(c) < 61 or not v or sum(v[-60:-20]) <= 0:
            return None
        vr = (sum(v[-20:]) / 20) / (sum(v[-60:-20]) / 40)
        r = c[-1] / c[-21] - 1
        if r < -0.60 or vr > 10:  # más que eso suele ser un cambio de ratio, un agrupamiento o un dato roto (EMBJ, SDA 20/11)
            return None
        return {"r20": round(r * 100, 1), "vol": round(vr, 1)} if r <= -0.10 and vr >= 1.5 else None
    from .ficha_frio import COBERTURAS
    no_va = COBERTURAS | APALANCADOS
    out = []
    ced = [t for t, x in pan.items() if x and len(x) > 4 and x[4] == "cedears" and t.isalpha() and not t.endswith(("D", "C")) and t not in no_va]
    with ThreadPoolExecutor(8) as ex:
        for t, v in zip(ced, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "6mo"), ced)):
            f = fase([x["c"] for x in v], [x.get("v") or 0 for x in v]) if v else None
            if f:
                out.append({"ticker": t, "tipo": "panico", "mercado": "cedears", **f})
    try:
        ccl = gratis.ccl_historico(); fs = sorted(ccl)
        for t, x in pan.items():
            if not x or len(x) < 5 or x[4] != "acciones":
                continue
            v = cache.velas(t)[-61:]
            c = [u for u in (_usd(fs, ccl, y["fecha"], y["cierre"]) for y in v if y.get("cierre")) if u]
            f = fase(c, [y.get("volumen") or 0 for y in v]) if len(c) == len(v) else None
            if f:
                out.append({"ticker": t, "tipo": "panico", "mercado": "acciones", **f})
    except Exception as ex_:
        print(f"[kostolany] acciones: {ex_}")
    res = {"fecha": hoy.isoformat(), "lista": out}
    almacen.put(CLAVE_KOST, res)
    print(f"[kostolany] fase de pánico: {len(out)} papeles")
    return res


def graham(almacen) -> list[dict]:
    t = almacen.get("biblioteca/graham") or {}
    out = []
    for tk, x in t.items():
        ev = x.get("ev") or {}
        if ev.get("cumple", 0) >= 5 and (ev.get("margen_pct") or -1) >= 0:
            out.append({"ticker": tk, "tipo": "graham", "cumple": ev["cumple"], "margen": ev["margen_pct"], "frase": x.get("frase")})
    out = sorted(out, key=lambda c: (-c["cumple"], -c["margen"]))
    # 20/11 (Lynch, probado a 12 meses): caja neta de más de 10% del precio (+15% contra el S&P, sin bancos ni financieras) o crece + PEG<1 + poca deuda (+4,2%)
    from .biblioteca import es_combo_lynch
    ya_ = {c["ticker"] for c in out}
    for tk, x in t.items():
        ly = x.get("lynch") or {}
        if tk in ya_ or not ly or ly.get("categoria") == "ciclica" or (ly.get("deuda_patrimonio") or 0) > 1:
            continue
        if (ly.get("caja_neta_pct") or 0) > 10 or es_combo_lynch(ly):
            out.append({"ticker": tk, "tipo": "lynch", "caja": ly.get("caja_neta_pct"), "peg": ly.get("peg"), "categoria": ly.get("categoria"),
                        "frase": x.get("frase_lynch")})
    return out


def fondeo(almacen, cartera: list[dict], hoy: date) -> str:
    """De dónde puede salir la plata: lo que vence pronto en la cartera (Clau: "no tengo disponible")."""
    try:
        from ..datos.bymaeduca import flujos_guardados
        fl = flujos_guardados(almacen)
        lim = (hoy + timedelta(days=35)).isoformat()
        vence = sorted((str((fl.get(c["ticker"]) or {}).get("vence") or ""), c["ticker"]) for c in cartera)
        pr = [f"{tk} vence el {f[8:10]}/{f[5:7]}" for f, tk in vence if hoy.isoformat() < f <= lim]
        return ("Para la plata: " + "; ".join(pr) + ".") if pr else ""
    except Exception:
        return ""


def proponer(ctx, almacen, hoy: date, cartera: list[dict], previas: list[dict], un_r: float, hora: str, max_monto: float | None = None) -> list[dict]:
    """Hasta 2 por día, una sola vez por día (después de las 11:20, con precios ya asentados)."""
    import hashlib
    from ..nucleo.calc import spread_pct
    from ..nucleo.config import sector
    if not ("11:20" <= (hora or "") < "16:30") or not un_r:
        return []
    hoy_s = hoy.isoformat()
    ya = {p["ticker"] for p in previas if p.get("linea") == "posicion" and p.get("fecha", "") >= (hoy - timedelta(days=20)).isoformat()}
    try:  # 20/11 (Marks): con calma en Argentina, más prudencia (1 por día); con miedo o neutral, hasta 2
        from .ciclo import max_posiciones_dia
        max_dia = max_posiciones_dia(almacen, MAX_DIA)
    except Exception:
        max_dia = MAX_DIA
    if sum(1 for p in previas if p.get("linea") == "posicion" and p.get("fecha") == hoy_s) >= max_dia:
        return []
    cand = almacen.get(CLAVE_CAND) or {}
    if cand.get("fecha") != hoy_s:
        from ..datos import gratis
        ccl = gratis.ccl_historico()
        precio_de = lambda tk: ((ctx.titulo(tk) or {}).get("ultimo"))
        kost = [k for k in ((almacen.get(CLAVE_KOST) or {}).get("lista") or []) if (almacen.get(CLAVE_KOST) or {}).get("fecha", "") >= (hoy - timedelta(days=4)).isoformat()]
        reb = rebotes(ctx, ctx.cache.velas, ccl, precio_de)
        en_reb = {r["ticker"] for r in reb}
        cand = {"fecha": hoy_s, "hora": hora, "lista": reb + [k for k in kost if k["ticker"] not in en_reb] + graham(almacen)[:8]}
        almacen.put(CLAVE_CAND, cand)
    mias = {c["ticker"] for c in cartera}
    out = []
    # cuando cae todo el mercado salen muchas: primero las más operadas (entrar y salir sin mover el precio)
    orden = {"rebote": 0, "panico": 1}
    lista = sorted(cand.get("lista") or [], key=lambda c: (orden.get(c["tipo"], 2), -((ctx.titulo(c["ticker"]) or {}).get("monto") or 0)))
    for c in lista:
        if len(out) + sum(1 for p in previas if p.get("linea") == "posicion" and p.get("fecha") == hoy_s) >= max_dia:
            break
        tk = c["ticker"]
        t = ctx.titulo(tk) or {}
        pr = t.get("ultimo")
        if tk in ya or not pr:
            continue
        sp = spread_pct(t, hora)
        if (sp is not None and sp > SPREAD_MAX) or ((t.get("monto") or 0) < MONTO_MIN and t.get("grupo") == "acciones"):
            continue  # 19/11 (GCLA): con mucha diferencia entre puntas o poco volumen, la ventaja se la come la entrada
        entrada = float(t.get("venta") or pr) if sp is not None else float(pr)
        if c["tipo"] == "rebote":
            # alarma lejos: debajo del mínimo del año si eso queda entre -12% y -25%; si no (ya está en el mínimo o muy
            # arriba), -25%. Nunca pegada: el 58% de las veces una alarma al 13% saltaba antes del rebote (20/11).
            m_ = c["min_1a"] * 0.98
            stop = round(m_ if entrada * 0.75 <= m_ <= entrada * 0.88 else entrada * 0.75, 2)
            meses, objetivo = 3, round(entrada * 1.25, 2)
            por_que = (f"📅 Posición de 3 meses (rebote en dólares): cayó {abs(c['dd']):.0f}% en dólares desde su máximo de 3 meses y "
                       f"{abs(c['r20']):.0f}% en el último mes. En 10 años, con 64 acciones argentinas, después de caídas así rindió a 3 meses "
                       f"+4,4% típico (+10% promedio) y subió 56 de cada 100 veces, contra -4,4% de un día cualquiera. Puede seguir cayendo "
                       f"antes de rebotar: por eso la alarma va lejos y el monto es chico.")
        elif c["tipo"] == "panico":
            stop = round(entrada * 0.75, 2)
            meses, objetivo = 3, round(entrada * 1.20, 2)
            ev_ = ("en CEDEARs, a 3 meses +6,8% típico y subieron 64 de cada 100 veces, contra +1,2% de cualquier momento"
                   if c.get("mercado") == "cedears" else
                   "en acciones argentinas (en dólares), a 3 meses +3,9% típico y subieron 55 de cada 100, contra -4,2% de cualquier momento")
            por_que = (f"📅 Posición de 3 meses (pánico de Kostolany): cayó {abs(c['r20']):.0f}% en un mes con {str(c['vol']).replace('.', ',')} veces "
                       f"su volumen normal: los que tiemblan están vendiendo. En 10 años, después de un pánico así, {ev_}. "
                       "Puede seguir cayendo antes de rebotar: alarma lejos y monto chico.")
        elif c["tipo"] == "lynch":
            stop = round(entrada * 0.75, 2)
            meses, objetivo = 12, round(entrada * 1.30, 2)
            por_que = ("📅 Posición de 12 meses (Lynch): "
                       + (f"tiene caja neta por {str(c['caja']).replace('.', ',')}% de su precio: en 2009-2025 las empresas así le ganaron al S&P 500 69 de cada 100 años (+15%). "
                          if (c.get("caja") or 0) > 10 else
                          f"crece, está barata para lo que crece (PEG {str(c['peg']).replace('.', ',')}) y debe poco: en 2009-2025 le ganaron al S&P 500 56 de cada 100 años (+4,2%). "))
        else:
            stop = round(entrada * 0.75, 2)
            meses, objetivo = 12, round(entrada * 1.30, 2)
            por_que = (f"📅 Posición de 12 meses (Graham): cumple {c['cumple']} de 7 criterios del inversor defensivo y el precio está "
                       f"{c['margen']}% debajo de lo que valdría según su fórmula (margen de seguridad). En 2010-2025, las que cumplían 5 o más "
                       f"le ganaron al S&P 500 60 de cada 100 años (+3,3%).")
        if c["tipo"] == "rebote" and tk in mias:
            por_que += " Ya tenés este papel: esto sería sumar."
        riesgo_u = entrada - stop
        cant = int(un_r / riesgo_u) if riesgo_u > 0 else None
        # 20/11 (Marks, Lo más importante): las más movedizas no rinden más, solo duelen más (CEDEARs 10 años: peor caída
        # típica en un año -44% contra -17% de las tranquilas; pierden 30%+ en el año 22 de cada 100 contra 2). Mitad de monto.
        try:
            import numpy as _np
            cs_ = [x["cierre"] for x in ctx.cache.velas(tk)[-251:] if x.get("cierre")]
            vol = float(_np.std(_np.diff(_np.log(cs_))) * _np.sqrt(250)) if len(cs_) > 120 else None
        except Exception:
            vol = None
        if vol and vol > 0.60 and cant:
            cant = max(1, cant // 2)
            por_que += (f" Ojo: se mueve mucho ({vol * 100:.0f}% anual). Según Marks y la historia, las más movedizas no rinden más,"
                        " solo duelen más: la cantidad sugerida va a la mitad.")
        if cant and max_monto and cant * entrada > max_monto:
            cant = int(max_monto / entrada)  # tope por posición (usuario/capital tope_posicion_pct; 25% desde el 20/11)
        f_ = fondeo(almacen, cartera, hoy)
        plan = {"ticker": tk, "lado": "compra", "entrada": round(entrada, 2), "stop": stop, "objetivo": objetivo, "tamano_r": 1.0,
                "vence": (hoy + timedelta(days=30 * meses)).isoformat(), "riesgo_pct": round(riesgo_u / entrada * 100, 1),
                "recompensa_pct": round((objetivo / entrada - 1) * 100, 1)}
        out.append({"id": hashlib.sha1(f"pos{hoy_s}{tk}".encode()).hexdigest()[:10], "ticker": tk, "sector": sector(tk),
                    "linea": "posicion", "tipo_posicion": c["tipo"], "meses": meses, "plan": plan, "fecha": hoy_s, "hora": hora,
                    "decision": "pendiente", "precio_al_proponer": pr, "cantidad_sugerida": cant,
                    "monto_sugerido": round(cant * entrada) if cant else None, "confianza": "media",
                    "resumen_jefe": por_que + (f" {f_}" if f_ else "") + " La alarma escalonada deja correr la ganancia.",
                    "senales": [{"agente": "posiciones", "direccion": 1, "fuerza": 0.6, "texto": por_que}],
                    "riesgo": {"ok": True, "tamano_r": 1.0, "motivos": [], "avisos": [f"Diferencia entre puntas {sp:.1f}%." if sp else ""]},
                    "seguimiento": {"estado": "pendiente"}})
    return out
