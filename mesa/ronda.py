"""Una ronda de la mesa: datos → 13 agentes → debate → Riesgo → Jefe → registro y avisos.

Uso:  python -m mesa.ronda            (decide sola si le toca correr según hora y presupuesto)
      python -m mesa.ronda --forzar   (corre igual, p. ej. botón 'Analizar ahora')
      python -m mesa.ronda --simular  (sin IOL: usa tests/fixtures, para probar)
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, timedelta

import yaml

from .agentes import adr, analistas, con_ia, cripto, economista, panico, radar, informes as informes_mod, oportunidades, riesgo, seguimiento, supervisor, wallstreet
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


def _calendario(almacen, ctx, hoy, ops, abiertas, cartera) -> list[dict]:
    """Eventos de los próximos 45 días que importan: los de mis activos, oportunidades y los CEDEARs más operados."""
    try:
        base = lambda t: t[:-1] if t.endswith(("D", "C")) and ctx.titulo(t[:-1]) else t
        mios = {base(t) for t in ctx.tickers_lista() + list(abiertas) + [c.get("ticker", "").upper() for c in cartera]}
        mios |= {o["ticker"] for l in (ops or {}).values() for o in l}
        mios |= set((almacen.get("usuario/ons") or {}).keys())
        top = sorted((t for t in ctx.grupo("cedears") if t.get("monto")), key=lambda t: -t["monto"])[:30]
        mios |= {t["simbolo"] for t in top if t.get("simbolo")}
        ev = eventos_mod.armar(almacen, hoy, 45, mios)
        for e in ev:
            e["mio"] = e.get("ticker") in mios and e.get("ticker") not in {t["simbolo"] for t in top} or e.get("tipo") == "macro"
        return ev[:80]
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
            tot += s.direccion * s.fuerza * reg.peso(s.agente, s.fuerza) * m
    return round(tot, 3)


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
        return radar.detectar(ctx, ya.hour * 60 + ya.minute, brechas, ctx.riesgo_pais_ayer, ccl_ay)
    except Exception as ex:
        print(f"[radar] {ex}")
        return []


def _radar_investigar(ctx, almacen, hoy, alertas: list[dict], por_ticker: dict) -> tuple[list[dict], list[dict]]:
    """Investiga cada alerta (máx. 10) y devuelve (investigaciones, avisos para el celular de las graves y nuevas)."""
    from .nucleo.config import emisores
    nombres = {"tecnico": "Técnico", "historiador": "Historiador", "fuerza_relativa": "Fuerza relativa", "volumen_flujo": "Volumen y flujo",
               "economista": "Economista", "wallstreet": "Wall Street", "cripto": "Cripto", "adr": "Noche de Nueva York", "panico": "Comprador de pánico",
               "acciones": "Acciones", "cedears": "CEDEARs", "soberanos": "Soberanos", "ons": "ONs", "macro_dolar": "Macro / dólar",
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
        if not toca_correr(ya, consumo.factor_frecuencia()):
            return {"corrio": False, "motivo": "no toca en este horario"}

    # Cloudflare KV gratis: ~1.000 escrituras por día. Lo que no es urgente se guarda cada 30 minutos.
    minuto_dia = ya.hour * 60 + ya.minute
    cada30 = bool(forzar or simular or minuto_dia % 30 < 5 or minuto_dia >= 16 * 60 + 55)
    if not simular and not forzar:
        ultima = almacen.get("ronda/ultima") or {}
        if ultima.get("ts") and ya.timestamp() - ultima["ts"] < 170:
            return {"corrio": False, "motivo": "ya corrió una ronda hace menos de 3 minutos"}
    if not simular:
        almacen.put("ronda/ultima", {"ts": ya.timestamp(), "hora": ya.strftime("%H:%M")})

    iol = None
    if not simular:
        from .datos.iol import IOL
        iol = IOL(consumo, almacen=almacen)
    cache = CacheHistorico(almacen, iol)
    reg = Registro(almacen)
    estado_ui = almacen.get("ui/estado") or {}
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

    # candidatos: lo que alguien marcó + Mi lista; con carga de historial una sola vez por ticker
    marcados = [s.ticker for s in senales if s.direccion != 0 and ctx.titulo(s.ticker)]
    # --- Radar: todo lo anormal del mercado entra al análisis de TODOS los analistas en esta ronda ---
    alertas_radar = [] if simular else _radar_detectar(ctx, almacen, hoy, ya)
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
    vetos = {s.ticker for s in hechos if s.veto}

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
                          "sector": sector(tk), "puntaje": puntajes[tk], "plan": plan.dict(), "riesgo": r,
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
            debatidos = [e for e in debatidos if (e.get("prob_modelo") or 0) >= modelo.get("umbral", 0.5)]
        except Exception as ex:
            print(f"[jefe-modelo] {ex}")
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
        tks = list(dict.fromkeys(pedidos + preseleccion + ctx.tickers_lista() + list(ya_propuestos)))
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
        "eventos": _calendario(almacen, ctx, hoy, ops, abiertas, cartera),
        "flujos_bonos": {k: v for k, v in eventos_mod.flujos_bonos().items()
                         if k in {c.get("ticker", "").upper() for c in cartera}},
    }
    almacen.put("ui/estado", {**estado_ui, **resumen})
    # foto compacta de TODOS los paneles para el Asistente (sin gastar consultas extra)
    if cada30 or ya.minute % 15 < 5:
      almacen.put("ui/panel", {"fecha": hoy.isoformat(), "hora": ctx.hora, "titulos": {
        tk: [round(t.get("ultimo") or 0, 4), round(t["variacion"], 2) if t.get("variacion") is not None else None,
             t.get("compra"), t.get("venta"), t.get("grupo")]
        for tk, t in ctx.por_simbolo.items() if t.get("ultimo")}})
    previas = almacen.get("ui/alertas") or []
    ya_avisadas = {(a["fecha"], a["ticker"]) for a in previas}
    alertas_lista = [a for a in alertas_seg + avisos_radar + _alertas_lista(ctx, lista) if (a["fecha"], a["ticker"]) not in ya_avisadas]
    if alertas_lista:
        almacen.put("ui/alertas", (alertas_lista + previas)[:60])
    consumo.guardar()

    if (nuevas or alertas_lista) and not simular:
        subs = almacen.get("push/suscripciones") or []
        res = push.enviar(subs)
        if res["vencidas"]:
            almacen.put("push/suscripciones", [s for s in subs if s.get("endpoint") not in res["vencidas"]])
    return {"corrio": True, "nuevas": len(nuevas), "senales": len(senales), "consumo": consumo.resumen(),
            "diagnostico": {"kv_escrituras": getattr(almacen, "escrituras", None), "kv_omitidas": getattr(almacen, "omitidas", None),
                            "paneles": {g: len(t) for g, t in paneles.items()},
                            "riesgo_pais": ctx.riesgo_pais.get("valor"), "rp_ayer": ctx.riesgo_pais_ayer,
                            "dolares": sorted(k for k in ctx.dolares if not k.startswith("_")),
                            "noticias": len(ctx.noticias), "con_historial": len(cache.indice),
                            "ia": ia.disponible, "agentes": sorted({s.agente for s in senales}),
                            "ejemplo_soberanos": [t["simbolo"] for t in paneles.get("soberanos", [])[:8]],
                            "ejemplo_cedears": [t["simbolo"] for t in paneles.get("cedears", [])[:8]]}}


def _ar(x: float) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


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
