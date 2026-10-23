"""Tareas fuera de la ronda.

python -m mesa.cierre diario         17:10 — velas del día (gratis con el panel), seguimiento, señales, riesgo país
python -m mesa.cierre calificadoras  10:00 — Calificadoras (1 vez por día)
python -m mesa.cierre semanal        viernes — ranking e incentivos
python -m mesa.cierre mensual        1er día hábil — capacitación (queda pendiente de tu aprobación)
"""
from __future__ import annotations

import json
import sys
from datetime import timedelta

from .agentes import con_ia
from .datos import gratis
from .datos.cache import CacheHistorico
from .datos.consumo import Consumo
from .nucleo import capacitacion
from .nucleo.almacen import almacen_por_defecto
from .nucleo.ia import IA
from .nucleo.registro import Registro
from .nucleo.reloj import ahora, es_dia_habil
from .ronda import cargar_paneles


def diario(simular: bool = False) -> dict:
    a = almacen_por_defecto()
    hoy = ahora().date()
    if not simular and not es_dia_habil(hoy, a):
        return {"corrio": False, "motivo": "día no hábil"}
    consumo = Consumo(a)
    iol = None
    if not simular:
        from .datos.iol import IOL
        iol = IOL(consumo, almacen=a)
    paneles = cargar_paneles(iol, consumo, a, simular)
    cache = CacheHistorico(a, iol)
    agregadas = 0
    precios = {}
    for grupo_p, titulos in paneles.items():
        for t in titulos:
            s = t.get("simbolo")
            if not s or not t.get("ultimo"):
                continue
            t.setdefault("grupo", grupo_p)
            precios[s] = t
            # solo se arma vela si el ticker ya tiene historial (no se inflan miles de tickers sin uso)
            if cache.velas(s):
                v = cache.vela_del_dia(t, hoy)
                agregadas += cache.agregar(s, [v]) if v else 0
    # historial nuevo para los CEDEARs y acciones más operados (máx. 12 por día, cuida el cupo):
    # así Técnico, Historiador y Oportunidades también los analizan
    if iol is not None:
        import re as _re
        simbolos = {t.get("simbolo") for g in ("cedears", "acciones") for t in paneles.get(g, [])}
        es_linea_usd = lambda s: s[-1:] in ("D", "C") and s[:-1] in simbolos  # AAPLD sí; PLD o AMD no
        candidatos = [t for g in ("cedears", "acciones") for t in paneles.get(g, [])
                      if t.get("simbolo") and t.get("monto") and not es_linea_usd(t["simbolo"])
                      and not cache.velas(t["simbolo"])]
        candidatos.sort(key=lambda t: t["monto"], reverse=True)
        # CEDEARs: historial gratis (EE.UU. × CCL), hasta 40 por día. Acciones: IOL, hasta 12 por día.
        nuevos_ced = nuevos_acc = 0
        for t in [t for t in candidatos if t in paneles.get("cedears", [])][:40]:
            cache.asegurar_cedear(t["simbolo"], t["ultimo"])
            nuevos_ced += 1 if cache.velas(t["simbolo"]) else 0
        for t in [t for t in candidatos if t in paneles.get("acciones", [])][:12]:
            if not consumo.puede_consultar(1):
                break
            cache.asegurar(t["simbolo"], 1)
            nuevos_acc += 1 if cache.velas(t["simbolo"]) else 0
        print(f"[cierre] historial nuevo: {nuevos_ced} CEDEARs (gratis) y {nuevos_acc} acciones (IOL)")

    # MAE: histórico propio de cierres de bonos/ONs/letras, comparación de cierres con BYMA e historial gratis
    if not simular:
        try:
            from .agentes import mae as _mae
            from .datos.gratis import mae_cierres
            rows = mae_cierres(hoy - timedelta(days=4), hoy)
            nuevos = _mae.guardar_historico(a, rows, set(precios))
            rf = {tk: t for tk, t in precios.items() if t.get("grupo") in _mae.GRUPOS_RF}
            hoy_rows = [{**r, "monto": r.get("volumen")} for r in rows if r["fecha"][:10] == hoy.isoformat()]
            pares = _mae.comparar(rf, hoy_rows)
            if pares:
                comp = a.get("mae/comparacion") or {"dias": []}
                comp["dias"] = [d for d in comp["dias"] if d["fecha"] != hoy.isoformat()][-89:] + [
                    {"fecha": hoy.isoformat(), "resumen": _mae.resumen(pares),
                     "mayores": [p for p in pares if p["liquido"]][:8]}]
                a.put("mae/comparacion", comp)
            sin_hist = sorted((t for t in rf.values() if not cache.velas(t["simbolo"])), key=lambda t: -(t.get("monto") or 0))[:60]
            cargados = sum(1 for t in sin_hist if cache.asegurar_mae(t["simbolo"]))
            print(f"[cierre] MAE: {nuevos} cierres nuevos, {len(pares)} comparados con BYMA, {cargados} historiales gratis")
        except Exception as ex:
            print(f"[cierre] mae: {ex}")

    # Corresponsal: cierra las anotaciones de hace una semana y aprende qué temas anticipan el precio
    if not simular:
        try:
            from .agentes import mundo as _mundo
            log = a.get("mundo/log") or []
            if log:
                quedan, stats = _mundo.evaluar(log, a.get("mundo/stats") or {}, lambda tk: (precios.get(tk) or {}).get("ultimo"), hoy.isoformat())
                if len(quedan) != len(log):
                    a.put("mundo/log", quedan)
                    a.put("mundo/stats", stats)
                print(f"[cierre] corresponsal: {len(log) - len(quedan)} anotaciones evaluadas")
        except Exception as ex:
            print(f"[cierre] mundo: {ex}")

    # Reunión de la mesa: el Jefe y los analistas revisan lo que miraron en la última semana y aprenden
    if not simular:
        try:
            from .agentes import revision as _rev
            panel_ui = (a.get("ui/panel") or {}).get("titulos") or {}
            r = _rev.reunir(a, cache, panel_ui, hoy, 7)
            aj = _rev.ajustes(r)
            r["lecciones"] = _rev.lecciones(r)
            r["ajustes"] = aj
            a.put("revision/ultima", r)
            a.put("revision/ajustes", aj)
            print(f"[cierre] reunión: {r['senales']} señales revisadas, {len(aj)} ajustes")
        except Exception as ex:
            print(f"[cierre] reunión: {ex}")

    # calendario de balances y dividendos de EE.UU. para los CEDEARs (gratis, no usa IOL)
    if not simular:
        try:
            from .datos import eventos as ev_mod
            simb = {t.get("simbolo") for t in paneles.get("cedears", []) if t.get("simbolo")}
            cedears = {s for s in simb if not (s[-1:] in ("D", "C") and s[:-1] in simb)}
            ev = ev_mod.eeuu(cedears, hoy, 21)
            a.put("eventos/eeuu", {"fecha": hoy.isoformat(), "eventos": ev})
            print(f"[cierre] eventos EE.UU.: {len(ev)}")
        except Exception as ex:
            print(f"[cierre] eventos EE.UU.: {ex}")

    # datos de Wall Street para el Estratega (gratis): índices + CEDEARs del universo, últimos ~300 días
    if not simular:
        try:
            a.put("wallstreet/datos", _datos_ws(a, paneles, "2y", 300))
        except Exception as ex:
            print(f"[cierre] wall street: {ex}")

    # histórico propio de ADRs: estadística del día con las fotos de cada ronda
    if not simular:
        try:
            from .agentes import adr as _adr
            dia_ui = (a.get("ui/estado") or {}).get("dia") or {}
            fotos = dia_ui.get(f"adr/fotos/{hoy.isoformat()}") or a.get(f"adr/fotos/{hoy.isoformat()}") or []
            ccl_s = ((a.get("macro/series") or {}).get("series") or {}).get("ccl") or {}
            ccl_ant = next((v for f, v in sorted(ccl_s.items(), reverse=True) if f < hoy.isoformat()), None)
            if fotos:
                dia = _adr.estadistica_del_dia(fotos, ccl_ant)
                est = a.get("adr/estadistica") or {"desde": hoy.isoformat(), "dias": 0, "plazos": {}}
                if est.get("ultimo_dia") != hoy.isoformat():
                    est["plazos"] = _adr.acumular(est.get("plazos") or {}, dia)
                    est["dias"] = est.get("dias", 0) + 1
                    est["ultimo_dia"] = hoy.isoformat()
                    a.put("adr/estadistica", est)
                print(f"[cierre] ADR: {len(fotos)} fotos, {dia['30'].get('casos', 0)} casos hoy")
        except Exception as ex:
            print(f"[cierre] adr: {ex}")

    # Anticipador (días antes): lista de papeles con precursores de suba, para mañana
    if not simular:
        try:
            from .agentes import anticipo as _ant2
            from .datos import gratis as _g2
            mod = a.get("anticipo/modelo") or {}
            if mod.get("w"):
                from concurrent.futures import ThreadPoolExecutor
                uni = _universo_cedears(a)
                with ThreadPoolExecutor(8) as ex:
                    ser = {tk: f for tk, f in zip(uni, ex.map(lambda t: _g2.yahoo_ohlcv(t.replace(".", "-"), "6mo"), uni)) if len(f) > 60}
                for tk in cache.indice:
                    vs = cache.velas(tk)
                    if tk not in ser and len(vs) > 60 and tk in {t.get("simbolo") for t in paneles.get("acciones", [])}:
                        ser[tk] = [{"fecha": v["fecha"], "c": v["cierre"], "h": v.get("maximo") or v["cierre"],
                                    "l": v.get("minimo") or v["cierre"], "v": v.get("volumen") or 0} for v in vs[-120:]]
                spy = {f: c for f, c in _g2.yahoo("SPY", "3mo")}
                vix = {f: c for f, c in _g2.yahoo("^VIX", "3mo")}
                btc = {f: c for f, c in _g2.yahoo("BTC-USD", "3mo")}
                cm = _ant2.contexto_mkt(max(spy) if spy else hoy.isoformat(), spy, vix, btc)
                lista = _ant2.puntuar(mod, ser, cm)
                a.put("anticipo/lista", {"fecha": hoy.isoformat(), "activo": mod.get("activo"), "umbral": mod.get("umbral"),
                                         "prueba": mod.get("prueba"), "lista": [x for x in lista if x["prob"] >= (mod.get("umbral") or 1)][:15]})
        except Exception as ex:
            print(f"[cierre] anticipador: {ex}")

    # Anticipador: estadística propia (desde el primer precio operable hasta el cierre)
    if not simular:
        try:
            from .agentes import anticipo as _ant
            reg_a = ((a.get("ui/estado") or {}).get("dia") or {}).get(f"anticipo/{hoy.isoformat()}") or {}
            if reg_a:
                dia = _ant.evaluar_dia(reg_a, {tk: t.get("ultimo") for tk, t in precios.items()})
                est = a.get("anticipo/estadistica") or {"desde": hoy.isoformat(), "dias": 0, "plazos": {}}
                if est.get("ultimo_dia") != hoy.isoformat():
                    from .agentes.adr import acumular
                    est["plazos"] = acumular(est.get("plazos") or {}, dia)
                    est["dias"] += 1
                    est["ultimo_dia"] = hoy.isoformat()
                    a.put("anticipo/estadistica", est)
        except Exception as ex:
            print(f"[cierre] anticipo: {ex}")

    # datos del agente Cripto (gratis): Bitcoin y dólar cripto
    if not simular:
        try:
            from .datos import gratis as _g
            a.put("cripto/datos", {"fecha": hoy.isoformat(), "btc": _g.yahoo("BTC-USD", "2y")[-300:],
                                   "dolar_cripto": dict(sorted(_g.dolar_cripto_historico().items())[-60:])})
        except Exception as ex:
            print(f"[cierre] cripto: {ex}")

    # huecos (p. ej. un cierre que falló): se completan pidiendo SOLO las fechas faltantes, máx. 10 por día
    if iol is not None:
        from datetime import date, timedelta
        huecos = 0
        for tk in list(cache.indice):
            previas = [v["fecha"] for v in cache.velas(tk) if v["fecha"] < hoy.isoformat()]
            if not previas:
                continue
            ult = date.fromisoformat(previas[-1])
            faltan = [ult + timedelta(days=i) for i in range(1, (hoy - ult).days)
                      if es_dia_habil(ult + timedelta(days=i), a)]
            if faltan and huecos < 10 and consumo.puede_consultar(1):
                try:
                    cache.agregar(tk, iol.historial(tk, faltan[0], faltan[-1]), fuente="iol")
                    huecos += 1
                except Exception as e:
                    print(f"[hueco] {tk}: {e}")
    cache.guardar()

    reg = Registro(a)
    cambios = reg.actualizar_seguimiento(precios, hoy)
    fechas = sorted({v["fecha"] for tk in cache.indice for v in cache.velas(tk)})[-40:]
    cierres = {tk: {v["fecha"]: v["cierre"] for v in cache.velas(tk)} for tk in cache.indice}
    reg.evaluar_senales(fechas, cierres)
    reg.guardar()
    rp = gratis.riesgo_pais() if not simular else {"valor": None}
    if rp.get("valor"):
        a.put("ref/riesgo_pais_cierre", {"valor": rp["valor"], "fecha": hoy.isoformat()})
    consumo.guardar()
    a.put("ui/cierre", {"fecha": hoy.isoformat(), "velas_agregadas": agregadas, "cambios": len(cambios),
                        "esperanza": reg.esperanza_mesa(), "consumo_iol": consumo.resumen()})
    return {"corrio": True, "velas": agregadas, "cambios": len(cambios), "consumo": consumo.resumen()}


def calificadoras() -> dict:
    a = almacen_por_defecto()
    ia = IA()
    res = con_ia.calificadoras(ia, a, ahora().date())
    lic = con_ia.licitaciones(ia, a, ahora().date())
    from .datos.eventos import actualizar_licitaciones
    mae = actualizar_licitaciones(a, ahora().date(), ahora().strftime("%H:%M"), forzar=True)
    return {"cambios": len(res.get("cambios", [])), "licitacion": (lic.get("proxima") or {}).get("fecha"),
            "licitaciones_mae": len(mae.get("eventos") or [])}


def semanal() -> list[dict]:
    a = almacen_por_defecto()
    reg = Registro(a)
    reg.recalibrar()
    return reg.cerrar_ranking_semanal()


def _universo_cedears(a, paneles=None) -> list[str]:
    """CEDEARs que la mesa sigue: los que tienen historial + Mi lista + cartera (máx. 80)."""
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    ced = {tk for tk, x in panel.items() if x[4] == "cedears"}
    base = lambda t: t[:-1] if t[-1:] in ("D", "C") and t[:-1] in ced else t
    idx = set((a.get("cache/indice") or {}).keys())
    mios = {base(str(x.get("ticker", "")).upper()) for k in ("usuario/lista", "usuario/cartera") for x in (a.get(k) or [])}
    from .agentes.cripto import CEDEARS_CRIPTO
    from .agentes.panico import INDICES_CEDEAR
    return sorted(({base(t) for t in idx & ced} | (mios & ced) | (set(CEDEARS_CRIPTO + INDICES_CEDEAR) & ced)) - {""})[:95]


def _datos_ws(a, paneles, rango: str, ultimos: int | None = None) -> dict:
    from .datos import gratis
    d = gratis.datos_wallstreet(_universo_cedears(a, paneles), rango)
    if ultimos:
        d["indices"] = {k: v[-ultimos:] for k, v in d["indices"].items()}
        d["precios"] = {k: v[-ultimos:] for k, v in d["precios"].items()}
    return d


def entrenar() -> dict:
    """Entrenamiento con la historia: hace opinar a los agentes en cada día pasado y mide cuánto acertaron."""
    from .nucleo import calibracion
    a = almacen_por_defecto()
    cache = CacheHistorico(a)
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    grupos = {tk: x[4] for tk, x in panel.items()}
    series = {tk: cache.velas(tk) for tk in cache.indice}
    from .datos import gratis
    macro = gratis.series_macro()
    registro: list = []  # todas las opiniones de la historia, para que el Jefe aprenda combinaciones
    hist = calibracion.entrenar_con_historia(series, grupos, a.get("params/agentes") or {}, macro=macro, registro=registro)
    a.put("ranking/stats_historicas", hist)
    ens = {k: f"{v['aciertos'] / v['casos'] * 100:.1f}% de {v['casos']} ({v['suma_ret'] / v['casos']:+.2f}% prom.)"
           for k, v in (hist.get("_ensenanza") or {}).items() if v.get("casos")}
    a.put("ranking/ensenanza", hist.get("_ensenanza") or {})
    # Estratega de Wall Street: 5 años en dólares
    from .agentes import wallstreet
    datos5 = _datos_ws(a, None, "5y")
    ws = wallstreet.entrenar(datos5, registro=registro)
    a.put("wallstreet/datos", {"fecha": datos5["fecha"], "indices": {k: v[-300:] for k, v in datos5["indices"].items()},
                               "precios": {k: v[-300:] for k, v in datos5["precios"].items()}})
    hist["wallstreet"] = ws["wallstreet"]
    a.put("ranking/stats_historicas", hist)
    a.put("ranking/ensenanza_ws", ws["ensenanza"])
    ens["wallstreet"] = {k: f"{v['aciertos'] / v['casos'] * 100:.1f}% de {v['casos']} ({v['suma_ret'] / v['casos']:+.2f}% prom.)"
                         for k, v in ws["ensenanza"].items() if v.get("casos")}
    # Noche de Nueva York: ADRs contra acciones locales (lo realista: desde la apertura del día siguiente)
    from .agentes import adr
    adrs2 = {x: gratis.yahoo(x, "2y") for x in set(adr.ADRS.values())}
    hist["adr"] = adr.entrenar({loc: cache.velas(loc) for loc in adr.ADRS}, adrs2, macro.get("ccl") or {})
    a.put("ranking/stats_historicas", hist)
    ph = hist["adr"]["por_horizonte"]
    ens["adr"] = {k: f"{v['aciertos'] / v['casos'] * 100:.1f}% de {v['casos']} ({v['suma_ret'] / v['casos']:+.2f}% prom.)"
                  for k, v in ph.items() if v.get("casos")}
    a.put("ranking/prueba_adr", ph)

    # Comprador de pánico: CEDEARs 5 años en dólares + acciones locales con el riesgo país
    from .agentes import panico
    acciones = {tk: cache.velas(tk) for tk in cache.indice if grupos.get(tk) == "acciones"}
    hist["panico"] = panico.entrenar(datos5["precios"], datos5["indices"], acciones, macro.get("riesgo_pais") or {}, registro=registro)
    a.put("ranking/stats_historicas", hist)
    a.put("ranking/prueba_panico", {"por_tipo": hist["panico"]["por_tipo"], "por_horizonte": hist["panico"]["por_horizonte"]})
    ens["panico"] = {k: f"{v['aciertos'] / v['casos'] * 100:.1f}% de {v['casos']} ({v['suma_ret'] / v['casos']:+.2f}% prom. a 20 ruedas)"
                     for k, v in hist["panico"]["por_tipo"].items() if v.get("casos")}

    # Anticipador (días antes): precursores de subas de 5% en la semana, 5 años de CEDEARs + acciones locales
    from .agentes import anticipo as _ant
    ohlcv = {}
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(8) as ex:
        tks = list(datos5["precios"])
        for tk, f in zip(tks, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "5y"), tks)):
            if len(f) > 300:
                ohlcv[tk] = f
    for tk in cache.indice:
        if grupos.get(tk) == "acciones":
            vs = cache.velas(tk)
            if len(vs) > 120:
                ohlcv[tk] = [{"fecha": v["fecha"], "c": v["cierre"], "h": v.get("maximo") or v["cierre"],
                              "l": v.get("minimo") or v["cierre"], "v": v.get("volumen") or 0} for v in vs]
    sp = {f: c for f, c in datos5["indices"].get("SPY", [])}
    vx = {f: c for f, c in datos5["indices"].get("^VIX", [])}
    bt = {f: c for f, c in gratis.yahoo("BTC-USD", "5y")}
    mod_a = _ant.entrenar(ohlcv, sp, vx, bt)
    a.put("anticipo/modelo", mod_a)
    ens["anticipador"] = {"motivo": mod_a.get("motivo"), "prueba": mod_a.get("prueba"), "activo": mod_a.get("activo")}

    # Cripto: BTC 5 años y dólar cripto desde 2023
    from .agentes import cripto
    from .datos import gratis as _g
    btc5 = _g.yahoo("BTC-USD", "5y")
    dcr = _g.dolar_cripto_historico()
    cr = cripto.entrenar(btc5, datos5["precios"], dcr, macro.get("ccl") or {}, registro=registro)
    # El Jefe aprende combinaciones (precio en dólares para CEDEARs, en pesos para acciones)
    from .nucleo import combinador
    precios_lbl = {tk: [c for _, c in s] for tk, s in datos5["precios"].items()}
    fechas_lbl = {tk: {f: i for i, (f, _) in enumerate(s)} for tk, s in datos5["precios"].items()}
    for tk in cache.indice:
        if tk not in precios_lbl and grupos.get(tk) == "acciones":
            vs = cache.velas(tk)
            precios_lbl[tk] = [v["cierre"] for v in vs]
            fechas_lbl[tk] = {v["fecha"]: i for i, v in enumerate(vs)}
    vix = datos5["indices"].get("^VIX")
    rp_m = macro.get("riesgo_pais") or {}
    datos_jefe = combinador.armar_datos(registro, precios_lbl, fechas_lbl, lambda f: combinador.contexto(f, btc5, vix, rp_m))
    modelo = combinador.entrenar(datos_jefe)
    a.put("jefe/modelo", modelo)
    ens["jefe"] = {"motivo": modelo.get("motivo"), "prueba": modelo.get("prueba"), "aprendio": modelo.get("lo_que_aprendio")}
    hist["cripto"] = cr["cripto"]
    a.put("ranking/stats_historicas", hist)
    a.put("ranking/ensenanza_cripto", cr["ensenanza"])
    a.put("cripto/datos", {"fecha": datos5["fecha"], "btc": btc5[-300:], "dolar_cripto": dict(sorted(dcr.items())[-60:])})
    ens["cripto"] = {k: v.get("veredicto") for k, v in cr["ensenanza"].items()}
    ens["cripto_por_plazo"] = {h: f"{v['aciertos'] / v['casos'] * 100:.1f}% de {v['casos']} ({v['suma_ret'] / v['casos']:+.2f}% prom.)"
                               for h, v in cr["cripto"]["por_horizonte"].items() if v.get("casos")}
    ens["wallstreet_por_plazo"] = {h: f"{v['aciertos'] / v['casos'] * 100:.1f}% de {v['casos']} ({v['suma_ret'] / v['casos']:+.2f}% prom.)"
                                   for h, v in ws["wallstreet"]["por_horizonte"].items() if v.get("casos")}
    reg = Registro(a)
    cal = reg.recalibrar()
    a.put("ranking/tabla", reg.ranking())
    resumen = {ag: f"{c['acierto_pct']}% de {c['casos']} casos ({c['fuente']}) -> voto x{c['factor']}" for ag, c in cal.items()}
    return {"series": len(series), "calibracion": resumen, "ensenanza_economista": ens}


def mensual() -> dict:
    a = almacen_por_defecto()
    cache = CacheHistorico(a)
    series = [cache.velas(tk) for tk in cache.indice if len(cache.velas(tk)) >= 200]
    params = a.get("params/agentes") or {}
    pendientes = []
    for fn, ag in ((capacitacion.entrenar_tecnico, "tecnico"), (capacitacion.entrenar_historiador, "historiador")):
        r = fn(series, params.get(ag, {}))
        if r:
            pendientes.append({**r, "fecha": ahora().date().isoformat(), "estado": "pendiente"})
    a.put("capacitacion/pendientes", pendientes)
    return {"series": len(series), "propuestas_de_cambio": len(pendientes)}


if __name__ == "__main__":
    tarea = sys.argv[1] if len(sys.argv) > 1 else "diario"
    fn = {"diario": diario, "calificadoras": calificadoras, "semanal": semanal, "mensual": mensual, "entrenar": entrenar}[tarea]
    import os
    import traceback
    _a = almacen_por_defecto()
    _hoy = ahora().date().isoformat()
    _hechas = _a.get("tareas/hechas") or {}
    if os.environ.get("RESPALDO") and _hechas.get(tarea) == _hoy:
        print(f"::notice::{tarea}: ya se hizo hoy (respaldo sin trabajo)")
        sys.exit(0)
    try:
        r = fn()
        _hechas[tarea] = _hoy
        _a.put("tareas/hechas", _hechas)
        print(json.dumps(r, ensure_ascii=False, indent=1, default=str))
        print(f"::notice::{tarea} OK: {str(r)[:1500]}")
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)[-1]
        print(f"::error::{tarea}: {type(e).__name__}: {str(e)[:400]} (en {tb.filename.split('/')[-1]}:{tb.lineno})")
        raise
