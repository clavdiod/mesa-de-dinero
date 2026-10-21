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


def yahoo_vivo(simbolo: str, prepost: bool = False) -> dict:
    """Precio actual y cierre anterior de Yahoo. Con prepost=True incluye el pre-market (antes de las 10:30 ART)."""
    from urllib.parse import quote
    try:
        extra = "&includePrePost=true" if prepost else ""
        r = _S.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(simbolo)}?range=1d&interval=5m{extra}", headers=_UA_JSON, timeout=20)
        res = r.json()["chart"]["result"][0]
        m = res["meta"]
        precio = m.get("regularMarketPrice")
        if prepost:
            cl = [c for c in (res["indicators"]["quote"][0].get("close") or []) if c]
            precio = cl[-1] if cl else precio
        return {"precio": precio, "anterior": m.get("chartPreviousClose") or m.get("previousClose"),
                "hora": m.get("regularMarketTime")}
    except Exception as e:
        print(f"[yahoo vivo] {simbolo}: {e}")
        return {}


def yahoo_varios(simbolos: list[str], prepost: bool = False, hilos: int = 8) -> dict[str, dict]:
    """Varios precios en vivo en paralelo (Yahoo, gratis)."""
    from concurrent.futures import ThreadPoolExecutor
    simbolos = list(dict.fromkeys(simbolos))
    with ThreadPoolExecutor(hilos) as ex:
        res = list(ex.map(lambda s: yahoo_vivo(s.replace(".", "-"), prepost), simbolos))
    return {s: r for s, r in zip(simbolos, res) if r.get("precio")}


def yahoo_ohlcv(simbolo: str, rango: str = "5y") -> list[dict]:
    """Velas diarias completas [{fecha, c, h, l, v}] de Yahoo."""
    from datetime import datetime, timezone
    from urllib.parse import quote
    try:
        r = _S.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(simbolo)}?range={rango}&interval=1d", headers=_UA_JSON, timeout=30)
        res = r.json()["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        out = []
        for k, ts in enumerate(res["timestamp"]):
            c = q["close"][k]
            if c:
                out.append({"fecha": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(), "c": round(c, 4),
                            "h": round(q["high"][k] or c, 4), "l": round(q["low"][k] or c, 4), "v": q["volume"][k] or 0})
        return out
    except Exception as e:
        print(f"[yahoo ohlcv] {simbolo}: {e}")
        return []


# ---------- Licitaciones del día (MAE / A3 Mercados: ONs, fideicomisos, Tesoro, provincias) ----------
_MAE = "https://api.marketdata.mae.com.ar/api/"
_MAE_H = {"Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}


def _clase_licitacion(titulo: str) -> str:
    t = titulo.upper().strip()
    if "MINISTERIO DE ECONOM" in t or "TESORO" in t:
        return "Tesoro"
    if "PROVINCIA" in t or "CIUDAD" in t or "MUNICIPALIDAD" in t:
        return "Provincia"
    if t.startswith("ON") or " ON " in t or "OBLIGACIONES NEGOCIABLES" in t:
        return "ON"
    if t.startswith("FF") or "FIDEICOMISO" in t:
        return "Fideicomiso"
    if t.startswith("VCP") or "VALORES DE CORTO PLAZO" in t:
        return "VCP"
    return "Otra"


def _hora_art(iso: str | None) -> tuple[str, str]:
    """'2026-10-23T13:00:00Z' -> ('2026-10-23', '10:00') en hora argentina (UTC-3)."""
    if not iso:
        return "", ""
    d = datetime.fromisoformat(iso.replace("Z", "+00:00")) - timedelta(hours=3)
    return d.date().isoformat(), d.strftime("%H:%M")


def licitaciones_mae(desde, hasta, detalle_dias: int = 10, max_detalles: int = 25) -> list[dict]:
    """Calendario público de licitaciones del MAE (gratis, no usa consultas de IOL).
    Para las cercanas trae el detalle: emisor, moneda, monto, qué se licita (tasa/precio), liquidación."""
    r = _S.get(_MAE + "mercado/licitaciones", headers=_MAE_H, timeout=30,
               params={"fechaDesde": desde.isoformat(), "fechaHasta": hasta.isoformat()})
    r.raise_for_status()
    out, pedidos = [], 0
    lim_det = (desde + timedelta(days=detalle_dias)).isoformat()
    for e in r.json().get("events") or []:
        titulo = " ".join(str(e.get("title") or "").split())
        clase = _clase_licitacion(titulo)
        fecha, hora_ini = _hora_art(e.get("start"))
        _, hora_fin = _hora_art(e.get("end"))
        ev = {"fecha": fecha, "tipo": "licitacion", "clase": clase, "id": e.get("id"), "titulo": titulo,
              "hora_inicio": hora_ini if clase not in ("Tesoro", "Provincia") else "",
              "hora_cierre": hora_fin if clase not in ("Tesoro", "Provincia") else ""}
        if clase not in ("Tesoro", "Provincia") and fecha <= lim_det and pedidos < max_detalles:
            pedidos += 1
            try:
                d = _S.get(_MAE + f"mercado/licitacion/{e['id']}", headers=_MAE_H, timeout=20).json()
                ev.update({"emisor": " ".join(str(d.get("emisor") or "").split()), "moneda": d.get("moneda"),
                           "monto": d.get("montoaLicitar"), "licita": (d.get("variableLicitar") or "").lower(),
                           "liquidacion": _hora_art(d.get("fechaLiquidacion"))[0], "estado": d.get("estado"),
                           "modalidad": d.get("modalidad"), "colocador": " ".join(str(d.get("colocador") or "").split()),
                           "segmento": d.get("tipo")})
            except Exception as ex:
                print(f"[mae] detalle {e.get('id')}: {ex}")
        ev["nombre"] = nombre_licitacion(ev)
        out.append(ev)
    out.sort(key=lambda x: (x["fecha"], x.get("hora_cierre") or ""))
    return out


def nombre_licitacion(e: dict) -> str:
    t = e["titulo"]
    if t.isupper():
        siglas = {"ON", "FF", "VCP", "SA", "S.A.", "PYME", "USD", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"}
        t = " ".join(w if w in siglas else w.capitalize() for w in t.split())
    if e["clase"] == "Tesoro":
        return "Licitación del Tesoro (Ministerio de Economía: LECAP, BONCAP, CER, duales)"
    if e["clase"] == "Provincia":
        return "Licitación de la Provincia de Buenos Aires" if "BUENOS AIRES" in e["titulo"].upper() else f"Licitación: {t}"
    partes = [f"Licitación {t}"]
    det = []
    if e.get("moneda"):
        det.append("en dólares" if "USD" in str(e["moneda"]).upper() else "en pesos" if "ARS" in str(e["moneda"]).upper() or "PESO" in str(e["moneda"]).upper() else str(e["moneda"]))
    if e.get("licita"):
        det.append(f"se licita {e['licita']}")
    if e.get("monto"):
        det.append(f"por {e['monto']:,.0f}".replace(",", "."))
    if e.get("hora_cierre"):
        det.append(f"de {e.get('hora_inicio')} a {e['hora_cierre']} h")
    if e.get("liquidacion"):
        det.append(f"liquida {e['liquidacion'][8:10]}/{e['liquidacion'][5:7]}")
    if det:
        partes.append(" · ".join(det))
    return " — ".join(partes)


# ---------- MAE: panel y cierres de renta fija, avisos de pago y de licitaciones (gratis) ----------
def ticker_mae_a_byma(cod: str, moneda: str | None, existentes=None) -> str:
    """MAE informa el código y la moneda por separado; en BYMA la moneda va en la letra final.
    AL30 + D -> AL30D; YM44O + D -> YM44D (ON: la O es la línea en pesos)."""
    tk, m = cod.strip().upper(), (moneda or "$").strip().upper()
    if m in ("$", "P", "ARS", ""):
        return tk
    suf = "D" if m == "D" else "C"
    cands = ([tk[:-1] + suf] if tk.endswith("O") else []) + [tk if tk.endswith(suf) else tk + suf]
    if existentes is not None:
        for c in cands:
            if c in existentes:
                return c
    return cands[0]


def escala_mae(moneda: str | None) -> float:
    """MAE da las líneas en dólares por 1 nominal; BYMA cada 100."""
    return 100.0 if (moneda or "$").strip().upper() in ("D", "C") else 1.0


def mae_panel_rf() -> list[dict]:
    r = _S.get(_MAE + "mercado/datos/RF", headers=_MAE_H, timeout=30)
    r.raise_for_status()
    return r.json() or []


def mae_cierres(desde, hasta) -> list[dict]:
    """Precios de cierre de toda la renta fija operada en MAE entre dos fechas (una sola consulta)."""
    import json as _json
    o = _json.dumps({"fechaDesde": desde.isoformat(), "fechaHasta": hasta.isoformat()}, separators=(",", ":"))
    r = _S.get(_MAE + f"mercado/historico/preciocierre?oTitulo={o}", headers=_MAE_H, timeout=120)
    r.raise_for_status()
    return r.json() or []


def mae_documentos(ruta: str) -> list[dict]:
    """Listados de documentos públicos: 'pagoamortizrenta' (avisos de pago), 'boletin-mpmae' (licitaciones), 'inforelevante'."""
    r = _S.get(_MAE + f"mercado/{ruta}", headers=_MAE_H, timeout=30)
    r.raise_for_status()
    return r.json() or []
