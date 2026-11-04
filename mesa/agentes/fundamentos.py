"""Fundamentos de los CEDEARs (04/11): P/E, crecimiento de ganancias, PEG, flujo de caja libre y si es cíclica.

Fuente gratis: las ganancias que cada empresa publica en la SEC de EE.UU. (companyfacts) y el precio de Yahoo.
Es SOLO un dato para leer, sin voto: en 10 años de historia (53 empresas, 4.085 meses) lo barato no rindió más
ni lo caro menos a 3 meses (ver Aprendizajes 04/11). La base de la SEC se refresca una vez por semana por empresa.
"""
from __future__ import annotations

from datetime import date, timedelta
from statistics import mean, pstdev

from ..datos.gratis import _S, yahoo_varios

H = {"User-Agent": "MesaDeDinero research bot (uso personal, sin fines comerciales)", "Accept": "application/json"}
CLAVE = "fundamentos/cedears"
NO_EMPRESA = {"SPY", "QQQ", "DIA", "IWM", "GLD", "SLV", "EWZ", "XLE", "ARKK", "IBB", "BITO", "IBIT", "ETHA", "EEM", "XLF", "SMH", "URA"}


def _ciks() -> dict[str, str]:
    j = _S.get("https://www.sec.gov/files/company_tickers.json", headers=H, timeout=30).json()
    return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in j.values()}


def _periodos(unidades: list[dict], dmin: int, dmax: int) -> list[tuple[str, float]]:
    """(fin, valor) de los períodos de esa duración, la primera vez que se publicó cada uno."""
    q: dict[str, tuple[str, float]] = {}
    for x in unidades or []:
        if not (x.get("start") and x.get("end") and x.get("filed")):
            continue
        d = (date.fromisoformat(x["end"]) - date.fromisoformat(x["start"])).days
        if dmin <= d <= dmax:
            q[x["end"]] = min(q.get(x["end"], (x["filed"], x["val"])), (x["filed"], x["val"]))
    return sorted((e, v) for e, (_, v) in q.items())


def base_sec(cik: str) -> dict | None:
    """Lo que no cambia con el precio: ganancias 12m, crecimiento, si es cíclica, flujo de caja libre por acción."""
    j = _S.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=H, timeout=40).json()
    g = j.get("facts", {}).get("us-gaap", {})
    u = lambda k, un="USD": ((g.get(k) or {}).get("units") or {}).get(un) or []
    eps = _periodos(u("EarningsPerShareDiluted", "USD/shares") or u("EarningsPerShareBasic", "USD/shares"), 80, 100)
    if len(eps) < 8:
        return None
    v = [x for _, x in eps]
    ttm, ant = sum(v[-4:]), sum(v[-8:-4])
    ult5 = v[-20:]
    out = {"eps_12m": round(ttm, 4), "al": eps[-1][0],
           "crec": round(ttm / ant - 1, 4) if ant > 0 and ttm > 0 else None,
           "ciclica": bool(pstdev(ult5) / (abs(mean(ult5)) + 1e-9) > 0.8)}
    ocf = _periodos(u("NetCashProvidedByUsedInOperatingActivities"), 350, 380)
    capex = dict(_periodos(u("PaymentsToAcquirePropertyPlantAndEquipment"), 350, 380))
    acc = ((j.get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding") or {}).get("units") or {}).get("shares") or []
    acciones = max(acc, key=lambda x: x.get("end", ""))["val"] if acc else None
    if ocf and acciones:
        fin, o = ocf[-1]
        out["fcf_accion"] = round((o - capex.get(fin, 0)) / acciones, 4)
    return out


def actualizar(a, universo: list[str], hoy: date, maximo: int = 40) -> dict:
    """Refresca la base de la SEC (semanal, hasta `maximo` empresas por día) y recalcula P/E y PEG con el precio de hoy."""
    from concurrent.futures import ThreadPoolExecutor
    tabla = a.get(CLAVE) or {}
    emp = [t for t in universo if t not in NO_EMPRESA]
    viejo = (hoy - timedelta(days=7)).isoformat()
    pend = [t for t in emp if (tabla.get(t) or {}).get("sec_fecha", "") < viejo][:maximo]
    if pend:
        try:
            cik = _ciks()
        except Exception as ex:
            print(f"[fundamentos] SEC: {ex}")
            cik = {}

        def uno(t):
            c = cik.get(t.replace(".", "-"))
            try:
                return t, (base_sec(c) if c else None)
            except Exception as ex:
                print(f"[fundamentos] {t}: {ex}")
                return t, False

        with ThreadPoolExecutor(4) as ex:  # la SEC pide no pasar de 10 consultas por segundo
            for t, b in ex.map(uno, pend):
                if b is False:
                    continue  # error de red: se reintenta otro día
                tabla[t] = {**(b or {"sin_datos": True}), "sec_fecha": hoy.isoformat()}
    precios = yahoo_varios([t for t in emp if (tabla.get(t) or {}).get("eps_12m")])
    for t, p in precios.items():
        f = tabla[t]
        pr = p["precio"]
        f["precio_usd"] = round(pr, 2)
        f["pe"] = round(pr / f["eps_12m"], 1) if f["eps_12m"] > 0 else None
        f["peg"] = round(f["pe"] / (f["crec"] * 100), 2) if f.get("pe") and (f.get("crec") or 0) > 0 else None
        f["fcf_rinde"] = round(f["fcf_accion"] / pr * 100, 1) if f.get("fcf_accion") is not None and pr else None
        f["fecha"] = hoy.isoformat()
    a.put(CLAVE, tabla)
    print(f"[fundamentos] {len(pend)} refrescadas en la SEC, {len(precios)} con P/E de hoy")
    return tabla


def de(a, ticker: str) -> dict | None:
    """Fundamentos guardados de un CEDEAR (acepta el símbolo con D o C al final)."""
    tabla = a.get(CLAVE) or {}
    t = ticker.upper()
    f = tabla.get(t) or (tabla.get(t[:-1]) if t[-1:] in ("D", "C") else None)
    return f if f and f.get("eps_12m") is not None else None


def frase(f: dict | None) -> str:
    if not f:
        return ""
    c = lambda x: str(x).replace(".", ",")
    p = []
    if f.get("pe"):
        p.append(f"P/E {c(f['pe'])} (precio sobre ganancias de 12 meses)")
    elif (f.get("eps_12m") or 0) <= 0:
        p.append("da pérdida en los últimos 12 meses")
    if f.get("crec") is not None:
        p.append(f"ganancias {'+' if f['crec'] >= 0 else ''}{c(round(f['crec'] * 100))}% en un año")
    if f.get("peg"):
        p.append(f"PEG {c(f['peg'])}" + (" (barata para lo que crece)" if f["peg"] < 1 else " (cara para lo que crece)" if f["peg"] >= 2 else ""))
    if f.get("fcf_rinde") is not None:
        p.append(f"flujo de caja libre {'positivo' if f['fcf_rinde'] > 0 else 'negativo'} ({c(f['fcf_rinde'])}% del precio)")
    if f.get("ciclica"):
        p.append("ganancias muy variables (cíclica: el P/E bajo puede ser el pico)")
    if not p:
        return ""
    return "Fundamentos (dato, sin voto): " + "; ".join(p) + ". En 10 años esto no separó ganadoras de perdedoras."
