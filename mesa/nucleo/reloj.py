"""Horario de mercado, feriados y frecuencia adaptativa."""
from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import requests

from .config import config

TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def ahora() -> datetime:
    return datetime.now(TZ)


def _hhmm(s: str) -> time:
    h, m = s.split(":")
    return time(int(h), int(m))


def feriados(anio: int, almacen=None) -> set[str]:
    """Feriados nacionales. Se guardan en el almacén para no consultarlos de nuevo en el año."""
    clave = f"ref/feriados_{anio}"
    if almacen is not None:
        guardado = almacen.get(clave)
        if guardado is not None:
            return set(guardado)
    fechas: set[str] = set()
    try:
        url = config()["fuentes"]["feriados"].format(anio=anio)
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        fechas = {f["fecha"] for f in r.json() if "fecha" in f}
        if almacen is not None and fechas:
            almacen.put(clave, sorted(fechas))
    except Exception:
        pass  # si falla, la ronda igual detecta mercado cerrado porque no hay operaciones
    return fechas


def es_dia_habil(d: date, almacen=None) -> bool:
    if d.weekday() >= 5:
        return False
    return d.isoformat() not in feriados(d.year, almacen)


def en_horario(dt: datetime | None = None) -> bool:
    dt = dt or ahora()
    c = config()["mercado"]
    return _hhmm(c["apertura"]) <= dt.time() <= _hhmm(c["cierre"])


def intervalo_minutos(dt: datetime | None = None) -> int:
    """5 min en la primera y última hora, 10 al mediodía (configurable)."""
    dt = dt or ahora()
    f = config()["frecuencia"]
    t = dt.time()
    if t < time(11, 30):
        return f["primera_hora_min"]
    if t >= time(16, 0):
        return f["ultima_hora_min"]
    return f["mediodia_min"]


def toca_correr(dt: datetime | None = None, factor: int = 1) -> bool:
    """El cron dispara cada 5 min; esto decide si esta ronda corre o se saltea para ahorrar consultas.

    `factor` multiplica el intervalo cuando el presupuesto mensual de IOL viene ajustado.
    Usa minutos desde la apertura para que las rondas queden alineadas aunque el cron se atrase.
    """
    dt = dt or ahora()
    if not en_horario(dt):
        return False
    ap = _hhmm(config()["mercado"]["apertura"])
    minutos = (dt.hour * 60 + dt.minute) - (ap.hour * 60 + ap.minute)
    paso = intervalo_minutos(dt) * max(1, factor)
    # tolerancia de 2 minutos por atrasos del cron
    return (minutos % paso) <= 2
