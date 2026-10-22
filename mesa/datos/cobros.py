"""Tus cobros: cuánto cobrás, de qué y cuándo (renta y amortización de bonos, ONs y letras de tu cartera).

Flujos (gratis, sin cupo de IOL), en este orden:
1. Las ONs que cargaste a mano en la web (usuario/ons).
2. config/bonos_flujos.yaml (soberanos en dólares).
3. MAE (A3 Mercados): emisiones/flujofondos/{ticker}. Sirve para casi todo: soberanos, ONs, duales, bonos CER...
   Se guarda en cobros/flujos y se vuelve a bajar cada 7 días.
Los flujos vienen cada 100 nominales originales: cobro = nominales × (renta + amortización) / 100.
Las LECAP no traen flujo en MAE (pagan todo al vencimiento): se avisa la fecha sin monto.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

_MAE = "https://api.marketdata.mae.com.ar/api/"
_H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}


def candidatos(tk: str) -> list[str]:
    """Cómo puede llamarse el papel en MAE: AL30D -> AL30; YM34D -> YM34O (la O es la línea en pesos de la ON)."""
    tk = tk.upper()
    out = [tk]
    if tk[-1:] in ("D", "C"):
        out += [tk[:-1] + "O", tk[:-1]]
    return list(dict.fromkeys(out))


def flujos_mae(tk: str) -> dict | None:
    from .gratis import _S
    for c in candidatos(tk):
        try:
            r = _S.get(_MAE + f"emisiones/flujofondos/{c}", headers=_H, timeout=20).json()
        except Exception as ex:
            print(f"[cobros] {c}: {ex}")
            continue
        det = r.get("detalle") or []
        if det:
            return {"especie": r.get("especie"), "moneda": r.get("moneda"), "descripcion": r.get("descripcion"), "fuente": "MAE",
                    "flujos": [{"fecha": d["fechaPago"][:10], "interes": round(d.get("renta") or 0, 6),
                                "amortizacion": round(d.get("amortizacion") or 0, 6), "vr": d.get("vr")} for d in det]}
    return None


def asegurar_flujos(almacen, tickers: list[str], hoy: date, maximo: int = 10, ya_tienen: set[str] | None = None) -> dict:
    """Baja de MAE los flujos que falten (o tengan más de 7 días). Devuelve {ticker: flujo}."""
    guardado = almacen.get("cobros/flujos") or {}
    cambio, bajados = False, 0
    for tk in tickers:
        tk = tk.upper()
        if ya_tienen and tk in ya_tienen:
            continue
        g = guardado.get(tk)
        viejo = not g or (date.fromisoformat(g.get("bajado", "2000-01-01")) + timedelta(days=7)) < hoy
        if viejo and bajados < maximo:
            bajados += 1
            f = flujos_mae(tk)
            guardado[tk] = {**(f or {"flujos": [], "sin_datos": True}), "bajado": hoy.isoformat()}
            cambio = True
    if cambio:
        almacen.put("cobros/flujos", guardado)
    return {k: v for k, v in guardado.items() if k in {t.upper() for t in tickers} and v.get("flujos")}


def _habil(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def moneda(f: dict, tk: str) -> str:
    m = str(f.get("moneda") or "").upper()
    return "USD" if "USD" in m or "DOLAR" in m else "ARS" if m else ("USD" if tk[-1:] in ("D", "C") else "ARS")


def proximos(cartera: list[dict], fuentes: dict[str, dict], hoy: date, dias: int = 45) -> list[dict]:
    """Cobros de tu cartera en los próximos `dias`, con el monto calculado."""
    hasta = hoy + timedelta(days=dias)
    out = []
    for pos in cartera:
        tk = (pos.get("ticker") or "").upper()
        cant = float(pos.get("cantidad") or 0)
        f = fuentes.get(tk)
        if not f or not cant:
            continue
        for fl in f.get("flujos") or []:
            try:
                pago = _habil(date.fromisoformat(str(fl["fecha"])[:10]))
            except ValueError:
                continue
            if not (hoy <= pago <= hasta):
                continue
            i, a = cant * float(fl.get("interes") or 0) / 100, cant * float(fl.get("amortizacion") or 0) / 100
            out.append({"fecha": pago.isoformat(), "ticker": tk, "nominales": cant, "renta": round(i, 2), "amortizacion": round(a, 2),
                        "total": round(i + a, 2), "moneda": moneda(f, tk), "descripcion": f.get("descripcion") or "",
                        "fuente": f.get("fuente") or "cargado"})
    return sorted(out, key=lambda x: (x["fecha"], x["ticker"]))


def vencimientos_lecap(cartera: list[dict], titulos, hoy: date, dias: int = 45) -> list[dict]:
    """LECAP/BONCAP (S13N6, T15E7...): vencen todo junto; se avisa la fecha (sin monto si no lo tenemos)."""
    meses = {"E": 1, "F": 2, "M": 3, "A": 4, "Y": 5, "J": 6, "L": 7, "G": 8, "S": 9, "O": 10, "N": 11, "D": 12}
    out = []
    for pos in cartera:
        tk = (pos.get("ticker") or "").upper()
        m = re.fullmatch(r"[ST](\d{2})([EFMAYJLGSOND])(\d)", tk)
        if not m:
            continue
        try:
            v = _habil(date(2020 + int(m.group(3)), meses[m.group(2)], int(m.group(1))))
        except ValueError:
            continue
        if hoy <= v <= hoy + timedelta(days=dias):
            out.append({"fecha": v.isoformat(), "ticker": tk, "nominales": float(pos.get("cantidad") or 0), "renta": None, "amortizacion": None,
                        "total": None, "moneda": "ARS", "descripcion": "Vence la letra: cobrás el valor final (capital + interés capitalizado).",
                        "fuente": "vencimiento"})
    return out


def _plata(x: float, mon: str) -> str:
    s = f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("US$ " if mon == "USD" else "$") + s


def texto(c: dict) -> str:
    if c["total"] is None:
        return f"{c['ticker']}: {c['descripcion']}"
    partes = ([f"renta {_plata(c['renta'], c['moneda'])}"] if c["renta"] else []) + ([f"amortización {_plata(c['amortizacion'], c['moneda'])}"] if c["amortizacion"] else [])
    return f"{_plata(c['total'], c['moneda'])} de {c['ticker']} ({' + '.join(partes)})"


def totales(cs: list[dict]) -> str:
    t: dict[str, float] = {}
    for c in cs:
        if c["total"] is not None:
            t[c["moneda"]] = t.get(c["moneda"], 0) + c["total"]
    return " y ".join(_plata(v, m) for m, v in sorted(t.items(), key=lambda x: x[0] != "USD"))


def avisos(cs: list[dict], hoy: date) -> list[dict]:
    """Avisos para el celular: hoy, mañana (día hábil siguiente) y, los lunes, la semana."""
    h = hoy.isoformat()
    man = _habil(hoy + timedelta(days=1)).isoformat()
    fin_sem = (hoy + timedelta(days=6 - hoy.weekday())).isoformat()
    out = []
    de_hoy = [c for c in cs if c["fecha"] == h]
    de_man = [c for c in cs if c["fecha"] == man]
    if de_hoy:
        out.append({"cuando": "hoy", "texto": "💵 Hoy cobrás " + "; ".join(texto(c) for c in de_hoy) + "."
                    + (f" Total: {totales(de_hoy)}." if len(de_hoy) > 1 else "") + " Suele acreditarse en la cuenta del bróker en el día o al siguiente."})
    if de_man:
        out.append({"cuando": "mañana", "texto": f"💵 {'Mañana' if man == (hoy + timedelta(days=1)).isoformat() else 'El lunes'} cobrás "
                    + "; ".join(texto(c) for c in de_man) + "."})
    if hoy.weekday() == 0:
        sem = [c for c in cs if h <= c["fecha"] <= fin_sem]
        if len(sem) > len(de_hoy) + len(de_man):
            out.append({"cuando": "semana", "texto": f"💵 Esta semana cobrás {totales(sem) or ''}: "
                        + "; ".join(f"{c['fecha'][8:10]}/{c['fecha'][5:7]} {texto(c)}" for c in sem) + "."})
    return out
