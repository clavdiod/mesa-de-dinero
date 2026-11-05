"""Wall Street en vivo (05/11): la lectura de la rueda de Nueva York mientras está abierta, al estilo de un operador.

Pedido de Clau (a partir de un posteo de Damian Brik): cuánto cae o sube el Nasdaq, el miedo (VIX), qué sector manda,
volúmenes anormales con el precio pegado al mínimo o al máximo del día, apalancados que se desploman, cuánto lleva
cada papel en 5 días, un mes y desde máximos, y qué pasó en 10 años después de días parecidos.
Solo datos (Yahoo, gratis). No inventa causas: los motivos los ponen los titulares, si hay.
"""
from __future__ import annotations

import statistics as st
from datetime import datetime
from zoneinfo import ZoneInfo

from ..datos.gratis import _S, _UA_JSON

NY = ZoneInfo("America/New_York")
INDICES = {"QQQ": "Nasdaq 100", "SPY": "S&P 500", "IWM": "Russell 2000 (pymes)", "^VIX": "VIX (miedo)"}
SEMIS = {"SOXX": "semiconductores", "SOXL": "semis apalancado 3x", "NVDA": "Nvidia", "AMD": "AMD", "MU": "Micron", "AVGO": "Broadcom", "TSM": "TSMC"}
HYPER = {"MSFT": "Microsoft", "GOOGL": "Google", "AMZN": "Amazon", "META": "Meta", "ORCL": "Oracle"}
OTROS = {"AAPL": "Apple", "TSLA": "Tesla", "TLT": "bonos del Tesoro largos", "GLD": "oro", "BTC-USD": "bitcoin"}
APALANCADOS = {"SOXL", "TQQQ"}


def _p(x: float, d: int = 1) -> str:
    return f"{'+' if x > 0 else ''}{x:.{d}f}%".replace(".", ",")


def _serie(sim: str) -> dict | None:
    """Velas diarias de un año (la de hoy incluida mientras la rueda está abierta) + datos del día."""
    try:
        r = _S.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sim}?range=1y&interval=1d", headers=_UA_JSON, timeout=20)
        res = r.json()["chart"]["result"][0]
        m, q = res["meta"], res["indicators"]["quote"][0]
        fechas = [datetime.fromtimestamp(t, NY).date().isoformat() for t in res["timestamp"]]
        c = [(f, x, v or 0) for f, x, v in zip(fechas, q["close"], q.get("volume") or [0] * len(fechas)) if x]
        if len(c) < 30:
            return None
        hoy = datetime.now(NY).date().isoformat()
        precio = m.get("regularMarketPrice") or c[-1][1]
        if c[-1][0] == hoy:
            ant = c[-2][1]; hist = c[:-1]
        else:
            ant = c[-1][1]; hist = c
        cs = [x for _, x, _ in hist] + [precio]
        return {"precio": precio, "var": (precio / ant - 1) * 100, "hoy": c[-1][0] == hoy,
                "d5": (precio / cs[-6] - 1) * 100, "m1": (precio / cs[-22] - 1) * 100,
                "desde_max": (precio / max(cs) - 1) * 100,
                "alto": m.get("regularMarketDayHigh"), "bajo": m.get("regularMarketDayLow"),
                "vol": m.get("regularMarketVolume") or 0, "vol_prom": st.mean([v for _, _, v in hist[-20:]]) or 0}
    except Exception as ex:
        print(f"[ws vivo] {sim}: {ex}")
        return None


def _avance_rueda(ahora: datetime) -> float:
    """Qué parte de la rueda de Nueva York (9:30 a 16:00) ya pasó: para comparar el volumen 'a esta hora'."""
    n = ahora.astimezone(NY)
    mins = (n.hour * 60 + n.minute) - (9 * 60 + 30)
    return min(1.0, max(0.08, mins / 390))


def _parecidos(h: dict, var_qqq: float, var_vix: float | None) -> str | None:
    """Qué hizo el Nasdaq en los 20 días hábiles siguientes a días como hoy (10 años)."""
    q = [c for _, c in h.get("qqq") or []]
    if len(q) < 500 or abs(var_qqq) < 2:
        return None
    lado = -1 if var_qqq < 0 else 1
    casos = [q[i + 20] / q[i] - 1 for i in range(1, len(q) - 20)
             if (q[i] / q[i - 1] - 1) * 100 * lado >= abs(var_qqq) - 1 and (q[i] / q[i - 1] - 1) * 100 * lado <= abs(var_qqq) + 1.5]
    if len(casos) < 8:
        return None
    s = sorted(casos)
    txt = (f"En 10 años hubo {len(casos)} días en que el Nasdaq {'cayó' if lado < 0 else 'subió'} parecido a hoy. "
           f"Un mes después estaba más arriba {round(sum(1 for x in casos if x > 0) / len(casos) * 100)} de cada 100 veces "
           f"(caso típico {_p(s[len(s) // 2] * 100)}; el peor 10% {_p(s[len(s) // 10] * 100)}).")
    return txt


def lectura(ahora: datetime, propios: dict[str, str] | None = None, hist: dict | None = None, titulares: list[str] | None = None) -> dict | None:
    """propios: {símbolo en NY: cómo lo tenés} (CEDEARs y ADRs de tu cartera)."""
    from concurrent.futures import ThreadPoolExecutor
    todos = {**INDICES, **SEMIS, **HYPER, **OTROS, **(propios or {})}
    with ThreadPoolExecutor(8) as ex:
        d = {s: r for s, r in zip(todos, ex.map(_serie, todos)) if r}
    q, v, spy = d.get("QQQ"), d.get("^VIX"), d.get("SPY")
    if not q or not q["hoy"]:
        return None  # Nueva York todavía no abrió (o es feriado allá)
    av = _avance_rueda(ahora)
    for s, x in d.items():
        x["vol_rel"] = x["vol"] / (x["vol_prom"] * av) if x["vol_prom"] else None
        rango = (x["alto"] or 0) - (x["bajo"] or 0)
        x["pos_dia"] = (x["precio"] - x["bajo"]) / rango if rango > 0 else None
    semis = [d[s]["var"] for s in ("NVDA", "AMD", "MU", "AVGO", "TSM") if s in d]
    hyper = [d[s]["var"] for s in HYPER if s in d]
    m_semis = st.mean(semis) if semis else 0
    m_hyper = st.mean(hyper) if hyper else 0
    vq = q["var"]
    if vq <= -3:
        tit, col = "Venta muy fuerte", "rojo"
    elif vq <= -1.5:
        tit, col = "Día de venta", "rojo"
    elif vq >= 3:
        tit, col = "Suba muy fuerte", "verde"
    elif vq >= 1.5:
        tit, col = "Día de compra", "verde"
    else:
        tit, col = "Día tranquilo", "amar"
    foco = ""
    if spy and m_semis - spy["var"] <= -2:
        foco = ", en especial semiconductores e IA"
    elif spy and m_semis - spy["var"] >= 2:
        foco = ", liderada por semiconductores e IA"
    lin = [f"{tit} en Wall Street{foco}: Nasdaq 100 (QQQ) {_p(vq)}" + (f", S&P 500 {_p(spy['var'])}" if spy else "")
           + (f", pymes (IWM) {_p(d['IWM']['var'])}" if "IWM" in d else "") + "."]
    if v:
        nivel = "pánico" if v["precio"] >= 30 else "miedo alto" if v["precio"] >= 25 else "miedo moderado" if v["precio"] >= 20 else "calma"
        lin.append(f"Miedo: el VIX está en {v['precio']:.1f} ({_p(v['var'], 0)} hoy), {nivel}.".replace(".", ",", 1))
    if semis:
        lin.append("Semiconductores: " + ", ".join(f"{SEMIS[s]} {_p(d[s]['var'])}" for s in ("NVDA", "AMD", "MU", "AVGO", "TSM") if s in d) + ".")
    if hyper:
        lin.append(f"Hiperescaladoras (las que invierten en IA): promedio {_p(m_hyper)} — " + ", ".join(f"{HYPER[s]} {_p(d[s]['var'])}" for s in HYPER if s in d) + ".")
    # apalancados desplomándose o volando: señal de exceso de apalancamiento y ventas forzadas
    for s in APALANCADOS:
        x = d.get(s)
        if x and abs(x["var"]) >= 8:
            lin.append(f"{s} ({SEMIS.get(s, 'apalancado 3x')}) {_p(x['var'])} hoy, {_p(x['d5'], 0)} en 5 días, {_p(x['m1'], 0)} en un mes y {_p(x['desde_max'], 0)} desde su máximo."
                       + (" Movimientos así suelen ser ventas forzadas (llamados de margen)." if x["var"] < 0 else ""))
    # volumen anormal con el precio en un extremo del día: quién manda
    vend = [s for s, x in d.items() if s != "^VIX" and (x["vol_rel"] or 0) >= 1.8 and x["pos_dia"] is not None and x["pos_dia"] <= 0.2 and x["var"] < 0]
    comp = [s for s, x in d.items() if s != "^VIX" and (x["vol_rel"] or 0) >= 1.8 and x["pos_dia"] is not None and x["pos_dia"] >= 0.8 and x["var"] > 0]
    if vend:
        lin.append("Vendedores en control: " + ", ".join(f"{s} ({d[s]['vol_rel']:.1f}x)".replace(".", ",") for s in vend[:5])
                   + " operan mucho más volumen que lo normal a esta hora y están pegados al mínimo del día.")
    if comp:
        lin.append("Compradores en control: " + ", ".join(f"{s} ({d[s]['vol_rel']:.1f}x)".replace(".", ",") for s in comp[:5])
                   + " con volumen fuerte y cerca del máximo del día.")
    ref = [f"{OTROS[s]} {_p(d[s]['var'])}" for s in ("TLT", "GLD", "BTC-USD") if s in d]
    if ref:
        refugio = vq < -1.5 and any(d[s]["var"] > 0.3 for s in ("TLT", "GLD") if s in d)
        lin.append(("La plata busca refugio: " if refugio else "Otros: ") + ", ".join(ref) + ".")
    if propios:
        lin.append("Lo tuyo en Nueva York: " + ", ".join(f"{propios[s]} {_p(d[s]['var'])}" for s in propios if s in d) + ".")
    ctx = _parecidos(hist or {}, vq, v["var"] if v else None)
    if ctx:
        lin.append(ctx)
    tabla = [{"sim": s, "nombre": todos[s], "var": round(x["var"], 2), "d5": round(x["d5"], 1), "m1": round(x["m1"], 1),
              "desde_max": round(x["desde_max"], 1), "vol_rel": round(x["vol_rel"], 1) if x["vol_rel"] else None}
             for s, x in d.items()]
    hora_ny = ahora.astimezone(NY).strftime("%H:%M")
    return {"titulo": f"{tit} · QQQ {_p(vq)}" + (f" · VIX {v['precio']:.1f}".replace(".", ",") if v else ""), "color": col,
            "lineas": lin, "titulares": (titulares or [])[:3], "tabla": tabla, "hora_ny": hora_ny,
            "nota": "Datos de Yahoo (pueden tener unos minutos de atraso). El volumen se compara con lo normal a esta altura de la rueda. Solo lectura: no vota."}
