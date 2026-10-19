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
    res = con_ia.calificadoras(IA(), a, ahora().date())
    return {"cambios": len(res.get("cambios", []))}


def semanal() -> list[dict]:
    a = almacen_por_defecto()
    return Registro(a).cerrar_ranking_semanal()


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
    fn = {"diario": diario, "calificadoras": calificadoras, "semanal": semanal, "mensual": mensual}[tarea]
    print(json.dumps(fn(), ensure_ascii=False, indent=1, default=str))
