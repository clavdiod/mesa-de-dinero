"""Una ronda de la mesa: datos → 13 agentes → debate → Riesgo → Jefe → registro y avisos.

Uso:  python -m mesa.ronda            (decide sola si le toca correr según hora y presupuesto)
      python -m mesa.ronda --forzar   (corre igual, p. ej. botón 'Analizar ahora')
      python -m mesa.ronda --simular  (sin IOL: usa tests/fixtures, para probar)
"""
from __future__ import annotations

import argparse
import os
import hashlib
import json
from datetime import date, timedelta

import yaml

from .agentes import adr, analistas, anticipo, con_ia, cripto, economista, panico, radar, informes as informes_mod, oportunidades, riesgo, seguimiento, supervisor, wallstreet
from .datos import gratis
from .datos import eventos as eventos_mod
from .datos.cache import CacheHistorico
from .datos.consumo import Consumo, PresupuestoAgotado
from .nucleo import push
from .nucleo.almacen import almacen_por_defecto
from .nucleo.config import RAIZ, config, sector
from .nucleo.contexto import Contexto
from .nucleo.ia import IA
from .nucleo.modelos import Senal
from .nucleo.registro import Registro
from .nucleo.simulacion import Simulador
from .nucleo import combinador
from .nucleo import calc
from .nucleo.reloj import ahora, en_horario, es_dia_habil, toca_correr


def _eventos() -> list[dict]:
    with open(RAIZ / "config" / "eventos.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def cargar_paneles(iol, consumo: Consumo, almacen, simular: bool) -> dict[str, list[dict]]:
    if simular:
        return json.loads((RAIZ / "tests" / "fixtures" / "paneles.json").read_text(encoding="utf-8"))
    nombres = almacen.get("iol/paneles") or {}   # nombres reales descubiertos por scripts/probar_iol.py
    out: dict[str, list[dict]] = {}
    for p in config()["iol"]["paneles"]:
        clave = f"{p['instrumento']}|{p['panel']}"
        inst, pan = nombres.get(clave, (p["instrumento"], p["panel"]))
        if not consumo.puede_consultar(1):
            break
        try:
            out.setdefault(p["grupo"], []).extend(iol.panel(inst, pan))
        except PresupuestoAgotado:
            break
        except Exception as e:
            print(f"[panel] {clave}: {e}")
    for grupo in ("ons", "letras"):  # gratis, no gastan cupo de IOL
        if not out.get(grupo):
            out[grupo] = gratis.data912(grupo)
    return out


def refrescar_puntas(ctx: Contexto, iol, consumo: Consumo, tickers: list[str]) -> None:
    """Puntas detalladas solo para Mi lista y posiciones abiertas, con tope por ronda."""
    tope = config()["iol"]["max_puntas_por_ronda"]
    for tk in tickers[:tope]:
        if not consumo.puede_consultar(1):
            return
        try:
            t = iol.cotizacion(tk, plazo=config()["mercado"]["plazo"])
            base = ctx.por_simbolo.get(tk, {})
            ctx.por_simbolo[tk] = {**base, **{k: v for k, v in t.items() if v not in (None, [])}}
        except Exception as e:
            print(f"[puntas] {tk}: {e}")


def _calendario(almacen, ctx, hoy, ops, abiertas, cartera, simular: bool = False) -> list[dict]:
    """Eventos de los próximos 45 días que importan: los de mis activos, oportunidades y los CEDEARs más operados."""
    try:
        base = lambda t: t[:-1] if t.endswith(("D", "C")) and ctx.titulo(t[:-1]) else t
        mios = {base(t) for t in ctx.tickers_lista() + list(abiertas) + [c.get("ticker", "").upper() for c in cartera]}
        mios |= {o["ticker"] for l in (ops or {}).values() for o in l}
        mios |= set((almacen.get("usuario/ons") or {}).keys())
        top = sorted((t for t in ctx.grupo("cedears") if t.get("monto")), key=lambda t: -t["monto"])[:30]
        mios |= {t["simbolo"] for t in top if t.get("simbolo")}
        if not simular:
            _lic = eventos_mod.actualizar_licitaciones(almacen, hoy, ctx.hora or "")
            ctx.extra["licitaciones_noticias"] = _lic.get("noticias")
            ctx.extra["licitaciones_avisos"] = _lic.get("avisos")
        ev = eventos_mod.armar(almacen, hoy, 45, mios)
        for e in ev:
            if e.get("fuente") == "mae" and e.get("tipo") == "cobro":
                continue  # el "mío" de los pagos de MAE se decide por emisor (en armar)
            e["mio"] = e.get("ticker") in mios and e.get("ticker") not in {t["simbolo"] for t in top} or e.get("tipo") in ("macro", "licitacion")
        # todo lo mío primero; del resto (pagos de ONs de otros emisores, etc.) hasta completar 140
        mios_ev = [e for e in ev if e.get("mio") or e.get("tipo") in ("macro", "licitacion")]
        otros = [e for e in ev if e not in mios_ev][: max(0, 140 - len(mios_ev))]
        return sorted(mios_ev + otros, key=lambda e: (e["fecha"], e.get("tipo", "")))
    except Exception as ex:
        print(f"[calendario] {ex}")
        return []


def _aprendizajes() -> list[dict]:
    try:
        return yaml.safe_load((RAIZ / "config" / "aprendizajes.yaml").read_text(encoding="utf-8")) or []
    except Exception:
        return []


def puntaje_ticker(senales: list[Senal], reg: Registro, ctx: Contexto | None = None) -> float:
    """Suma ponderada de las señales. El Economista "enseña": según el contexto macro, a las señales de los
    demás que van a favor del régimen se les cree más y a las que van en contra, menos."""
    reg_eco = (ctx.extra.get("regimen") if ctx else None)
    tot = 0.0
    for s in senales:
        if s.direccion:
            m = economista.multiplicador(reg_eco, ctx, s.ticker, s.direccion) if s.agente != "economista" else 1.0
            if ctx and s.agente != "wallstreet":
                m *= wallstreet.multiplicador(ctx.extra.get("wallstreet"), (ctx.titulo(s.ticker) or {}).get("grupo"), s.direccion)
            if ctx and s.agente != "cripto" and ctx.extra.get("cripto"):
                m *= cripto.multiplicador(ctx.extra["cripto"].get("btc"), ctx.extra["cripto"].get("ens") or {},
                                          (ctx.titulo(s.ticker) or {}).get("grupo"), s.direccion)
            if s.agente == "ministro" and (s.datos or {}).get("probada") and ctx and \
                    (ctx.titulo(s.ticker) or {}).get("grupo") in MINISTRO_DOMINIO:
                m *= 1.5  # en bonos y pesos el Ministro decide: su voto probado pesa 50% más
            tot += s.direccion * s.fuerza * reg.peso(s.agente, s.fuerza) * m
    return round(tot, 3)


# terreno del Ministro: bonos soberanos, letras y ONs (donde la política económica manda)
MINISTRO_DOMINIO = {"soberanos", "letras", "bonos", "ons"}


def _senales_ws(ctx, ws_datos: dict, tickers: list[str]) -> list[Senal]:
    """Opinión del Estratega de Wall Street sobre los CEDEARs que la mesa está mirando."""
    cl = ctx.extra.get("wallstreet")
    if not cl or not ws_datos.get("precios"):
        return []
    ced = [t for t in dict.fromkeys(tickers) if (ctx.titulo(t) or {}).get("grupo") == "cedears"]
    lim = (ctx.fecha + timedelta(days=4)).isoformat()
    bal = {e.get("ticker") for e in ctx.eventos if e.get("tipo") == "balance" and ctx.fecha.isoformat() <= e.get("fecha", "") <= lim}
    try:
        return wallstreet.senales_en(ws_datos["precios"], cl, ctx.fecha.isoformat(), ced, bal)
    except Exception as ex:
        print(f"[wallstreet] {ex}")
        return []


def _ccl_ayer(almacen, hoy):
    ccl = ((almacen.get("macro/series") or {}).get("series") or {}).get("ccl") or {}
    return next((v for f, v in sorted(ccl.items(), reverse=True) if f < hoy.isoformat()), None), ccl


def _radar_detectar(ctx, almacen, hoy, ya) -> list[dict]:
    try:
        ccl_ay, _ = _ccl_ayer(almacen, hoy)
        vivo = {a: gratis.yahoo_vivo(a) for a in set(adr.ADRS.values())}
        ctx.extra["adr_vivo"] = vivo
        ccl_now = (ctx.dolares.get("contadoconliqui") or {}).get("venta")
        fo = adr.foto(ctx, vivo, ccl_now)
        brechas = {loc: adr.brecha_vivo(f, ccl_now, ccl_ay) for loc, f in fo["filas"].items()}
        alertas = radar.detectar(ctx, ya.hour * 60 + ya.minute, brechas, ctx.riesgo_pais_ayer, ccl_ay)
        # --- Anticipador: CEDEARs que todavía no copiaron lo que su acción ya hizo en Nueva York (incluye pre-market) ---
        minuto = ya.hour * 60 + ya.minute
        ced = sorted((t for t in ctx.grupo("cedears") if t.get("simbolo") and not (t["simbolo"][-1:] in ("D", "C") and ctx.titulo(t["simbolo"][:-1]))),
                     key=lambda t: -(t.get("monto") or 0))
        universo = [t["simbolo"] for t in ced[:80]] + [x for x in ctx.tickers_lista() if (ctx.titulo(x) or {}).get("grupo") == "cedears"]
        vivo_us = gratis.yahoo_varios(universo, prepost=True)
        atr = anticipo.atrasos(ctx, vivo_us, ccl_now, ccl_ay, minuto)
        ctx.extra["anticipos"] = atr
        ctx.extra["anticipo_diag"] = {"universo": len(universo), "con_precio_ny": len(vivo_us),
                                      "mayor_atraso": max((abs(x["atraso"]) for x in anticipo.atrasos(ctx, vivo_us, ccl_now, ccl_ay, minuto, 0)), default=None)}
        # --- MAE contra BYMA: mismo bono/ON, distinto precio (gratis, una consulta por ronda) ---
        try:
            from .agentes import mae as _mae
            if 11 * 60 <= minuto <= 17 * 60 + 15:
                tit = {tk: t for tk, t in ctx.por_simbolo.items() if t.get("grupo") in _mae.GRUPOS_RF}
                pares = _mae.comparar(tit, gratis.mae_panel_rf())
                ctx.extra["mae"] = {"hora": ctx.hora, "resumen": _mae.resumen(pares),
                                    "pares": [p for p in pares if p["liquido"]][:25], "comparados": len(pares)}
                ya_tk = {a["ticker"] for a in alertas}
                alertas += [a for a in _mae.alertas(pares) if a["ticker"] not in ya_tk]
        except Exception as ex:
            print(f"[mae] {ex}")
        ya_alertados = {a["ticker"] for a in alertas}
        for a in atr:
            if a["ticker"] in ya_alertados:
                continue
            cuando = "antes de que abra BYMA" if a["antes_de_abrir"] else "en vivo"
            alertas.append({"tipo": "anticipo", "tipos": ["anticipo"], "ticker": a["ticker"], "grupo": "cedears", "valor": a["atraso"],
                            "severidad": a["severidad"],
                            "texto": f"⏩ {a['ticker']}: en Nueva York va {a['us']:+.1f}% ({cuando}); el CEDEAR debería {'subir' if a['atraso'] > 0 else 'bajar'} "
                                     f"{abs(a['atraso']):.1f}% más para acomodarse."})
        # ADRs antes de que abra BYMA: la acción local todavía no operó, todo lo que hizo el ADR es anticipo
        if minuto < 11 * 60:
            for loc, b in brechas.items():
                if b is not None and abs(b) >= 2 and loc not in ya_alertados:
                    alertas.append({"tipo": "anticipo", "tipos": ["anticipo"], "ticker": loc, "grupo": "acciones", "valor": b,
                                    "severidad": "alta" if abs(b) >= 4 else "media",
                                    "texto": f"⏩ {loc}: su ADR en Nueva York va {b:+.1f}% antes de que abra BYMA: debería abrir {'arriba' if b > 0 else 'abajo'}."})
        # registro del día para la estadística propia (precio de referencia = primer precio operable en BYMA)
        reg_a = almacen.get(f"anticipo/{hoy.isoformat()}") or {}
        for a in atr:
            r = reg_a.setdefault(a["ticker"], {"hora": ctx.hora, "atraso": a["atraso"], "ref": None})
            if r["ref"] is None and minuto >= 11 * 60 + 5:
                r["ref"] = (ctx.titulo(a["ticker"]) or {}).get("ultimo")
        for tk, r in reg_a.items():  # los que se marcaron antes de abrir toman referencia en la primera ronda con BYMA abierto
            if r["ref"] is None and minuto >= 11 * 60 + 5:
                r["ref"] = (ctx.titulo(tk) or {}).get("ultimo")
        if reg_a:
            almacen.put(f"anticipo/{hoy.isoformat()}", reg_a)
        return sorted(alertas, key=lambda a: (a["severidad"] != "alta", a["tipo"] != "anticipo", -abs(a["valor"])))
    except Exception as ex:
        print(f"[radar] {ex}")
        return []


def _radar_investigar(ctx, almacen, hoy, alertas: list[dict], por_ticker: dict) -> tuple[list[dict], list[dict]]:
    """Investiga cada alerta (máx. 10) y devuelve (investigaciones, avisos para el celular de las graves y nuevas)."""
    from .nucleo.config import emisores
    nombres = {"tecnico": "Técnico", "historiador": "Historiador", "fuerza_relativa": "Fuerza relativa", "volumen_flujo": "Volumen y flujo",
               "economista": "Economista", "wallstreet": "Wall Street", "cripto": "Cripto", "adr": "Noche de Nueva York", "panico": "Comprador de pánico",
               "mundo": "Corresponsal (mundo)", "ministro": "Ministro (política económica)", "ganadores": "Cazador de ganadores", "profesionales": "Herramientas de Wall Street", "combinaciones": "Combinaciones (historia)", "anticipador_arg": "Anticipador ARG", "anticipador_mundo": "Anticipador Mundo", "acciones": "Acciones", "cedears": "CEDEARs", "soberanos": "Soberanos", "ons": "ONs", "macro_dolar": "Macro / dólar",
               "noticias": "Noticias", "hechos_emisor": "Hechos del emisor", "calificadoras": "Calificadoras",
               "oportunidades_corto": "Oportunidades (corto)", "oportunidades_mediano": "Oportunidades (mediano)"}
    cache_n = almacen.get(f"radar/noticias/{hoy.isoformat()}") or {}
    busquedas = 0
    out = []
    for a in alertas[:10]:
        tk = a["ticker"]
        em = emisores().get(tk[:-1] if tk.endswith("D") and tk[:-1] in emisores() else tk) or {}
        clave = (em.get("clave") or em.get("nombre") or "").lower()
        notis = [n for n in ctx.noticias if clave and clave in n.get("titulo", "").lower()]
        if not notis and a["grupo"] != "macro" and a["severidad"] == "alta" and busquedas < 3:
            if tk not in cache_n:
                q = em.get("nombre") or tk
                cache_n[tk] = [{"titulo": n["titulo"], "link": n.get("link")} for n in gratis.buscar_noticias(f'"{q}"', horas=48, max_items=5)]
                busquedas += 1
            notis = cache_n.get(tk) or []
        out.append(radar.investigar(a, ctx, por_ticker, notis, nombres))
    if busquedas:
        almacen.put(f"radar/noticias/{hoy.isoformat()}", cache_n)
    # historial del día (primera vez que se vio cada alerta) y avisos de las graves nuevas
    hist = almacen.get(f"radar/{hoy.isoformat()}") or {}
    avisos = []
    for r in out:
        k = r["ticker"]
        if k not in hist:
            hist[k] = {"primera": ctx.hora, "texto": r["texto"], "severidad": r["severidad"]}
            if r["severidad"] == "alta":
                avisos.append({"fecha": hoy.isoformat(), "hora": ctx.hora, "ticker": f"{k} (radar)",
                               "texto": f"📡 {r['texto']} {r['conclusion']}"})
        r["primera"] = hist[k]["primera"]
    almacen.put(f"radar/{hoy.isoformat()}", hist)
    return out, avisos


def _senales_mundo(ctx, almacen, hoy, minuto: int, refrescar: bool, simular: bool) -> list[Senal]:
    """Corresponsal: noticias del mundo y de empresas. Lee los portales cada 30 minutos (gratis); en el resto de
    las rondas usa lo último guardado. Lleva su propia estadística por tema para aprender qué titulares anticipan."""
    if simular:
        return []
    try:
        from .agentes import mundo
        from .nucleo.config import emisores
        guardado = almacen.get("mundo/ultimo") or {}
        if refrescar or guardado.get("fecha") != hoy.isoformat():
            tit = mundo.leer()
            temas = mundo.detectar_temas(tit)
            conteos = mundo.marcar_novedad(temas, guardado.get("conteos") or {}, hoy.isoformat())
            emp = mundo.detectar_empresas(tit, mundo.claves_empresas(emisores()))
            guardado = {"fecha": hoy.isoformat(), "hora": ctx.hora, "titulares": len(tit), "temas": temas, "empresas": emp,
                        "conteos": conteos}
            almacen.put("mundo/ultimo", guardado)
        existe = lambda tk: ctx.titulo(tk) is not None
        stats = almacen.get("mundo/stats") or {}
        sens = mundo.senales(guardado.get("temas") or [], guardado.get("empresas") or [], existe, stats)
        ctx.extra["mundo_senales"] = sens
        ctx.extra["mundo"] = {**{k: v for k, v in guardado.items() if k != "conteos"}, "stats": stats}
        ctx.extra["mundo_alertas"] = mundo.alertas_radar(guardado.get("temas") or [], guardado.get("empresas") or [], existe)
        if minuto >= 11 * 60 + 5:  # anotación con precio de BYMA abierto, para la estadística propia
            log = almacen.get("mundo/log") or []
            if mundo.anotar(log, sens, lambda tk: (ctx.titulo(tk) or {}).get("ultimo"), hoy.isoformat()):
                almacen.put("mundo/log", log[-1500:])
        return sens
    except Exception as ex:
        print(f"[mundo] {ex}")
        return []


def _noticias_papeles(ctx, almacen, hoy, tks: list[str], simular: bool) -> list[Senal]:
    """Corresponsal en el debate: busca las noticias de cada papel que se debate (máx. 6 búsquedas por ronda,
    cada papel se vuelve a buscar a las 2 horas). Gratis: Google Noticias + nombre de la empresa en Yahoo."""
    if simular or not tks:
        return []
    try:
        from .agentes import mundo
        from .nucleo.config import emisores, ticker_base
        cache = almacen.get("mundo/papeles") or {}
        if cache.get("fecha") != hoy.isoformat():
            cache = {"fecha": hoy.isoformat(), "papeles": {}}
        nombres = almacen.get("mundo/nombres") or {}
        ahora_min = int(ctx.hora[:2]) * 60 + int(ctx.hora[3:5]) if ctx.hora else 0
        busquedas, cambio_n = 0, False
        out = []
        for tk in tks:
            t = ctx.titulo(tk) or {}
            base = ticker_base(tk)
            if t.get("grupo") == "cedears" and tk[-1:] in ("D", "C") and ctx.titulo(tk[:-1]):
                base = tk[:-1]
            if t.get("grupo") not in ("acciones", "cedears", "ons"):
                continue
            info = cache["papeles"].get(base)
            vieja = not info or ahora_min - info.get("minuto", 0) >= 120
            if vieja and busquedas < 6:
                local = t.get("grupo") in ("acciones", "ons") or base in emisores()
                nombre = (emisores().get(base) or {}).get("nombre") or nombres.get(base)
                if not nombre and not local:
                    nombre = mundo.nombre_yahoo(base)
                    if nombre:
                        nombres[base], cambio_n = nombre, True
                info = {**mundo.noticias_papel(base, nombre, local), "minuto": ahora_min, "hora": ctx.hora}
                cache["papeles"][base] = info
                busquedas += 1
            if info:
                s = mundo.senal_papel(base, info, almacen.get("mundo/stats") or {})
                out.append(Senal(s.agente, tk, s.direccion, s.fuerza, s.texto, s.datos, evaluable=s.evaluable))
        if busquedas:
            almacen.put("mundo/papeles", cache)
        if cambio_n:
            almacen.put("mundo/nombres", nombres)
        return out
    except Exception as ex:
        print(f"[mundo papeles] {ex}")
        return []


def _senales_ministro(ctx, almacen, hoy, simular: bool) -> list[Senal]:
    """El Ministro: reservas, compras del BCRA, tasa real, inflación, dólar y pagos de deuda (API del BCRA, gratis).
    Las series se bajan una vez por día; los titulares del Ministro cada 2 horas."""
    if simular:
        return []
    try:
        from .agentes import ministro
        guard = almacen.get("ministro/series") or {}
        if guard.get("fecha") != hoy.isoformat():
            ser = ministro.bajar_series(hoy - timedelta(days=400), hoy)
            if sum(len(v) for v in ser.values()) > 100:
                guard = {"fecha": hoy.isoformat(), "series": ser}
                almacen.put("ministro/series", guard)
        series = guard.get("series") or {}
        f = ministro.foto(series, hoy.isoformat())
        prueba = almacen.get("ministro/prueba") or {}
        notis = almacen.get("ministro/noticias") or {}
        minuto = int(ctx.hora[:2]) * 60 + int(ctx.hora[3:5]) if ctx.hora else 0
        if notis.get("fecha") != hoy.isoformat() or minuto - notis.get("minuto", 0) >= 120:
            tit = gratis.buscar_noticias("Caputo ministro de Economía", horas=48, max_items=8)
            tes = gratis.buscar_noticias("licitación del Tesoro rollover", horas=168, max_items=8)
            notis = {"fecha": hoy.isoformat(), "minuto": minuto, "titulares": [{"titulo": n["titulo"], "link": n.get("link")} for n in tit[:6]],
                     "rollover": ministro.rollover(tes)}
            almacen.put("ministro/noticias", notis)
        f["rollover"] = notis.get("rollover")
        ctx.extra["ministro"] = {**ministro.lectura(f, prueba.get("activas")), "titulares": notis.get("titulares") or [],
                                 "prueba": {k: {"casos": v["casos"], "acierto": round(v["aciertos"] / v["casos"] * 100, 1),
                                                "promedio": round(v["suma_ret"] / v["casos"], 2), "activa": (prueba.get("activas") or {}).get(k)}
                                            for k, v in (prueba.get("stats") or {}).items() if v.get("casos")}}
        # mira tu cartera: una opinión por papel (y voto cuando hay una regla probada detrás)
        ons_u = ctx.extra.get("ons_usuario") or {}
        desc = lambda tk: (ons_u.get(tk) or {}).get("emisor") or (ctx.titulo(tk) or {}).get("descripcion") or ""
        op = ministro.opinion_cartera(f, ctx.cartera or [], lambda tk: (ctx.titulo(tk) or {}).get("grupo"), desc, prueba.get("activas"))
        ctx.extra["ministro"]["cartera"] = op
        sens = ministro.senales(f, lambda tk: ctx.titulo(tk) is not None, prueba.get("activas"))
        ya = {s.ticker for s in sens}
        for o in op:
            if o["ticker"] not in ya:
                sens.append(Senal("ministro", o["ticker"], o["dir"], 0.45 if o["dir"] else 0.0, f"Ministro: {o['texto']}",
                                  {"regla": "cartera", "probada": bool(o["dir"])}, evaluable=bool(o["dir"])))
        return sens
    except Exception as ex:
        print(f"[ministro] {ex}")
        return []


def _senales_panico(ctx, almacen, ws_datos, simular) -> list[Senal]:
    """Comprador de pánico: CEDEARs (dólares, con VIX y S&P) y acciones locales (con el riesgo país)."""
    if simular:
        return []
    try:
        out = []
        if ws_datos.get("precios"):
            ced = [t for t in ws_datos["precios"] if ctx.titulo(t)]
            out += panico.senales_cedears(ws_datos["precios"], ws_datos.get("indices") or {}, ctx.fecha.isoformat(), ced)
        rp = dict(((almacen.get("macro/series") or {}).get("series") or {}).get("riesgo_pais") or {})
        if ctx.riesgo_pais.get("valor"):
            rp[ctx.fecha.isoformat()] = ctx.riesgo_pais["valor"]
        loc = [t for t in (ctx.cache.indice if ctx.cache else {}) if (ctx.titulo(t) or {}).get("grupo") == "acciones"]
        velas = {t: ctx.cache.velas(t) for t in loc}
        out += panico.senales_locales(velas, rp, ctx.fecha.isoformat(), {t: ctx.titulo(t)["ultimo"] for t in loc if ctx.titulo(t).get("ultimo")})
        return out
    except Exception as ex:
        print(f"[panico] {ex}")
        return []


def _senales_adr(ctx, almacen, hoy, ya, simular) -> list[Senal]:
    """Noche de Nueva York: brecha de los ADRs contra la acción local. Los ADRs se bajan una vez por día (Yahoo, gratis)."""
    if simular:
        return []
    try:
        datos = almacen.get("adr/datos") or {}
        if datos.get("fecha") != hoy.isoformat():
            datos = {"fecha": hoy.isoformat(), "adrs": {a: gratis.yahoo(a, "3mo") for a in set(adr.ADRS.values())}}
            almacen.put("adr/datos", datos)
        ccl = ((almacen.get("macro/series") or {}).get("series") or {}).get("ccl") or {}
        sen, tabla = adr.senales_en(ctx, datos, ccl, ya.hour * 60 + ya.minute)
        # histórico propio: una foto por ronda (ADR en vivo, acción local, CCL) para armar estadística
        vivo = ctx.extra.get("adr_vivo") or {a: gratis.yahoo_vivo(a) for a in set(adr.ADRS.values())}
        # mismo CCL que la serie histórica (dolarapi/argentinadatos), para no mezclar fuentes en la brecha
        ccl_now = (ctx.dolares.get("contadoconliqui") or {}).get("venta") or ctx.extra.get("ccl_al30")
        fo = adr.foto(ctx, vivo, ccl_now)
        if fo["filas"]:
            clave = f"adr/fotos/{hoy.isoformat()}"
            fotos = (almacen.get(clave) or []) + [fo]
            almacen.put(clave, fotos[-120:])
        ccl_ant = next((v for f, v in sorted(ccl.items(), reverse=True) if f < hoy.isoformat()), None)
        en_vivo = sorted(({"ticker": loc, "adr": adr.ADRS[loc], "brecha": adr.brecha_vivo(f, ccl_now, ccl_ant)}
                          for loc, f in fo["filas"].items()), key=lambda x: -abs(x["brecha"] or 0))
        ctx.extra["adr_tabla"] = {"hora": ctx.hora, "filas": sorted(tabla, key=lambda x: -abs(x["resta"])) if tabla else [],
                                  "vivo": [x for x in en_vivo if x["brecha"] is not None],
                                  "estadistica": almacen.get("adr/estadistica")}
        return sen
    except Exception as ex:
        print(f"[adr] {ex}")
        return []


def _senales_cripto(ctx, almacen, reg, senales, tickers, simular) -> list[Senal]:
    """Agente Cripto: Bitcoin + dólar cripto. Aprende del agente con mejor historial (mayor voto calibrado)."""
    if simular:
        return []
    try:
        datos = almacen.get("cripto/datos") or {}
        ens = almacen.get("ranking/ensenanza_cripto") or {}
        btc = cripto.lectura_btc(datos.get("btc") or [], ctx.fecha.isoformat())
        dc = (ctx.dolares.get("cripto") or {}).get("venta")
        ccl = ctx.extra.get("ccl_al30") or (ctx.dolares.get("contadoconliqui") or {}).get("venta")
        brecha = (dc / ccl - 1) * 100 if dc and ccl else None
        cal = {a: c.get("factor") or 0 for a, c in (reg.calibracion or {}).items() if a != "cripto"}
        mejor = max(cal, key=cal.get) if cal and max(cal.values()) >= 1 else None
        otras: dict[str, list] = {}
        for s in senales:
            otras.setdefault(s.ticker, []).append(s)
        nombre_mejor = {"wallstreet": "el Estratega de Wall Street"}.get(mejor, mejor)
        cl = cripto.clase(btc, brecha, nombre_mejor, ens)
        ctx.extra["cripto"] = {**cl, "btc": btc, "brecha": round(brecha, 2) if brecha is not None else None, "ens": ens}
        sen = cripto.senales_en(btc, brecha, ctx, [t for t in tickers if ctx.titulo(t)], ens, otras, mejor)
        for s in sen:
            s.texto = s.texto.replace(f" {mejor}, el de", f" {nombre_mejor}, el de") if mejor else s.texto
        return sen
    except Exception as ex:
        print(f"[cripto] {ex}")
        return []


def _series_macro(almacen, hoy) -> dict:
    """Series macro guardadas; se refrescan una vez por día (4 consultas gratis a argentinadatos)."""
    guardado = almacen.get("macro/series") or {}
    if guardado.get("fecha") == hoy.isoformat():
        return guardado.get("series") or {}
    series = gratis.series_macro()
    if any(series.values()):
        almacen.put("macro/series", {"fecha": hoy.isoformat(), "series": series})
        return series
    return guardado.get("series") or {}


def correr(forzar: bool = False, simular: bool = False) -> dict:
    almacen = almacen_por_defecto()
    ya = ahora()
    hoy = ya.date()
    consumo = Consumo(almacen)

    pedido = None if simular else almacen.get("ui/pedido_analisis")
    if pedido and not forzar and es_dia_habil(hoy, almacen) and en_horario(ya):
        forzar = True  # botón "Analizar ahora" de la web
        almacen.put("ui/pedido_analisis", None)
    if not simular and not forzar:
        if not es_dia_habil(hoy, almacen):
            return {"corrio": False, "motivo": "día no hábil"}
        if consumo.solo_cierre():
            return {"corrio": False, "motivo": f"consumo IOL {consumo.pct:.0f}%: solo ronda de cierre"}
        if not toca_correr(ya, consumo.factor_frecuencia()) and not os.environ.get("RESPALDO"):
            return {"corrio": False, "motivo": "no toca en este horario"}

    # Cloudflare KV gratis: ~1.000 escrituras por día. Lo que no es urgente se guarda cada 30 minutos.
    minuto_dia = ya.hour * 60 + ya.minute
    cada30 = bool(forzar or simular or minuto_dia % 30 < 5 or minuto_dia >= 16 * 60 + 55)
    if not simular and not forzar and os.environ.get("RESPALDO"):
        # respaldo de GitHub: solo trabaja si el reloj de Cloudflare no corrió rondas en los últimos 12 minutos
        est = almacen.get("ui/estado") or {}
        if est.get("fecha") == hoy.isoformat() and est.get("hora"):
            hh, mm = (int(x) for x in est["hora"].split(":")[:2])
            if minuto_dia - (hh * 60 + mm) < 12:
                return {"corrio": False, "motivo": "respaldo: el reloj de Cloudflare está funcionando"}
    if not simular and not forzar:
        ultima = {}  # (antes: ronda/ultima; ya no hay rondas duplicadas y ahorraba una escritura por ronda)
        if ultima.get("ts") and ya.timestamp() - ultima["ts"] < 170:
            return {"corrio": False, "motivo": "ya corrió una ronda hace menos de 3 minutos"}
    if not simular:
        pass

    iol = None
    if not simular:
        from .datos.iol import IOL
        iol = IOL(consumo, almacen=almacen)
    cache = CacheHistorico(almacen, iol)
    reg = Registro(almacen)
    estado_ui = almacen.get("ui/estado") or {}
    from .nucleo.almacen import AlmacenDelDia
    dia = dict(estado_ui.get("dia") or {}) if (estado_ui.get("dia") or {}).get("fecha") == hoy.isoformat() else {"fecha": hoy.isoformat()}
    almacen = AlmacenDelDia(almacen, dia)
    lista = almacen.get("usuario/lista") or []
    cartera = almacen.get("usuario/cartera") or []
    params = almacen.get("params/agentes") or {}
    rp_ayer = (almacen.get("ref/riesgo_pais_cierre") or {}).get("valor")

    paneles = cargar_paneles(iol, consumo, almacen, simular)
    if not any(paneles.values()):
        consumo.guardar()
        return {"corrio": False, "motivo": "sin datos de paneles"}

    ctx = Contexto(fecha=hoy, hora=ya.strftime("%H:%M"), paneles=paneles,
                   dolares={} if simular else gratis.dolares(),
                   riesgo_pais={} if simular else gratis.riesgo_pais(), riesgo_pais_ayer=rp_ayer,
                   reservas={} if simular else gratis.bcra_reservas(),
                   noticias=[] if simular else gratis.noticias(),
                   cache=cache, lista=lista, cartera=cartera, params=params, eventos=_eventos() + ((almacen.get("eventos/eeuu") or {}).get("eventos") or []))
    if simular:
        fx = json.loads((RAIZ / "tests" / "fixtures" / "contexto.json").read_text(encoding="utf-8"))
        ctx.dolares, ctx.riesgo_pais, ctx.riesgo_pais_ayer = fx["dolares"], fx["riesgo_pais"], fx["riesgo_pais_ayer"]

    ctx.extra["ons_usuario"] = almacen.get("usuario/ons") or {}
    ctx.extra["licitaciones"] = almacen.get("licitaciones/ultimo") or {}
    abiertas = [p["ticker"] for p in reg.abiertas()]
    # pedidos de la hoja "Debate" de la web (se procesan una vez; máx. 3 por ronda)
    pedido_deb = (almacen.get("ui/pedido_debate") or {}) if not simular else {}
    pedidos = [tk for tk in (pedido_deb.get("tickers") or []) if ctx.titulo(tk)][:3]
    foco = list(dict.fromkeys(pedidos + ctx.tickers_lista() + abiertas))
    if iol is not None:
        refrescar_puntas(ctx, iol, consumo, foco)

    ia = IA()
    # --- analistas por reglas ---
    senales: list[Senal] = []
    senales += analistas.macro_dolar(ctx)
    # --- Economista: régimen macro (riesgo país, dólar, brecha, tasa real) que guía al resto ---
    try:
        series_m = {} if simular else _series_macro(almacen, hoy)
        fx = economista.foto(series_m, hoy, ctx.riesgo_pais.get("valor"), ctx.extra.get("ccl_al30"), ctx.extra.get("caucion_tna"))
        ctx.extra["regimen"] = economista.regimen(fx)
        activa, motivo = economista.ensenanza_activa(almacen.get("ranking/ensenanza") or {})
        ctx.extra["regimen"].update(ensenanza_activa=activa, ensenanza_motivo=motivo)
    except Exception as ex:
        print(f"[economista] {ex}")
    # --- Estratega de Wall Street (CEDEARs): clima de EE.UU. con los datos que guarda el cierre ---
    ws_datos = {} if simular else (almacen.get("wallstreet/datos") or {})
    if ws_datos.get("indices"):
        try:
            cl = wallstreet.clima(ws_datos["indices"], hoy.isoformat())
            activa, motivo = wallstreet.ensenanza_activa(almacen.get("ranking/ensenanza_ws") or {})
            cl.update(ensenanza_activa=activa, ensenanza_motivo=motivo, datos_al=ws_datos.get("fecha"))
            if activa == "contrario":  # la lección que respaldan los datos reemplaza a la del manual
                cl["ensena"] = [x for x in cl["ensena"] if not x.startswith("Wall Street en modo")]
                if cl["riesgo"] <= -0.4:
                    cl["ensena"].insert(0, "Hay miedo en Wall Street: en 5 años, comprar CEDEARs con este clima rindió más que con clima comprador. Buen momento para comprar, con tamaño prudente.")
                elif cl["riesgo"] >= 0.5:
                    cl["ensena"].insert(0, "Clima comprador en Wall Street: en 5 años, comprar CEDEARs con este clima rindió menos que comprar con miedo. Ser selectivo: solo lo que tenga tendencia y momentum.")
            ctx.extra["wallstreet"] = cl
        except Exception as ex:
            print(f"[wallstreet] {ex}")
    senales += analistas.acciones(ctx)
    senales += analistas.cedears(ctx)
    senales += analistas.ons(ctx)
    senales += analistas.soberanos(ctx)
    senales += analistas.pesos_tasas(ctx)
    senales += con_ia.noticias(ctx, ia, almacen)
    cal = almacen.get("calificadoras/ultimo") or {}
    if cal.get("fecha") == hoy.isoformat():
        senales += con_ia.senales_calificadoras(ctx, cal)

    # agentes nuevos (usan el historial guardado y el panel de la ronda: no gastan IOL)
    senales += analistas.fuerza_relativa(ctx)
    senales += analistas.volumen_flujo(ctx)

    # Cazador de ganadores (Wall Street): solo votan las estrategias que le ganaron al promedio en 5 años
    if not simular:
        try:
            from .agentes import ganadores as _gan
            lg = almacen.get("ganadores/lista") or {}
            pg = almacen.get("ganadores/prueba") or {}
            ctx.extra["ganadores"] = {"fecha": lg.get("fecha"), "lista": lg.get("lista") or [],
                                      "prueba": {k: {"nombre": v["nombre"], "activa": v["activa"], "plazo": v["plazo"],
                                                     **((v.get("horizontes") or {}).get(str(v["plazo"])) or (v.get("horizontes") or {}).get(v["plazo"]) or {})}
                                                 for k, v in (pg.get("estrategias") or {}).items()},
                                      "base": pg.get("base")}
            senales += _gan.senales(lg.get("lista") or [], pg, lambda tk: ctx.titulo(tk) is not None)
        except Exception as ex:
            print(f"[ganadores] {ex}")
        try:  # herramientas profesionales: consenso de analistas, compras de insiders, sectores líderes
            from .agentes import profesionales as _pro
            lp = almacen.get("profesionales/lista") or {}
            pp = almacen.get("profesionales/prueba") or {}
            ctx.extra["profesionales"] = {"fecha": lp.get("fecha"), "lista": lp.get("lista") or {}, "lideres": lp.get("lideres") or [],
                                          "sectores_3m": lp.get("sectores_3m") or {}, "nombres": lp.get("nombres") or {},
                                          "prueba": {k: {"nombre": v["nombre"], "activa": v["activa"], "plazo": v["plazo"],
                                                         **((v.get("horizontes") or {}).get(str(v["plazo"])) or {})}
                                                     for k, v in (pp.get("herramientas") or {}).items()}}
            senales += _pro.senales(lp.get("lista") or {}, pp, lambda tk: ctx.titulo(tk) is not None)
        except Exception as ex:
            print(f"[profesionales] {ex}")
    # El Ministro: la política económica (reservas, tasa real, dólar, deuda) que mueve bonos, bancos y pesos
    senales += _senales_ministro(ctx, almacen, hoy, simular)
    # Corresponsal: el mundo y las empresas (guerra en el Golfo, Fed, aranceles, rumores, nuevos desarrollos...)
    senales += _senales_mundo(ctx, almacen, hoy, ya.hour * 60 + ya.minute, cada30, simular)

    # candidatos: lo que alguien marcó + Mi lista; con carga de historial una sola vez por ticker
    marcados = [s.ticker for s in senales if s.direccion != 0 and ctx.titulo(s.ticker)]
    # --- Radar: todo lo anormal del mercado entra al análisis de TODOS los analistas en esta ronda ---
    alertas_radar = [] if simular else _radar_detectar(ctx, almacen, hoy, ya)
    alertas_radar += [a for a in ctx.extra.get("mundo_alertas") or [] if a["ticker"] not in {x["ticker"] for x in alertas_radar}]
    radar_tks = [a["ticker"] for a in alertas_radar if a["grupo"] != "macro" and ctx.titulo(a["ticker"])][:15]
    candidatos = list(dict.fromkeys(foco + radar_tks + marcados))
    # cargas iniciales de historial: máx. 2 por ronda y 15 por día (cuida el cupo de IOL);
    # primero Mi lista y posiciones abiertas, después lo que marcaron los agentes
    clave_cargas = f"cache/cargas/{hoy.isoformat()}"
    cargas_hoy = int(almacen.get(clave_cargas) or 0)
    restantes_hist = min(2, max(0, 15 - cargas_hoy))
    for tk in candidatos:
        if restantes_hist <= 0:
            break
        if not cache.velas(tk):
            cache.asegurar(tk, 1, None if simular else ctx.titulo(tk))
            restantes_hist -= 1
            cargas_hoy += 1
    almacen.put(clave_cargas, cargas_hoy)
    senales += analistas.tecnico(ctx, candidatos)
    senales += analistas.historiador(ctx, candidatos)

    if ctx.extra.get("regimen"):
        senales += economista.senales(ctx, ctx.extra["regimen"], candidatos)
    senales += anticipo.senales_atraso(ctx.extra.get("anticipos") or [])
    # los tres anticipadores (CEDEARs, Argentina y Mundo): cada uno vota solo si pasó su examen con la historia
    from .agentes import anticipadores as _antic
    fr_debil = {s.ticker for s in senales if s.agente == "fuerza_relativa" and s.direccion < 0 and s.fuerza >= 0.8}
    listas_ant = {}
    for ag_, (clave_, _nom) in _antic.AGENTES.items():
        listas_ant[ag_] = {} if simular else (almacen.get(clave_) or {})
        # Reunión del 22/10: los marcados que además estaban entre los más débiles (Fuerza relativa) siguieron cayendo
        senales += _antic.senales(ag_, listas_ant[ag_], lambda tk: ctx.titulo(tk) is not None, fr_debil)
        for x in listas_ant[ag_].get("lista") or []:
            x["fr_contra"] = x["ticker"] in fr_debil
    # cada idea de los anticipadores con su plan: entrada, stop, objetivo (+5%, lo que se probó), plazo y prioridad
    from .agentes.seguimiento_cartera import sumar_ruedas as _sr
    for ag_, l_ in listas_ant.items():
        items = l_.get("lista") or []
        for x in items:
            try:
                t_ = ctx.titulo(x["ticker"]) or {}
                precio_ = t_.get("ultimo")
                if precio_:
                    vs_ = ctx.cache.velas(x["ticker"]) if ctx.cache else []
                    atr_ = (calc.atr(vs_) or precio_ * 0.03) if len(vs_) >= 15 else precio_ * 0.03
                    # comprar hasta: el precio de ahora con 1% de margen; si hoy ya subió fuerte, un poco abajo (no perseguir)
                    hasta_ = precio_ * (0.995 if (t_.get("variacion") or 0) >= 2.5 else 1.01)
                    # stop: 1,5 veces lo que se mueve normalmente en un día, entre 4% y 10% (para una idea de 5 ruedas)
                    dist_ = min(0.10, max(0.04, 1.5 * atr_ / precio_))
                    x["plan"] = {"entrada": round(hasta_, 2), "precio": precio_, "objetivo": round(precio_ * 1.05, 2),
                                 "stop": round(precio_ * (1 - dist_), 2), "stop_pct": round(-dist_ * 100, 1)}
                base_f = date.fromisoformat(l_.get("fecha") or hoy.isoformat())
                x["vence"] = _sr(base_f, 5).isoformat()  # 5 ruedas desde la lista (lo que se probó)
            except Exception as ex:
                print(f"[plan anticipador] {x.get('ticker')}: {ex}")
        orden = sorted(items, key=lambda y: -(y.get("prob") or 0) * (0.5 if y.get("fr_contra") else 1))
        for k_, x in enumerate(orden, 1):
            x["prioridad"] = k_
    lista_ant = listas_ant["anticipador"]
    ctx.extra["anticipo_lista"] = lista_ant
    ctx.extra["anticipo_listas"] = {k: v for k, v in listas_ant.items() if k != "anticipador" and v.get("activo")}
    # los que todavía no aprobaron el examen: sus ideas se anotan igual en la libreta (en observación, sin votar ni mostrarse
    # en Hoy) para medir si en la vida real funcionan
    ctx.extra["anticipo_listas_obs"] = {k: v for k, v in listas_ant.items() if k != "anticipador" and not v.get("activo") and v.get("lista")}
    senales += _senales_ws(ctx, ws_datos, candidatos + [t for t in ctx.tickers_lista()])
    senales += _senales_cripto(ctx, almacen, reg, senales, candidatos + ctx.tickers_lista() + cripto.CEDEARS_CRIPTO, simular)
    senales += _senales_adr(ctx, almacen, hoy, ya, simular)
    senales += _senales_panico(ctx, almacen, ws_datos, simular)
    por_ticker: dict[str, list[Senal]] = {}
    for s in senales:
        por_ticker.setdefault(s.ticker, []).append(s)
    puntajes = {tk: puntaje_ticker(ss, reg, ctx) for tk, ss in por_ticker.items() if ctx.titulo(tk)}
    preseleccion = [tk for tk, p in sorted(puntajes.items(), key=lambda x: -x[1]) if p >= 0.6][:8]
    preseleccion += [tk for tk in ctx.tickers_lista() if tk not in preseleccion and puntajes.get(tk, 0) > 0]
    preseleccion += [tk for tk in pedidos if tk not in preseleccion]

    # --- hechos del emisor (solo preseleccionados, 1 búsqueda por emisor por día) ---
    hechos = [] if simular else con_ia.hechos_emisor(ctx, ia, preseleccion, almacen)
    senales += hechos
    # --- Corresponsal en el debate: noticias de cada papel que se debate (incluye la lista del Anticipador) ---
    lista_anticip = [x["ticker"] for x in (ctx.extra.get("anticipo_lista") or {}).get("lista") or []][:10]
    lista_anticip += [x["ticker"] for l_ in (ctx.extra.get("anticipo_listas") or {}).values() for x in (l_.get("lista") or [])[:5]]
    tks_notis = list(dict.fromkeys(pedidos + ctx.tickers_lista() + preseleccion + lista_anticip))
    ya_mundo = {s.ticker for s in senales if s.agente == "mundo"}
    for s in _noticias_papeles(ctx, almacen, hoy, tks_notis, simular):
        if s.ticker in ya_mundo and s.direccion == 0:
            continue  # ya opinó por un tema del mundo: el "sin novedades" no agrega
        senales.append(s)
        por_ticker.setdefault(s.ticker, []).append(s)
    vetos = {s.ticker for s in hechos if s.veto}
    # el Ministro frena compras de bonos cuando una regla PROBADA de política económica dice que vienen mal
    vetos |= {s.ticker for s in senales if s.agente == "ministro" and s.direccion < 0 and (s.datos or {}).get("probada")
              and (ctx.titulo(s.ticker) or {}).get("grupo") in MINISTRO_DOMINIO}

    # --- Riesgo ---
    propuestas_hoy = reg.de_hoy(hoy)
    estado = {"abiertas": reg.abiertas(), "propuestas_hoy": propuestas_hoy,
              "perdida_dia_r": reg.resultado_periodo(hoy.isoformat()),
              "perdida_semana_r": reg.resultado_periodo(date.fromordinal(hoy.toordinal() - hoy.weekday()).isoformat())}
    ya_propuestos = {p["ticker"] for p in propuestas_hoy} | set(abiertas)

    # --- oportunidades de corto y mediano (ANTES del Jefe, para que sus señales cuenten en la decisión;
    #     lección del 20/10: TXAR apareció como oportunidad a 690,5 y el Jefe recién lo vio a 715) ---
    ops = oportunidades.detectar(ctx, estado, vetos)
    sen_ops = oportunidades.como_senales(ops)
    # que el Técnico y el Historiador también opinen sobre cada oportunidad (usan el historial guardado, sin IOL)
    extra_tk = [tk for tk in dict.fromkeys(o["ticker"] for l in ops.values() for o in l) if tk not in candidatos]
    sen_extra = analistas.tecnico(ctx, extra_tk) + analistas.historiador(ctx, extra_tk) if extra_tk else []
    if extra_tk and ctx.extra.get("regimen"):
        sen_extra += economista.senales(ctx, ctx.extra["regimen"], extra_tk)
    sen_extra += _senales_ws(ctx, ws_datos, extra_tk)
    senales += sen_ops + sen_extra
    nuevos_pre = []
    for s_ in sen_ops + sen_extra:
        por_ticker.setdefault(s_.ticker, []).append(s_)
    ops = oportunidades.filtrar_por_mesa(ops, por_ticker, vetos, reg.peso)
    aprobadas_tk = {o["ticker"] for l in ops.values() for o in l if o["mesa"]["aprobada"]}
    for tk in {s_.ticker for s_ in sen_ops} & aprobadas_tk:  # solo las que el comité confirma llegan al Jefe
        if ctx.titulo(tk):
            puntajes[tk] = puntaje_ticker(por_ticker[tk], reg, ctx)
            if puntajes[tk] >= 0.6 and tk not in preseleccion:
                preseleccion.append(tk)
                nuevos_pre.append(tk)
    if nuevos_pre and not simular:
        hechos2 = con_ia.hechos_emisor(ctx, ia, nuevos_pre, almacen)
        senales += hechos2
        vetos |= {s_.ticker for s_ in hechos2 if s_.veto}
    evaluados = []
    for tk in preseleccion:
        if tk in ya_propuestos:
            continue
        sh = [s for s in por_ticker.get(tk, [])]
        # el plazo lo marca el agente que más empuja la idea (cada estrategia gana en su plazo)
        aportes = [(s.direccion * s.fuerza * reg.peso(s.agente, s.fuerza), s.agente) for s in sh if s.direccion > 0]
        principal = max(aportes)[1] if aportes else None
        ruedas = riesgo.plazo_de(principal)
        plan = riesgo.armar_plan(ctx, tk, ruedas)
        if not plan:
            continue
        r = riesgo.evaluar(ctx, plan, estado, vetos)
        plan.tamano_r = r["tamano_r"]
        hist = next((s.datos for s in sh if s.agente == "historiador"), None)
        evaluados.append({"id": hashlib.sha1(f"{hoy}{tk}{ctx.hora}".encode()).hexdigest()[:10], "ticker": tk,
                          "sector": sector(tk), "puntaje": puntajes.get(tk, puntaje_ticker(sh, reg, ctx)), "plan": plan.dict(), "riesgo": r,
                          "senales": [s.dict() for s in sh], "historiador": hist,
                          "principal": principal, "ruedas": ruedas})

    cupo = config()["riesgo"]["max_propuestas_dia"] - len(propuestas_hoy)
    # lo que el Jefe ya descartó hoy no se vuelve a debatir salvo que el puntaje haya subido
    descartes = almacen.get(f"jefe/descartes/{hoy.isoformat()}") or {}
    aprobados = [e for e in evaluados if e["riesgo"]["ok"] and e["puntaje"] > descartes.get(e["ticker"], -9)]
    if cupo <= 0:
        aprobados = []
    for e in aprobados[: config()["ia"]["max_candidatos_debate"]]:
        e["debate"] = con_ia.debate(ia, {"ticker": e["ticker"], "plan": e["plan"], "senales": e["senales"],
                                         "hechos": ctx.hechos.get(e["ticker"]), "clima": ctx.extra.get("clima_estado")})
    contexto_txt = (f"Clima {ctx.extra.get('clima_estado')}, riesgo país {ctx.riesgo_pais.get('valor')} "
                    f"(ayer {ctx.riesgo_pais_ayer}), MEP {ctx.extra.get('mep_al30')}, CCL {ctx.extra.get('ccl_al30')}")
    debatidos = [e for e in aprobados if "debate" in e]
    # Jefe que aprendió combinaciones: probabilidad de ganar más que la comisión a 20 ruedas
    modelo = almacen.get("jefe/modelo") or {}
    if modelo.get("activo") and debatidos:
        try:
            ws_i = (ws_datos.get("indices") or {}) if not simular else {}
            btc_s = (almacen.get("cripto/datos") or {}).get("btc") if not simular else None
            rp_s = ((almacen.get("macro/series") or {}).get("series") or {}).get("riesgo_pais")
            cx = combinador.contexto(hoy.isoformat(), btc_s, ws_i.get("^VIX"), rp_s)
            for e in debatidos:
                sen = {}
                for s_ in e["senales"]:
                    if s_.get("direccion") and abs(s_["direccion"] * s_["fuerza"]) > abs(sen.get(s_["agente"], 0)):
                        sen[s_["agente"]] = s_["direccion"] * s_["fuerza"]
                e["prob_modelo"] = combinador.probabilidad(modelo, sen, cx)
            # ya no filtra: es un voto más en el Comité (lo que aprendió de combinaciones parecidas en la historia)
            for e in debatidos:
                pm = e.get("prob_modelo")
                if pm is not None:
                    a_fav = pm >= modelo.get("umbral", 0.5)
                    e["senales"].append({"agente": "combinaciones", "ticker": e["ticker"], "direccion": 1 if a_fav else -1, "fuerza": 0.5,
                                         "texto": f"En la historia, combinaciones de analistas parecidas ganaron más que la comisión a 20 ruedas "
                                                  f"el {pm * 100:.0f}% de las veces ({'a favor' if a_fav else 'no alcanza'})."})
        except Exception as ex:
            print(f"[jefe-modelo] {ex}")
    # protecciones automáticas: frenos fijos que el Jefe no puede discutir (racha de stops, mala semana, penitencia)
    prot = {}
    try:
        from .nucleo import protecciones as _prot
        prot = _prot.evaluar(reg.propuestas, hoy)
        castigados = [e["ticker"] for e in debatidos if e["ticker"] in prot["penitencia"]]
        debatidos = [e for e in debatidos if e["ticker"] not in prot["penitencia"]]
        if prot["pausa"]:
            for e in debatidos:
                descartes[e["ticker"]] = e["puntaje"]
            debatidos = []
        prot["frenados_hoy"] = castigados
    except Exception as ex:
        print(f"[protecciones] {ex}")
    # el Comité: votan los analistas, cada uno con el peso de lo que acertó de verdad (reemplaza al Jefe)
    comite_estado = {}
    try:
        from .agentes import comite as _com
        pesos_v = _com.pesos_vivos([] if simular else (almacen.get("pronosticos/libreta") or []),
                                   {} if simular else (almacen.get("ranking/stats") or {}))
        elegidos, acta = _com.decidir(debatidos, pesos_v, cupo)
        previo_c = {} if simular else (almacen.get("ui/estado") or {}).get("comite") or {}
        actas = [a for a in (previo_c.get("acta") or []) if previo_c.get("fecha") == hoy.isoformat() and a["ticker"] not in {x["ticker"] for x in acta}]
        comite_estado = {"fecha": hoy.isoformat(), "hora": ctx.hora, "pesos": pesos_v, "acta": (acta + actas)[:20]}
        # historial por día (lo de hoy pisa lo de hoy): para entrar por fecha y ver qué se votó
        hist_c = {k: v for k, v in (previo_c.get("historial") or {}).items() if k != hoy.isoformat()}
        if comite_estado["acta"]:
            hist_c[hoy.isoformat()] = [{**{k: a[k] for k in ("ticker", "aprobada", "favor", "contra", "motivo", "ruedas")},
                                        "votos": a["votos"][:5]} for a in comite_estado["acta"]]
        comite_estado["historial"] = dict(sorted(hist_c.items())[-15:])
    except Exception as ex:
        print(f"[comite] {ex}")
        elegidos = con_ia.jefe(ia, debatidos, cupo, contexto_txt)
    ids_elegidos = {e["id"] for e in elegidos}
    for e in debatidos:
        if e["id"] not in ids_elegidos:
            descartes[e["ticker"]] = e["puntaje"]
    if debatidos:
        almacen.put(f"jefe/descartes/{hoy.isoformat()}", descartes)

    # --- expedientes para la hoja Debate (analistas a favor/en contra + opinión del supervisor) ---
    try:
        por_tk: dict[str, list[dict]] = {}
        for s in senales:
            por_tk.setdefault(s.ticker, []).append(s.dict())
        ev_por = {e["ticker"]: e for e in evaluados}
        el_por = {e["ticker"]: e for e in elegidos}
        for e in evaluados:
            if e["ticker"] in pedidos and "debate" not in e:
                e["debate"] = con_ia.debate(ia, {"ticker": e["ticker"], "plan": e["plan"], "senales": e["senales"],
                                                 "hechos": ctx.hechos.get(e["ticker"]), "clima": ctx.extra.get("clima_estado")})
        tks = list(dict.fromkeys(pedidos + preseleccion + ctx.tickers_lista() + list(ya_propuestos) + lista_anticip))
        previos_deb = almacen.get("ui/debates") or {}
        nuevos_deb = {tk: supervisor.expediente(tk, ctx, por_tk.get(tk, []), puntajes.get(tk, 0.0), ev_por.get(tk),
                                                el_por.get(tk), ctx.hora) for tk in tks if ctx.titulo(tk)}
        viejos = {k: v for k, v in previos_deb.items() if k not in nuevos_deb and v.get("fecha") == hoy.isoformat()}
        if cada30 or pedidos or not previos_deb:
            almacen.put("ui/debates", {**dict(list(viejos.items())[:40]), **nuevos_deb})
        if pedidos:
            resto = [t for t in (pedido_deb.get("tickers") or []) if t not in pedidos and ctx.titulo(t)]
            almacen.put("ui/pedido_debate", {"tickers": resto})
    except Exception as ex:  # el debate nunca frena la ronda
        print(f"[debate] {ex}")

    cap = {**config()["capital"], **{k: v for k, v in (almacen.get("usuario/capital") or {}).items() if v}}
    un_r = float(cap.get("monto_ars", 0)) * float(cap.get("riesgo_pct", cap.get("riesgo_por_operacion_pct", 1))) / 100
    nuevas = []
    for e in elegidos:
        pl = e["plan"]
        riesgo_unit = pl["entrada"] - pl["stop"]
        cantidad = int(un_r * pl["tamano_r"] / riesgo_unit) if riesgo_unit > 0 and un_r else None
        nuevas.append({**e, "fecha": hoy.isoformat(), "hora": ctx.hora, "decision": "pendiente",
                       "cantidad_sugerida": cantidad, "seguimiento": {"estado": "pendiente"}})
    reg.nuevas(nuevas)

    # --- simulación en papel: 1.000 nominales de cada oportunidad/propuesta, medida en pesos ---
    try:
        sim = Simulador(almacen)
        sim.actualizar(ctx.por_simbolo, hoy)
        sim.abrir(ops, nuevas, ctx, por_ticker, hoy, ctx.hora)
        sim.guardar(cada30)
    except Exception as ex:  # nunca frena la ronda
        print(f"[simulacion] {ex}")

    # --- libreta de pronósticos: todo lo que la mesa anticipa, controlado solo (¿se dio o no?) ---
    libreta = []
    try:
        from .nucleo import pronosticos as pron
        libreta = [] if simular else (almacen.get("pronosticos/libreta") or [])
        minuto = ya.hour * 60 + ya.minute
        nuevos_p = pron.desde_anticipador(ctx.extra.get("anticipo_lista") or {}, hoy, ctx.hora)
        for ag_, l_ in (ctx.extra.get("anticipo_listas") or {}).items():
            nuevos_p += pron.desde_anticipador(l_, hoy, ctx.hora, origen=ag_)
        for ag_, l_ in (ctx.extra.get("anticipo_listas_obs") or {}).items():
            nuevos_p += [{**x, "observacion": True, "texto": "En observación (todavía no aprobó el examen): " + x["texto"]}
                         for x in pron.desde_anticipador(l_, hoy, ctx.hora, origen=ag_)]
        nuevos_p += pron.desde_anticipos(ctx.extra.get("anticipos") or [], hoy, ctx.hora)
        nuevos_p += pron.desde_ganadores([s for s in senales if s.agente in ("ganadores", "profesionales")], hoy, ctx.hora,
                                         lambda tk: (ctx.titulo(tk) or {}).get("ultimo") if minuto >= 11 * 60 else None)
        nuevos_p += pron.desde_mundo(ctx.extra.get("mundo_senales") or [], hoy, ctx.hora, lambda tk: (ctx.titulo(tk) or {}).get("ultimo") if minuto >= 11 * 60 else None)
        for e in nuevas:
            x = pron.desde_plan("jefe", e["ticker"], e["plan"], hoy, ctx.hora, e.get("resumen_jefe") or "Propuesta del Jefe", e.get("id"))
            nuevos_p += [x] if x else []
        for plazo, lista_o in (ops or {}).items():
            for o in lista_o:
                if (o.get("mesa") or {}).get("aprobada"):
                    x = pron.desde_plan("oportunidad", o["ticker"], o["plan"], hoy, ctx.hora, f"{o.get('setup', '')} ({plazo})")
                    nuevos_p += [x] if x else []
        hubo = sum(pron.anotar(libreta, p) for p in nuevos_p) > 0
        hubo = pron.actualizar(libreta, ctx.por_simbolo, hoy, minuto >= 11 * 60) or hubo
        if minuto >= 17 * 60:
            hubo = pron.cerrar_dia(libreta, hoy) or hubo
        if not simular and (hubo or cada30):
            almacen.put("pronosticos/libreta", libreta)
    except Exception as ex:
        print(f"[pronosticos] {ex}")

    # --- seguimiento de propuestas y señales ---
    reg.actualizar_seguimiento({k: v for k, v in ctx.por_simbolo.items()}, hoy)
    try:  # Radar: investigación de cada alerta con lo que dijo cada analista, noticias y calendario
        radar_inv, avisos_radar = _radar_investigar(ctx, almacen, hoy, alertas_radar, por_ticker) if alertas_radar else ([], [])
    except Exception as ex:
        print(f"[radar] {ex}")
        radar_inv, avisos_radar = [], []
    try:  # seguimiento activo: mantener / subir stop / salir, con aviso si cambia
        alertas_seg = seguimiento.revisar(reg, ctx, por_ticker, lambda ss: puntaje_ticker(ss, reg, ctx))
        opinion_cartera = seguimiento.opinion_cartera(ctx, cartera, por_ticker, lambda ss: puntaje_ticker(ss, reg, ctx))
    except Exception as ex:
        print(f"[seguimiento] {ex}")
        alertas_seg, opinion_cartera = [], {}
    if cada30:  # las señales se registran cada 30 minutos (para el ranking alcanza y cuida las escrituras)
      reg.guardar_senales(hoy, [s.dict() for s in senales],
                        {k: v["ultimo"] for k, v in ctx.por_simbolo.items() if v.get("ultimo")})
    reg.guardar(cada30 or bool(nuevas))
    cache.guardar()

    # --- informe de cada analista (IA solo cada ~30 min para cuidar el costo) ---
    minuto = ya.hour * 60 + ya.minute
    informes = informes_mod.todos(ctx, ia if (forzar or minuto % 30 < 5) else None)
    previos = (estado_ui.get("informes") or {})
    for k, v in informes.items():
        pv = previos.get(k) or {}
        if "lectura_ia" in v:
            v["lectura_ia_hora"] = ctx.hora
        elif pv.get("lectura_ia") or pv.get("lectura_ia_previa"):
            v["lectura_ia_previa"] = pv.get("lectura_ia") or pv.get("lectura_ia_previa")
            v["lectura_ia_hora"] = pv.get("lectura_ia_hora")

    # --- estado para la web ---
    # --- tus cobros: cuánto cobrás, de qué y cuándo (renta y amortización de tu cartera) ---
    mis_cobros, flujos_cartera, avisos_cobro = [], {}, []
    try:
        from .datos import cobros as cob
        tks_cart = [c.get("ticker", "").upper() for c in cartera if c.get("ticker")]
        propios = {**{k: v for k, v in eventos_mod.flujos_bonos().items() if k in tks_cart},
                   **{k: {**v, "fuente": "cargado"} for k, v in (ctx.extra.get("ons_usuario") or {}).items() if k in tks_cart}}
        mae_f = {} if simular else cob.asegurar_flujos(almacen, tks_cart, hoy, ya_tienen=set(propios))
        flujos_cartera = {**mae_f, **propios}
        mis_cobros = cob.proximos(cartera, flujos_cartera, hoy, 60) + cob.vencimientos_lecap(cartera, ctx, hoy, 60)
        mis_cobros.sort(key=lambda c: (c["fecha"], c["ticker"]))
        avisados = almacen.get("cobros/avisados") or {}
        if not simular and avisados.get("fecha") != hoy.isoformat():
            avisos_cobro = [{"fecha": hoy.isoformat(), "hora": ctx.hora, "ticker": "COBROS-" + a["cuando"], "texto": a["texto"]}
                            for a in cob.avisos(mis_cobros, hoy)]
            almacen.put("cobros/avisados", {"fecha": hoy.isoformat(), "n": len(avisos_cobro)})
    except Exception as ex:
        print(f"[cobros] {ex}")

    proy_cartera = {}
    try:  # proyección de cada cosa que tenés: consejo (mantener, sumar, vender), objetivo, piso y rango a 1 mes
        from .agentes import proyeccion
        # precio en EE.UU. del cierre anterior (para pasar el objetivo de los analistas a pesos)
        precio_usa = {} if simular else ((almacen.get("profesionales/lista") or {}).get("precios_usd") or {})
        cons_d = {} if simular else ((almacen.get("profesionales/consensos") or {}).get("datos") or {})
        panel_prev = {} if simular else ((almacen.get("ui/panel") or {}).get("titulos") or {})
        def _tit(tk):  # si en esta ronda no vino el papel, el último precio conocido
            t = ctx.titulo(tk)
            if t and t.get("ultimo"):
                return t
            x = panel_prev.get(tk)
            return {"ultimo": x[0], "grupo": x[4]} if x and x[0] else None
        proy_cartera = proyeccion.para_cartera(cartera, _tit, cache.velas, opinion_cartera, reg.propuestas, cons_d, precio_usa,
                                               (ctx.extra.get("ministro") or {}).get("cartera"), mis_cobros, (prot or {}).get("penitencia"),
                                               {str(x.get("ticker", "")).upper(): (x.get("alertas") or []) + next((c.get("alertas") or [] for c in cartera
                                                if str(c.get("ticker", "")).upper() == str(x.get("ticker", "")).upper()), [])
                                                for x in list(ctx.lista or []) + list(cartera)}, ctx.hora,
                                               [] if simular else (almacen.get("pronosticos/libreta") or []))
    except Exception as ex:
        print(f"[proyeccion] {ex}")

    seg_cartera, avisos_cartera = {}, []
    try:  # seguimiento diario de cada cosa que tenés: plazo, qué cambió hoy y opciones (la decisión es tuya)
        from .agentes import seguimiento_cartera as segc
        foto = {} if simular else (almacen.get("cartera/foto") or {})
        ayer_f = foto if (foto.get("fecha") or "") < hoy.isoformat() else (foto.get("previa") or {})
        avis = {} if simular else (almacen.get("cartera/avisados") or {})
        antes_av = dict(avis)
        seg_cartera, avisos_cartera = segc.armar(cartera, proy_cartera, opinion_cartera, reg.propuestas,
                                                 [] if simular else (almacen.get("pronosticos/libreta") or []),
                                                 ayer_f.get("tks") or {}, avis, hoy, ctx.hora, ctx.eventos,
                                                 {tk: [{"dir": s_.direccion, "fuerza": s_.fuerza, "texto": s_.texto} for s_ in ss if s_.agente in ("mundo", "hechos_emisor", "noticias")]
                                                  for tk, ss in por_ticker.items()})
        if avis != antes_av and not simular:
            almacen.put("cartera/avisados", avis)
    except Exception as ex:
        print(f"[seguimiento_cartera] {ex}")

    eventos_cal = _calendario(almacen, ctx, hoy, ops, abiertas, cartera, simular)  # antes del resumen: carga licitaciones y avisos

    resumen = {
        "fecha": hoy.isoformat(), "hora": ctx.hora, "clima": ctx.extra.get("clima_estado"),
        "indicadores": {k: ctx.extra.get(k) for k in ("mep_al30", "ccl_al30", "canje_pct", "spread_gd_al_30",
                                                       "brecha_mep_pct", "caucion_tna", "ccl_cedears_mediana")},
        "riesgo_pais": ctx.riesgo_pais, "riesgo_pais_ayer": ctx.riesgo_pais_ayer, "dolares": ctx.dolares,
        "reservas": ctx.reservas,
        "senales": [s.dict() for s in senales][:300],
        "evaluados": [{k: e[k] for k in ("ticker", "puntaje", "plan", "riesgo")} for e in evaluados],
        "nuevas": [n["id"] for n in nuevas],
        "lista": {tk: ctx.por_simbolo.get(tk) for tk in ctx.tickers_lista()},
        "precios": {tk: {k: ctx.por_simbolo[tk].get(k) for k in ("ultimo", "variacion", "compra", "venta", "grupo")}
                    for tk in set(ctx.tickers_lista()) | set(abiertas) | set(ctx.extra["ons_usuario"])
                    | {c.get("ticker", "").upper() for c in cartera} if tk in ctx.por_simbolo},
        "tir_ons": ctx.extra.get("tir_ons"),
        "consumo_iol": consumo.resumen(), "ia_llamadas": ia.llamadas,
        "esperanza": reg.esperanza_mesa(),
        "informes": informes,
        "oportunidades": {k: [o for o in v if o["mesa"]["aprobada"]] for k, v in ops.items()},
        "oportunidades_observadas": sum(1 for v in ops.values() for o in v if not o["mesa"]["aprobada"]),
        "aprendizajes": _aprendizajes(),
        "opinion_cartera": opinion_cartera,
        "economista": ctx.extra.get("regimen"),
        "wallstreet": ctx.extra.get("wallstreet"),
        "cripto": {k: v for k, v in (ctx.extra.get("cripto") or {}).items() if k != "ens"},
        "adr": ctx.extra.get("adr_tabla"),
        "radar": radar_inv,
        "anticipos": ctx.extra.get("anticipos"),
        "licitaciones_noticias": ctx.extra.get("licitaciones_noticias"),
        "licitaciones_avisos": ctx.extra.get("licitaciones_avisos"),
        "mae": ctx.extra.get("mae"),
        "mundo": ctx.extra.get("mundo"),
        "ministro": ctx.extra.get("ministro"),
        "ganadores": ctx.extra.get("ganadores"),
        "profesionales": ctx.extra.get("profesionales"),
        "protecciones": prot,
        "comite": comite_estado,
        "proyeccion_cartera": proy_cartera,
        "seguimiento_cartera": seg_cartera,
        "memoria": None if simular else (almacen.get("memoria/papeles") or {}),
        "pronosticos": libreta[:200],
        "reunion": None if simular else almacen.get("revision/ultima"),
        "alertas_disparadas": None if simular else (almacen.get("alertas/disparadas") or {}),
        "mae_dias": None if simular else [{"fecha": d["fecha"], "resumen": d["resumen"]}
                                          for d in ((almacen.get("mae/comparacion") or {}).get("dias") or [])[-20:]],
        "anticipo_lista": ctx.extra.get("anticipo_lista"),
        "anticipo_listas": ctx.extra.get("anticipo_listas"),
        "anticipo_estadistica": None if simular else almacen.get("anticipo/estadistica"),
        "eventos": eventos_cal,
        "flujos_bonos": flujos_cartera or {k: v for k, v in eventos_mod.flujos_bonos().items()
                                           if k in {c.get("ticker", "").upper() for c in cartera}},
        "cobros": mis_cobros,
    }
    almacen.put("ui/estado", {**estado_ui, **resumen, "dia": dia})
    # foto compacta de TODOS los paneles para el Asistente (sin gastar consultas extra)
    if cada30 or ya.minute % 15 < 5:
      almacen.put("ui/panel", {"fecha": hoy.isoformat(), "hora": ctx.hora, "titulos": {
        tk: [round(t.get("ultimo") or 0, 4), round(t["variacion"], 2) if t.get("variacion") is not None else None,
             t.get("compra"), t.get("venta"), t.get("grupo")]
        for tk, t in ctx.por_simbolo.items() if t.get("ultimo")}})
    previas = almacen.get("ui/alertas") or []
    ya_avisadas = {(a["fecha"], a["ticker"]) for a in previas}
    try:
        alertas_niv = _alertas_niveles(ctx, lista + [c for c in cartera if c.get("alertas")], almacen, simular)
    except Exception as ex:
        print(f"[alertas de nivel] {ex}")
        alertas_niv = []
    alertas_lista = [a for a in alertas_seg + avisos_radar + _alertas_lista(ctx, lista) if (a["fecha"], a["ticker"]) not in ya_avisadas]
    alertas_lista += alertas_niv  # las de nivel avisan siempre (cada una una sola vez)
    alertas_lista += avisos_cobro  # cobros de hoy / mañana / la semana (una vez por día)
    alertas_lista += avisos_cartera  # la sugerencia sobre algo que tenés cambió: decidir en la app
    if alertas_lista:
        almacen.put("ui/alertas", (alertas_lista + previas)[:60])
    consumo.guardar()

    if (nuevas or alertas_lista) and not simular:
        subs = almacen.get("push/suscripciones") or []
        res = push.enviar(subs)
        if res["vencidas"]:
            almacen.put("push/suscripciones", [s for s in subs if s.get("endpoint") not in res["vencidas"]])
    return {"corrio": True, "nuevas": len(nuevas), "senales": len(senales), "consumo": consumo.resumen(),
            "diagnostico": {"anticipo": ctx.extra.get("anticipo_diag"), "kv_escrituras": getattr(almacen, "escrituras", None), "kv_omitidas": getattr(almacen, "omitidas", None),
                            "kv_claves": [k.split("/")[0] + "/" + k.split("/")[1][:12] for k in getattr(almacen, "escritas", [])],
                            "paneles": {g: len(t) for g, t in paneles.items()},
                            "riesgo_pais": ctx.riesgo_pais.get("valor"), "rp_ayer": ctx.riesgo_pais_ayer,
                            "dolares": sorted(k for k in ctx.dolares if not k.startswith("_")),
                            "noticias": len(ctx.noticias), "con_historial": len(cache.indice),
                            "ia": ia.disponible, "agentes": sorted({s.agente for s in senales}),
                            "ejemplo_soberanos": [t["simbolo"] for t in paneles.get("soberanos", [])[:8]],
                            "ejemplo_cedears": [t["simbolo"] for t in paneles.get("cedears", [])[:8]]}}


def _ar(x: float) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _alertas_niveles(ctx: Contexto, lista: list[dict], almacen, simular: bool) -> list[dict]:
    """Alertas de nivel que cargás en la app para cada favorito: "avisame si baja de X / sube de Y",
    en pesos (precio de BYMA) o en dólares (precio de la acción en EE.UU., para CEDEARs). Cada una avisa una vez."""
    items = [(it, al) for it in lista for al in (it.get("alertas") or []) if al.get("id") and al.get("nivel")]
    if not items:
        return []
    disparadas = almacen.get("alertas/disparadas") or {}
    usd_tks = {it["ticker"][:-1] if it["ticker"][-1:] in ("D", "C") and ctx.titulo(it["ticker"][:-1]) else it["ticker"]
               for it, al in items if al.get("moneda") == "USD" and al["id"] not in disparadas}
    vivo = {} if simular or not usd_tks else gratis.yahoo_varios(list(usd_tks), prepost=False)
    out, cambio = [], False
    for it, al in items:
        if al["id"] in disparadas:
            continue
        tk = it["ticker"]
        nivel = float(al["nivel"])
        if al.get("moneda") == "USD":
            base = tk[:-1] if tk[-1:] in ("D", "C") and ctx.titulo(tk[:-1]) else tk
            p = (vivo.get(base) or {}).get("precio")
            lo = hi = p
            mon = "US$ "
        else:
            t = ctx.titulo(tk) or {}
            p = t.get("ultimo")
            lo, hi = t.get("minimo") or p, t.get("maximo") or p
            mon = "$"
        if not p:
            continue
        toca = lo <= nivel if al.get("tipo") == "baja" else hi >= nivel
        if toca:
            disparadas[al["id"]] = {"fecha": ctx.fecha.isoformat(), "hora": ctx.hora, "precio": round(p, 4)}
            cambio = True
            out.append({"fecha": ctx.fecha.isoformat(), "hora": ctx.hora, "ticker": tk, "id": al["id"],
                        "texto": f"🔔 {tk} {'bajó de' if al.get('tipo') == 'baja' else 'superó'} {mon}{_ar(nivel)} (ahora {mon}{_ar(p)})."
                                 + (f" {al['nota']}" if al.get("nota") else "")})
    if cambio and not simular:
        almacen.put("alertas/disparadas", disparadas)
    return out


def _alertas_lista(ctx: Contexto, lista: list[dict]) -> list[dict]:
    """Alertas propias de Mi lista: precio objetivo tocado."""
    out = []
    for item in lista:
        t = ctx.titulo(item.get("ticker", ""))
        if not t or not t.get("ultimo") or not item.get("precio"):
            continue
        p = float(item["precio"])
        if (t.get("minimo") or t["ultimo"]) <= p <= (t.get("maximo") or t["ultimo"]):
            out.append({"fecha": ctx.fecha.isoformat(), "hora": ctx.hora, "ticker": item["ticker"],
                        "texto": f"{item['ticker']} tocó tu precio {_ar(p)} (último {_ar(t['ultimo'])})."})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--forzar", action="store_true")
    ap.add_argument("--simular", action="store_true")
    a = ap.parse_args()
    import traceback
    try:
        r = correr(a.forzar, a.simular)
        print(json.dumps(r, ensure_ascii=False, indent=1, default=str))
        if r.get("corrio"):
            print(f"::notice::Ronda OK: {r['nuevas']} propuestas, {r['senales']} señales, IOL {r['consumo']['total']}/{r['consumo']['tope']} | {json.dumps(r['diagnostico'], ensure_ascii=False)}")
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)[-1]
        print(f"::error::{type(e).__name__}: {str(e)[:400]} (en {tb.filename.split('/')[-1]}:{tb.lineno})")
        raise
