"""Fuentes gratuitas (no consumen el cupo de IOL): dólares, riesgo país, BCRA y noticias por RSS."""
from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import requests

from ..nucleo.config import config

_UA = {"User-Agent": "mesa-de-dinero/1.0 (+uso personal)"}


def _json(url: str):
    r = requests.get(url, timeout=20, headers=_UA)
    r.raise_for_status()
    return r.json()


def dolares() -> dict:
    """{'oficial': {...}, 'bolsa': {...}, 'contadoconliqui': {...}, ...} con compra/venta."""
    out = {}
    try:
        for d in _json(config()["fuentes"]["dolares"]):
            out[d.get("casa")] = {"compra": d.get("compra"), "venta": d.get("venta"),
                                  "fecha": d.get("fechaActualizacion")}
    except Exception as e:  # la mesa sigue aunque falte una fuente
        out["_error"] = str(e)
    return out


def riesgo_pais() -> dict:
    try:
        d = _json(config()["fuentes"]["riesgo_pais"])
        return {"valor": d.get("valor"), "fecha": d.get("fecha")}
    except Exception as e:
        return {"valor": None, "_error": str(e)}


def bcra_reservas() -> dict:
    """Reservas internacionales (variable 1 de la API de estadísticas del BCRA)."""
    try:
        d = _json(config()["fuentes"]["bcra"])
        for v in d.get("results", []):
            if v.get("idVariable") == 1:
                return {"valor": v.get("valor"), "fecha": v.get("fecha")}
    except Exception as e:
        return {"valor": None, "_error": str(e)}
    return {"valor": None}


def _limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", texto or ""))).strip()


def noticias(urls: list[str] | None = None, horas: int = 24, max_items: int = 60) -> list[dict]:
    import feedparser

    urls = urls or config()["fuentes"]["rss_noticias"]
    limite = datetime.now(timezone.utc) - timedelta(hours=horas)
    items = []
    for url in urls:
        try:
            r = requests.get(url, timeout=20, headers=_UA)
            feed = feedparser.parse(r.content)
        except Exception:
            continue
        for e in feed.entries:
            fecha = None
            if getattr(e, "published_parsed", None):
                fecha = datetime(*e.published_parsed[:6], tzinfo=timezone.utc)
                if fecha < limite:
                    continue
            items.append({"titulo": _limpiar(e.get("title", "")), "resumen": _limpiar(e.get("summary", ""))[:400],
                          "link": e.get("link"), "fecha": fecha.isoformat() if fecha else None,
                          "fuente": url.split("/")[2]})
    # sin duplicados por título
    vistos, unicos = set(), []
    for it in items:
        k = it["titulo"].lower()
        if k and k not in vistos:
            vistos.add(k)
            unicos.append(it)
    return unicos[:max_items]


def buscar_noticias(consulta: str, horas: int = 72, max_items: int = 10) -> list[dict]:
    url = config()["fuentes"]["google_news"].format(q=quote_plus(consulta))
    return noticias([url], horas=horas, max_items=max_items)
