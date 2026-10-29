"""33. Renta fija para cobrar: ONs y bonos en dólares con pagos periódicos, con el cronograma completo.

- Universo: las ONs y soberanos que cotizan en dólares MEP (línea D) en BYMA, con puntas de compra y venta.
- Cronograma: los flujos oficiales de MAE (A3 Mercados), cada 100 nominales originales (renta + amortización).
  Los soberanos, del archivo de flujos de la mesa.
- Para cada uno se calcula, con el precio de venta de hoy (lo que pagarías):
  * TIR: lo que rinde por año si lo tenés hasta el final y cobrás todo.
  * Cuántas veces paga por año, cuándo es el próximo pago y cuándo vence.
  * Cuánto cobrás en cada fecha con US$ 1.000 invertidos.
- Se proponen solo los que: vencen entre 6 meses y 6 años, pagan al menos cada 6 meses, tienen una TIR razonable
  (entre 3% y 16%: más de eso el mercado está avisando que duda de que pague), diferencia entre compra y venta de 2%
  o menos, y sin una baja de calificación reciente. Uno por emisor, para no concentrar.
- No pasa por el Comité: es otro tipo de inversión (para cobrar, no para vender más caro).
"""
from __future__ import annotations

from datetime import date, timedelta

MIN_TIR, MAX_TIR = 3.0, 16.0


def _habil(d: date) -> date:
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def liquidacion(hoy: date) -> date:
    """Las compras liquidan en 24 hs (T+1)."""
    return _habil(hoy + timedelta(days=1))


def futuros(flujos: list[dict], liq: date) -> list[dict]:
    out = []
    for f in flujos or []:
        try:
            d = _habil(date.fromisoformat(str(f["fecha"])[:10]))
        except (ValueError, KeyError):
            continue
        i, a = float(f.get("interes") or 0), float(f.get("amortizacion") or 0)
        if d > liq:  # con renta 0 también: en las de tasa variable el cupón todavía no se conoce
            out.append({"fecha": d.isoformat(), "renta": round(i, 4), "amortizacion": round(a, 4), "total": round(i + a, 4), "a_definir": not (i or a)})
    return sorted(out, key=lambda x: x["fecha"])


def tir(fl: list[dict], precio: float, liq: date) -> float | None:
    """TIR efectiva anual (%) que iguala los pagos futuros con el precio (cada 100 nominales originales)."""
    if not fl or not precio or precio <= 0:
        return None
    ts = [((date.fromisoformat(f["fecha"]) - liq).days / 365.0, f["total"]) for f in fl]

    def vpn(r: float) -> float:
        return sum(c / (1 + r) ** t for t, c in ts) - precio
    lo, hi = -0.5, 3.0
    if vpn(lo) * vpn(hi) > 0:
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        if vpn(lo) * vpn(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return round((lo + hi) / 2 * 100, 2)


def duration(fl: list[dict], r: float, liq: date) -> float | None:
    """Años promedio que tardás en recuperar la plata (Macaulay)."""
    ts = [((date.fromisoformat(f["fecha"]) - liq).days / 365.0, f["total"]) for f in fl]
    pv = [(t, c / (1 + r / 100) ** t) for t, c in ts]
    tot = sum(v for _, v in pv)
    return round(sum(t * v for t, v in pv) / tot, 2) if tot else None


def frecuencia(flujos: list[dict]) -> str:
    """Cada cuánto paga, mirando la distancia entre pagos (incluye los ya pagados)."""
    fs = sorted({str(f["fecha"])[:10] for f in flujos if f.get("fecha")})
    if len(fs) < 2:
        return "pago único al vencimiento"
    gaps = sorted((date.fromisoformat(b) - date.fromisoformat(a)).days for a, b in zip(fs, fs[1:]))
    g = gaps[len(gaps) // 2]
    return "mensual" if g <= 40 else "trimestral" if g <= 100 else "semestral" if g <= 200 else "anual" if g <= 400 else "irregular"


def tipo_tasa(desc: str) -> str:
    d = (desc or "").upper()
    if any(k in d for k in ("TAMAR", "BADLAR", "VARIABLE", "TASA VAR")):
        return "variable"
    if "DUAL" in d:
        return "dual"
    if any(k in d for k in ("CER", "UVA", "AJUST")):
        return "cer"
    if "LINK" in d:
        return "dólar linked"
    return "fija"


def analizar(tk: str, precio: float, flujo: dict, liq: date) -> dict | None:
    fl = futuros(flujo.get("flujos") or [], liq)
    if not fl:
        return None
    r = tir(fl, precio, liq)
    tt = tipo_tasa(flujo.get("descripcion") or "")
    # tasa variable: los cupones futuros todavía no se conocen (dependen de la TAMAR/Badlar): la TIR con los conocidos
    # no sirve; se informa lo que rinde el próximo cupón llevado a un año
    var_txt = None
    if tt in ("variable", "dual") and (r is None or sum(1 for f in fl if f["renta"] == 0) >= len(fl) - 1):
        fr = frecuencia(flujo.get("flujos") or [])
        n = {"mensual": 12, "trimestral": 4, "semestral": 2, "anual": 1}.get(fr, 0)
        if n and fl[0]["renta"]:
            r = round(fl[0]["renta"] * n / precio * 100, 2)
            var_txt = f"tasa variable: el próximo cupón, llevado a un año, rinde ~{r:.1f}%; los siguientes cambian con la tasa"
    if r is None:
        return None
    ultimo = fl[-1]["fecha"]
    anio = (liq + timedelta(days=365)).isoformat()
    pagos_anio = sum(1 for f in fl if f["fecha"] <= anio and (f["renta"] > 0 or f.get("a_definir")))
    renta_anio = round(sum(f["renta"] for f in fl if f["fecha"] <= anio), 2)
    return {"ticker": tk, "descripcion": flujo.get("descripcion") or flujo.get("emisor") or "", "precio": precio, "tir": r,
            "duration": duration(fl, r, liq), "vence": ultimo, "anios": round((date.fromisoformat(ultimo) - liq).days / 365, 1),
            "pagos_por_anio": pagos_anio, "renta_anual_c100": renta_anio,
            "renta_actual_pct": round(renta_anio / precio * 100, 2) if precio else None,
            "proximo": fl[0], "cronograma": fl, "fuente": flujo.get("fuente") or "flujos de la mesa",
            "frecuencia": frecuencia(flujo.get("flujos") or []), "tasa": tt, "tasa_txt": var_txt}


def ejemplo(x: dict, monto: float = 1000.0, liq: date | None = None) -> dict:
    """Con US$ monto: cuántos nominales comprás y cuánto cobrás en cada fecha."""
    vn = int(monto / (x["precio"] / 100))
    pagos = [{"fecha": f["fecha"], "renta": round(vn * f["renta"] / 100, 2), "amortizacion": round(vn * f["amortizacion"] / 100, 2),
              "total": round(vn * f["total"] / 100, 2), "a_definir": f.get("a_definir")} for f in x["cronograma"]]
    return {"monto": monto, "nominales": vn, "pagos": pagos, "cobras_total": round(sum(p["total"] for p in pagos), 2),
            "cobras_12m": round(sum(p["total"] for p in pagos if p["fecha"] <= ((liq or date.today()) + timedelta(days=365)).isoformat()), 2),
            "costo": round(vn * x["precio"] / 100, 2)}


def _riesgo(t: float) -> str:
    if t < 7:
        return "bajo: el mercado confía en que paga (por eso rinde menos)"
    if t < 10:
        return "medio"
    return "alto: rinde más porque el mercado duda más"


def _emisor(desc: str, tk: str) -> str:
    d = (desc or "").upper().replace("O.N.", "").replace("ON ", "").strip()
    return (d.split()[0] if d else tk[:3])


def proponer(panel: dict, flujos: dict, soberanos: dict, hoy: date, malas: set[str] | None = None,
             tengo: set[str] | None = None, n_ons: int = 6, n_sob: int = 2) -> dict:
    """panel: {tk: [ultimo, var, compra, venta, grupo]}. flujos: {tk: {...MAE}}. soberanos: flujos_bonos()."""
    liq = liquidacion(hoy)
    malas, tengo = malas or set(), tengo or set()
    cand = []
    for tk, p in panel.items():
        if not p or len(p) < 5 or p[4] not in ("ons", "soberanos") or not tk.endswith("D"):
            continue
        ult, compra, venta = p[0], p[2], p[3]
        if not compra or not venta or not (30 <= venta <= 130):
            continue
        spread = (venta - compra) / venta * 100
        if spread > 2:
            continue
        base = tk[:-1]
        f = soberanos.get(tk) or soberanos.get(base) if p[4] == "soberanos" else (flujos.get(tk) or flujos.get(base + "O"))
        if not f or not f.get("flujos"):
            continue
        mon = str(f.get("moneda") or "USD").upper()
        if p[4] == "ons" and mon not in ("USD", "U$S", "DOLARES", "DÓLARES", "US$", "DOLAR MEP", "USD MEP"):
            continue  # la línea D de una ON en pesos o dólar linked no paga dólares
        x = analizar(tk, float(venta), f, liq)
        if not x:
            continue
        x.update(grupo=p[4], compra=compra, spread_pct=round(spread, 2), riesgo=_riesgo(x["tir"]),
                 emisor=("Tesoro Nacional" if p[4] == "soberanos" else _emisor(x["descripcion"], tk)), ya_tenes=base in tengo or tk in tengo)
        x["motivos_fuera"] = [m for m, c in (
            (f"vence en {x['anios']} años", not (0.5 <= x["anios"] <= 6)),
            (f"pago {x['frecuencia']}", x["frecuencia"] in ("anual", "pago único al vencimiento", "irregular")),
            (f"TIR {x['tir']}% fuera de rango", not (MIN_TIR <= x["tir"] <= MAX_TIR)),
            ("calificación en baja", tk in malas or base in malas)) if c]
        cand.append(x)
    # ---- en pesos: ONs y bonos que pagan pesos (línea O / sin sufijo), con su cronograma de MAE ----
    for tk, p in panel.items():
        if not p or len(p) < 5 or p[4] not in ("ons", "letras", "soberanos", "bonos") or tk.endswith(("D", "C")):
            continue
        compra, venta = p[2], p[3]
        f = flujos.get(tk)
        if not compra or not venta or not f or not f.get("flujos") or str(f.get("moneda") or "").upper() not in ("ARS", "$", "PESOS"):
            continue
        if not (20 <= venta <= 400):  # cotiza cada 100 nominales
            continue
        spread = (venta - compra) / venta * 100
        if spread > 3:
            continue
        x = analizar(tk, float(venta), f, liq)
        if not x or x["tasa"] == "cer":  # CER: el cronograma de MAE no trae el ajuste por inflación; la TIR saldría mal
            continue
        x.update(grupo="pesos", compra=compra, spread_pct=round(spread, 2), riesgo="en pesos: compará con la inflación esperada",
                 emisor=_emisor(x["descripcion"], tk), ya_tenes=tk in tengo, moneda="ARS")
        x["motivos_fuera"] = [m for m, c in ((f"vence en {x['anios']} años", not (0.15 <= x["anios"] <= 5)),
                                             (f"TIR {x['tir']}% fuera de rango", not (5 <= x["tir"] <= 120)),
                                             ("calificación en baja", tk in malas)) if c]
        cand.append(x)
    ok = [x for x in cand if not x["motivos_fuera"]]
    def mejores(g: str, n: int) -> list[dict]:
        vistos, out = set(), []
        for x in sorted((y for y in ok if y["grupo"] == g), key=lambda y: -y["tir"]):
            if x["emisor"] in vistos:
                continue
            vistos.add(x["emisor"])
            out.append({**x, "ejemplo": ejemplo(x, 1_000_000.0 if g == "pesos" else 1000.0, liq=liq)})
            if len(out) >= n:
                break
        return out
    return {"fecha": hoy.isoformat(), "liquida": liq.isoformat(), "analizados": len(cand), "aptos": len(ok),
            "ons": mejores("ons", n_ons), "soberanos": mejores("soberanos", n_sob), "pesos": mejores("pesos", 5)}
