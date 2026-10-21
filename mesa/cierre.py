"""Tareas fuera de la ronda.

python -m mesa.cierre diario         17:10 — velas del día (gratis con el panel), seguimiento, señales, riesgo país
python -m mesa.cierre calificadoras  10:00 — Calificadoras (1 vez por día)
python -m mesa.cierre semanal        viernes — ranking e incentivos
python -m mesa.cierre mensual        1er día hábil — capacitación (queda pendiente de tu aprobación)
"""
from __future__ import annotations

import json
import sys

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
    for titulos in paneles.values():
        for t in titulos:
            s = t.get("simbolo")
            if not s or not t.get("ultimo"):
                continue
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
        nuevos = 0
        for t in candidatos[:12]:
            if not consumo.puede_consultar(1):
                break
            cache.asegurar(t["simbolo"], 1)
            nuevos += 1 if cache.velas(t["simbolo"]) else 0
        print(f"[cierre] historial nuevo: {nuevos} (más operados)")

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
    return {"cambios": len(res.get("cambios", [])), "licitacion": (lic.get("proxima") or {}).get("fecha")}


def semanal() -> list[dict]:
    a = almacen_por_defecto()
    reg = Registro(a)
    reg.recalibrar()
    return reg.cerrar_ranking_semanal()


def entrenar() -> dict:
    """Entrenamiento con la historia: hace opinar a los agentes en cada día pasado y mide cuánto acertaron."""
    from .nucleo import calibracion
    a = almacen_por_defecto()
    cache = CacheHistorico(a)
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    grupos = {tk: x[4] for tk, x in panel.items()}
    series = {tk: cache.velas(tk) for tk in cache.indice}
    hist = calibracion.entrenar_con_historia(series, grupos, a.get("params/agentes") or {})
    a.put("ranking/stats_historicas", hist)
    reg = Registro(a)
    cal = reg.recalibrar()
    a.put("ranking/tabla", reg.ranking())
    resumen = {ag: f"{c['acierto_pct']}% de {c['casos']} casos ({c['fuente']}) -> voto x{c['factor']}" for ag, c in cal.items()}
    return {"series": len(series), "calibracion": resumen}


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
    import traceback
    try:
        r = fn()
        print(json.dumps(r, ensure_ascii=False, indent=1, default=str))
        print(f"::notice::{tarea} OK: {str(r)[:1500]}")
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)[-1]
        print(f"::error::{tarea}: {type(e).__name__}: {str(e)[:400]} (en {tb.filename.split('/')[-1]}:{tb.lineno})")
        raise
