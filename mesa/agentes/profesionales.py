"""27. Herramientas profesionales de Wall Street (además del Cazador de ganadores):

1. Analistas: el consenso de los bancos (cuántos dicen "comprar") y su precio objetivo. Cuando el consenso MEJORA
   (más analistas pasan a comprar), el papel suele seguir subiendo: los fondos grandes siguen a los analistas.
   Fuente: Nasdaq (gratis), historia mensual de 13 meses.
2. Insiders: compras con plata propia de directores y gerentes de la empresa (formulario 4 de la SEC, vía
   OpenInsider). Los de adentro venden por mil motivos, pero compran por uno solo: creen que va a subir.
3. Rotación sectorial: qué sectores de EE.UU. vienen liderando en los últimos 3 meses (ETFs XLK, XLF, XLE...).
   El dinero institucional rota por sectores y los líderes suelen seguir liderando (Moskowitz y Grinblatt, 1999).

Todo se prueba contra el promedio (no alcanza con subir: tiene que ganarle a tener cualquier CEDEAR).
"""
from __future__ import annotations

import re
import statistics as st
from datetime import date, datetime, timedelta

from ..nucleo.modelos import Senal

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36", "Accept": "application/json, text/html"}
ETF_SECTOR = {"Technology": "XLK", "Health Care": "XLV", "Finance": "XLF", "Financials": "XLF", "Energy": "XLE",
              "Consumer Discretionary": "XLY", "Consumer Staples": "XLP", "Industrials": "XLI", "Utilities": "XLU",
              "Real Estate": "XLRE", "Basic Materials": "XLB", "Telecommunications": "XLC", "Communication Services": "XLC"}
NOMBRE_SECTOR = {"XLK": "Tecnología", "XLV": "Salud", "XLF": "Financiero", "XLE": "Energía", "XLY": "Consumo discrecional",
                 "XLP": "Consumo básico", "XLI": "Industria", "XLU": "Servicios públicos", "XLRE": "Inmobiliario",
                 "XLB": "Materiales", "XLC": "Comunicaciones"}
HERRAMIENTAS = {"analistas": "Mejora el consenso de analistas", "insiders": "Compras de directivos (insiders)",
                "sector": "Sector líder (rotación sectorial)"}


def _get(url: str, **kw):
    from ..datos.gratis import _S
    return _S.get(url, headers=UA, timeout=25, **kw)


# ---------- datos ----------
def sector_de(sym: str) -> str | None:
    try:
        d = _get(f"https://api.nasdaq.com/api/company/{sym}/company-profile").json().get("data") or {}
        return ((d.get("Sector") or {}).get("value") or None)
    except Exception:
        return None


def consenso(sym: str) -> dict | None:
    """Historia mensual del consenso: [{fecha, buy, hold, sell}] y precio objetivo actual."""
    try:
        d = _get(f"https://api.nasdaq.com/api/analyst/{sym}/targetprice").json().get("data") or {}
    except Exception:
        return None
    hist = []
    for h in d.get("historicalConsensus") or []:
        z = h.get("z") or {}
        try:
            f = datetime.strptime(z["date"], "%m/%d/%Y").date().isoformat()
        except Exception:
            continue
        hist.append({"fecha": f, "buy": z.get("buy") or 0, "hold": z.get("hold") or 0, "sell": z.get("sell") or 0})
    co = d.get("consensusOverview") or {}
    return {"hist": hist, "objetivo": co.get("priceTarget"), "buy": co.get("buy"), "hold": co.get("hold"), "sell": co.get("sell")}


def compras_insiders(sym: str = "", dias: int = 1461, minimo_usd: float = 100_000) -> list[dict]:
    """Compras en el mercado (tipo P) de directivos, de OpenInsider. sym vacío = todo el mercado."""
    try:
        h = _get("http://openinsider.com/screener", params={"s": sym, "fd": dias, "xp": 1, "cnt": 1000, "page": 1, "sortcol": 0,
                                                             "vl": int(minimo_usd / 1000)}).text
    except Exception:
        return []
    tabla = re.search(r'<table[^>]*class="tinytable"[^>]*>(.*?)</table>', h, re.S)
    out = []
    for f in re.findall(r"<tr[^>]*>(.*?)</tr>", tabla.group(1), re.S)[1:] if tabla else []:
        c = [re.sub(r"<[^>]+>", "", x).replace("&nbsp;", " ").strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", f, re.S)]
        if len(c) < 12 or not c[6].startswith("P"):
            continue
        tk = re.sub(r".*>", "", c[3]).strip().split()[-1] if c[3] else ""
        try:
            valor = float(re.sub(r"[^\d.]", "", c[11]) or 0)
        except ValueError:
            valor = 0
        out.append({"ticker": tk.upper(), "presentado": c[1][:10], "operacion": c[2][:10], "quien": c[4], "cargo": c[5], "valor": valor})
    return out


def lideres_sector(etfs: dict[str, list[list]], fecha: str, n: int = 3, ventana: int = 63) -> list[str]:
    r = {}
    for etf, s in etfs.items():
        x = [c for f, c in s if f <= fecha]
        if len(x) > ventana:
            r[etf] = x[-1] / x[-1 - ventana] - 1
    return sorted(r, key=r.get, reverse=True)[:n]


# ---------- prueba con la historia ----------
def _ret(serie: list[list], fecha: str, h: int) -> float | None:
    idx = next((i for i, (f, _) in enumerate(serie) if f >= fecha), None)
    if idx is None or idx + h >= len(serie):
        return None
    r = (serie[idx + h][1] / serie[idx][1] - 1) * 100
    return max(-60.0, min(100.0, r))  # datos rotos de Yahoo (splits mal ajustados) no deben dominar el promedio


def _base(precios: dict[str, list[list]], fechas: list[str], h: int) -> dict[str, float]:
    """Promedio de todo el universo para cada fecha (para medir el exceso)."""
    out = {}
    for f in fechas:
        rs = [r for s in precios.values() if (r := _ret(s, f, h)) is not None]
        if rs:
            out[f] = st.median(rs)  # el CEDEAR "típico" de ese día
    return out


def _resumen(casos: list[tuple[float, float]]) -> dict:
    if not casos:
        return {"casos": 0}
    ex = [r - b for r, b in casos]
    return {"casos": len(casos), "promedio": round(st.mean(r for r, _ in casos), 2), "exceso": round(st.mean(ex), 2),
            "exceso_mediana": round(st.median(ex), 2),
            "acierto": round(sum(1 for r, _ in casos if r > 0) / len(casos) * 100, 1),
            "le_gana": round(sum(1 for x in ex if x > 0) / len(ex) * 100, 1)}


def entrenar(precios: dict[str, list[list]], etfs: dict[str, list[list]], sectores: dict[str, str],
             consensos: dict[str, dict], insiders: list[dict]) -> dict:
    """precios: CEDEARs en dólares [[fecha, cierre]] (5 años)."""
    res = {k: {20: [], 60: []} for k in HERRAMIENTAS}
    # 1) consenso: mejora de 5 puntos o más en la proporción de "comprar" contra 3 meses antes
    for tk, co in consensos.items():
        h = co.get("hist") or []
        for i in range(3, len(h)):
            tot = lambda x: (x["buy"] + x["hold"] + x["sell"]) or 1
            p_ahora, p_antes = h[i]["buy"] / tot(h[i]), h[i - 3]["buy"] / tot(h[i - 3])
            if p_ahora - p_antes >= 0.05 and tk in precios:
                for hz in (20, 60):
                    r = _ret(precios[tk], h[i]["fecha"], hz)
                    if r is not None:
                        res["analistas"][hz].append((tk, h[i]["fecha"], r))
    # 2) insiders: desde la fecha en que se presentó (cuando el mercado se entera), una por papel y mes
    vistos = set()
    for c in insiders:
        k = (c["ticker"], c["presentado"][:7])
        if c["ticker"] in precios and k not in vistos and c["valor"] >= 100_000:
            vistos.add(k)
            for hz in (20, 60):
                r = _ret(precios[c["ticker"]], c["presentado"], hz)
                if r is not None:
                    res["insiders"][hz].append((c["ticker"], c["presentado"], r))
    # 3) sectores: cada mes, los CEDEARs de los 3 sectores líderes
    fechas_mes = sorted({f[:7] + "-01" for s in etfs.values() for f, _ in s})
    for fm in fechas_mes[4:]:
        lid = set(lideres_sector(etfs, fm))
        for tk, etf in sectores.items():
            if etf in lid and tk in precios:
                for hz in (20, 60):
                    r = _ret(precios[tk], fm, hz)
                    if r is not None:
                        res["sector"][hz].append((tk, fm, r))
    out = {"herramientas": {}}
    for k, hs in res.items():
        d = {}
        for hz, casos in hs.items():
            fechas = sorted({f for _, f, _ in casos})
            base = _base(precios, fechas, hz)
            d[hz] = _resumen([(r, base[f]) for _, f, r in casos if f in base])
        validos = [hz for hz in d if d[hz].get("casos", 0) >= 30 and d[hz]["acierto"] >= 52 and d[hz]["le_gana"] >= 50]
        plazo = max(validos or d, key=lambda hz: d[hz].get("exceso", -99)) if d else None
        out["herramientas"][k] = {"nombre": HERRAMIENTAS[k], "horizontes": d, "plazo": plazo,
                                  # además del promedio, la mediana tiene que ganar: que no dependa de 2 o 3 casos espectaculares
                                  "activa": bool(plazo in validos and d[plazo]["exceso"] >= 1.0 and d[plazo].get("exceso_mediana", 0) >= 0.25)}
    return out


# ---------- lo de hoy ----------
def lista_hoy(precios_hoy: dict[str, float], consensos: dict[str, dict], insiders_rec: list[dict], sectores: dict[str, str],
              lideres: list[str]) -> dict[str, dict]:
    """{ticker: {herramienta: motivo}} con lo que cada herramienta marca hoy."""
    out: dict[str, dict] = {}
    for tk, co in consensos.items():
        h = co.get("hist") or []
        if len(h) >= 4:
            tot = lambda x: (x["buy"] + x["hold"] + x["sell"]) or 1
            dif = h[-1]["buy"] / tot(h[-1]) - h[-4]["buy"] / tot(h[-4])
            if dif >= 0.05:
                pot = (co["objetivo"] / precios_hoy[tk] - 1) * 100 if co.get("objetivo") and precios_hoy.get(tk) else None
                out.setdefault(tk, {})["analistas"] = (f"{dif * 100:+.0f} puntos más de analistas que dicen comprar en 3 meses"
                                                      + (f"; precio objetivo promedio {pot:+.0f}% arriba" if pot is not None else ""))
    for c in insiders_rec:
        if c["ticker"] in sectores or c["ticker"] in precios_hoy:
            prev = out.setdefault(c["ticker"], {}).get("insiders")
            txt = f"{c['quien']} ({c['cargo']}) compró US$ {c['valor']:,.0f} el {c['operacion'][8:10]}/{c['operacion'][5:7]}".replace(",", ".")
            out[c["ticker"]]["insiders"] = (prev + "; " + txt) if prev else txt
    for tk, etf in sectores.items():
        if etf in lideres:
            out.setdefault(tk, {})["sector"] = f"su sector ({NOMBRE_SECTOR.get(etf, etf)}) está entre los 3 que más subieron en 3 meses"
    return out


def senales(lista: dict[str, dict], prueba: dict, existe) -> list[Senal]:
    her = (prueba or {}).get("herramientas") or {}
    out = []
    for tk, ev in lista.items():
        act = [k for k in ev if (her.get(k) or {}).get("activa")]
        if not act or not existe(tk):
            continue
        hz = lambda k: her[k]["horizontes"].get(str(her[k]["plazo"])) or her[k]["horizontes"].get(her[k]["plazo"]) or {}
        exc = max(hz(k).get("exceso", 0) for k in act)
        out.append(Senal("profesionales", tk, 1, round(min(0.8, 0.3 + 0.12 * len(act) + exc / 20), 2),
                         "Herramientas de Wall Street — " + "; ".join(f"{HERRAMIENTAS[k]}: {ev[k]}" for k in act)
                         + f". En la historia le ganó {exc:+.1f}% al promedio.", {"herramientas": act, "plazo": max(her[k]["plazo"] for k in act)}))
    return out


# ---------- datos guardados (para no repetir consultas) ----------
def _sym(tk: str) -> str:
    return tk.replace("-", ".")


def asegurar_datos(a, uni: list[str], hoy: date, forzar: bool = False) -> dict:
    """Sectores (se piden una sola vez), consensos (una vez por semana) y compras de insiders del último mes (cada día)."""
    from concurrent.futures import ThreadPoolExecutor
    sect = a.get("profesionales/sectores") or {}
    faltan = [t for t in uni if t not in sect]
    if faltan:
        with ThreadPoolExecutor(6) as ex:
            for t, s in zip(faltan, ex.map(lambda t: sector_de(_sym(t)), faltan)):
                sect[t] = ETF_SECTOR.get(s or "", None)
        a.put("profesionales/sectores", sect)
    cons = a.get("profesionales/consensos") or {}
    if forzar or not cons.get("fecha") or cons["fecha"] < (hoy - timedelta(days=7)).isoformat() or set(uni) - set(cons.get("datos") or {}):
        with ThreadPoolExecutor(6) as ex:
            datos = {t: c for t, c in zip(uni, ex.map(lambda t: consenso(_sym(t)), uni)) if c and c.get("hist")}
        cons = {"fecha": hoy.isoformat(), "datos": {**(cons.get("datos") or {}), **datos}}
        a.put("profesionales/consensos", cons)
    ins = a.get("profesionales/insiders_rec") or {}
    if forzar or ins.get("fecha") != hoy.isoformat():
        u = set(uni)
        rec = [c for c in compras_insiders("", 30, 100_000) if c["ticker"] in u or c["ticker"].replace(".", "-") in u]
        ins = {"fecha": hoy.isoformat(), "lista": rec}
        a.put("profesionales/insiders_rec", ins)
    return {"sectores": sect, "consensos": cons.get("datos") or {}, "insiders": ins.get("lista") or []}


def armar_lista(a, uni: list[str], ultimos: dict[str, float], hoy: date) -> dict:
    """Lista del día (corre en el cierre): qué marca cada herramienta y cuáles son los sectores líderes."""
    from ..datos import gratis
    d = asegurar_datos(a, uni, hoy)
    etfs = {e: gratis.yahoo(e, "1y") for e in NOMBRE_SECTOR}
    lid = lideres_sector(etfs, hoy.isoformat())
    rs = {e: round((s[-1][1] / s[-64][1] - 1) * 100, 1) for e, s in etfs.items() if len(s) > 64}
    lista = lista_hoy(ultimos, d["consensos"], d["insiders"], d["sectores"], lid)
    out = {"fecha": hoy.isoformat(), "lideres": lid, "sectores_3m": dict(sorted(rs.items(), key=lambda x: -x[1])),
           "nombres": {e: NOMBRE_SECTOR[e] for e in NOMBRE_SECTOR}, "lista": lista}
    a.put("profesionales/lista", out)
    return out


def entrenar_todo(a, precios5: dict[str, list[list]], hoy: date) -> dict:
    """Prueba de las 3 herramientas con la historia (viernes). precios5: {tk: [[fecha, cierre]]} 5 años en dólares."""
    from concurrent.futures import ThreadPoolExecutor
    from ..datos import gratis
    uni = list(precios5)
    d = asegurar_datos(a, uni, hoy, forzar=True)
    etfs = {e: gratis.yahoo(e, "5y") for e in NOMBRE_SECTOR}
    hist_ins = a.get("profesionales/insiders_hist") or {}
    if not hist_ins.get("fecha") or hist_ins["fecha"] < (hoy - timedelta(days=28)).isoformat():
        with ThreadPoolExecutor(4) as ex:
            todas = [c for l in ex.map(lambda t: compras_insiders(_sym(t), 1461, 100_000), uni) for c in l]
        hist_ins = {"fecha": hoy.isoformat(), "lista": todas}
        a.put("profesionales/insiders_hist", hist_ins)
    ins = [{**c, "ticker": c["ticker"].replace(".", "-") if c["ticker"].replace(".", "-") in precios5 else c["ticker"]}
           for c in hist_ins.get("lista") or []]
    res = entrenar(precios5, etfs, {k: v for k, v in d["sectores"].items() if v}, d["consensos"], ins)
    res["fecha"] = hoy.isoformat()
    res["datos"] = {"consensos": len(d["consensos"]), "insiders": len(ins), "sectores": sum(1 for v in d["sectores"].values() if v)}
    a.put("profesionales/prueba", res)
    return res
