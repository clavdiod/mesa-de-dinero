"""Fuentes gratuitas (no consumen el cupo de IOL): dólares, riesgo país, BCRA y noticias por RSS."""
from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import requests

from ..nucleo.config import config

_UA = {"User-Agent": "mesa-de-dinero/1.0 (+uso personal)"}


from ..nucleo.http import sesion as _sesion

_S = _sesion()


def _json(url: str):
    r = _S.get(url, timeout=20, headers=_UA)
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
            r = _S.get(url, timeout=20, headers=_UA)
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


def data912(grupo: str) -> list[dict]:
    """Panel gratis de data912 (ONs, letras). Mismo formato normalizado que IOL."""
    url = (config()["fuentes"].get("data912") or {}).get(grupo)
    if not url:
        return []
    try:
        filas = _json(url)
    except Exception as e:
        print(f"[data912] {grupo}: {e}")
        return []
    out = []
    for f in filas or []:
        ult = f.get("c")
        if not f.get("symbol") or not ult:
            continue
        var = f.get("pct_change")
        out.append({"simbolo": f["symbol"], "ultimo": float(ult), "variacion": float(var) if var is not None else None,
                    "compra": f.get("px_bid") or None, "venta": f.get("px_ask") or None,
                    "volumen": f.get("v"), "monto": None, "apertura": None, "maximo": None, "minimo": None,
                    "cierre_anterior": None, "fuente": "data912",
                    "puntas_compra": [], "puntas_venta": []})
    return out


# ---------- historial de CEDEARs: precio en EE.UU. × CCL de cada día (gratis, sin IOL) ----------
_UA_JSON = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "application/json"}
_CCL: dict[str, float] | None = None


def _num_usd(x) -> float | None:
    try:
        return float(str(x).replace("$", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def precios_eeuu(simbolo: str, dias: int = 420) -> list[dict]:
    """Velas diarias en dólares de una acción de EE.UU. Nasdaq primero; si falla, Yahoo."""
    from datetime import date, timedelta
    hasta = date.today()
    desde = hasta - timedelta(days=dias)
    try:
        r = _S.get(f"https://api.nasdaq.com/api/quote/{simbolo}/historical?assetclass=stocks&fromdate={desde}&todate={hasta}&limit=1000",
                   headers=_UA_JSON, timeout=30)
        filas = ((r.json().get("data") or {}).get("tradesTable") or {}).get("rows") or [] if r.ok else []
        out = []
        for f in filas:
            m, d, y = str(f.get("date", "")).split("/") if f.get("date") else ("", "", "")
            c = _num_usd(f.get("close"))
            if y and c:
                out.append({"fecha": f"{y}-{m}-{d}", "apertura": _num_usd(f.get("open")) or c, "maximo": _num_usd(f.get("high")) or c,
                            "minimo": _num_usd(f.get("low")) or c, "cierre": c})
        if len(out) > 100:
            return sorted(out, key=lambda v: v["fecha"])
    except Exception as e:
        print(f"[eeuu] nasdaq {simbolo}: {e}")
    try:
        from datetime import datetime, timezone
        r = _S.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}?range=2y&interval=1d", headers=_UA_JSON, timeout=30)
        res = ((r.json().get("chart") or {}).get("result") or [None])[0]
        q = res["indicators"]["quote"][0]
        out = []
        for i, ts in enumerate(res["timestamp"]):
            c = q["close"][i]
            if c:
                out.append({"fecha": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(), "apertura": q["open"][i] or c,
                            "maximo": q["high"][i] or c, "minimo": q["low"][i] or c, "cierre": c})
        return [v for v in out if v["fecha"] >= desde.isoformat()]
    except Exception as e:
        print(f"[eeuu] yahoo {simbolo}: {e}")
        return []


def ccl_historico() -> dict[str, float]:
    """fecha -> dólar CCL (venta), de argentinadatos. Se baja una vez por proceso."""
    global _CCL
    if _CCL is None:
        try:
            _CCL = {d["fecha"]: float(d["venta"]) for d in _json("https://api.argentinadatos.com/v1/cotizaciones/dolares/contadoconliqui")
                    if d.get("venta")}
        except Exception as e:
            print(f"[ccl] {e}")
            _CCL = {}
    return _CCL


def historial_cedear(simbolo: str, precio_hoy_ars: float) -> list[dict]:
    """Historial en pesos de un CEDEAR = precio en EE.UU. × CCL de ese día, escalado para que el último
    día coincida con el precio actual del CEDEAR (absorbe el ratio de conversión)."""
    us, ccl = precios_eeuu(simbolo), ccl_historico()
    if len(us) < 100 or not ccl or not precio_hoy_ars:
        return []
    fechas_ccl = sorted(ccl)
    def ccl_de(f):
        import bisect
        i = bisect.bisect_right(fechas_ccl, f) - 1
        return ccl[fechas_ccl[i]] if i >= 0 else None
    crudo = [(v, ccl_de(v["fecha"])) for v in us]
    crudo = [(v, c) for v, c in crudo if c]
    if not crudo:
        return []
    ult, c_ult = crudo[-1]
    k = precio_hoy_ars / (ult["cierre"] * c_ult)
    return [{"fecha": v["fecha"], "apertura": round(v["apertura"] * c * k, 4), "maximo": round(v["maximo"] * c * k, 4),
             "minimo": round(v["minimo"] * c * k, 4), "cierre": round(v["cierre"] * c * k, 4), "volumen": 0}
            for v, c in crudo]


def series_macro(anios: int = 3) -> dict:
    """Riesgo país, CCL, oficial (diarios) e inflación (mensual), de argentinadatos. fecha -> valor."""
    from datetime import date, timedelta
    desde = (date.today() - timedelta(days=365 * anios)).isoformat()
    base = "https://api.argentinadatos.com/v1"
    out = {}
    for nombre, url, campo in (("riesgo_pais", f"{base}/finanzas/indices/riesgo-pais", "valor"),
                               ("ccl", f"{base}/cotizaciones/dolares/contadoconliqui", "venta"),
                               ("oficial", f"{base}/cotizaciones/dolares/oficial", "venta"),
                               ("inflacion", f"{base}/finanzas/indices/inflacion", "valor")):
        try:
            out[nombre] = {d["fecha"]: float(d[campo]) for d in _json(url) if d.get(campo) is not None and d["fecha"] >= desde}
        except Exception as e:
            print(f"[macro] {nombre}: {e}")
            out[nombre] = {}
    return out


def yahoo(simbolo: str, rango: str = "2y") -> list[list]:
    """[[fecha, cierre], ...] diario de Yahoo (gratis). Índices con ^ (ej. ^VIX)."""
    from datetime import datetime, timezone
    from urllib.parse import quote
    try:
        r = _S.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(simbolo)}?range={rango}&interval=1d", headers=_UA_JSON, timeout=30)
        res = r.json()["chart"]["result"][0]
        cierres = res["indicators"]["quote"][0]["close"]
        return [[datetime.fromtimestamp(ts, timezone.utc).date().isoformat(), round(c, 4)]
                for ts, c in zip(res["timestamp"], cierres) if c]
    except Exception as e:
        print(f"[yahoo] {simbolo}: {e}")
        return []


def datos_wallstreet(universo: list[str], rango: str = "2y") -> dict:
    """Índices (S&P, VIX, tasa 10 años, sectores) y precios en dólares de los CEDEARs del universo."""
    from ..agentes.wallstreet import INDICES
    from datetime import date
    idx = {s: yahoo(s, rango) for s in INDICES}
    precios = {}
    for tk in universo:
        x = yahoo(tk.replace(".", "-"), rango)
        if len(x) >= 260:
            precios[tk] = x
    return {"fecha": date.today().isoformat(), "indices": idx, "precios": precios}


def dolar_cripto_historico() -> dict[str, float]:
    try:
        return {d["fecha"]: float(d["venta"]) for d in _json("https://api.argentinadatos.com/v1/cotizaciones/dolares/cripto") if d.get("venta")}
    except Exception as e:
        print(f"[cripto] dólar cripto: {e}")
        return {}


def yahoo_vivo(simbolo: str) -> dict:
    """Precio actual (o último) y cierre anterior de Yahoo. {'precio', 'anterior', 'hora'}"""
    from urllib.parse import quote
    try:
        r = _S.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(simbolo)}?range=1d&interval=5m", headers=_UA_JSON, timeout=20)
        m = r.json()["chart"]["result"][0]["meta"]
        return {"precio": m.get("regularMarketPrice"), "anterior": m.get("chartPreviousClose") or m.get("previousClose"),
                "hora": m.get("regularMarketTime")}
    except Exception as e:
        print(f"[yahoo vivo] {simbolo}: {e}")
        return {}
