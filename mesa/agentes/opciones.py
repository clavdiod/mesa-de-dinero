"""37. Mesa de Opciones: un grupo de expertos que analiza SOLO opciones (BYMA). Le consulta a la mesa principal la
dirección del papel para la decisión final, pero las opciones las evalúan ellos. Por ahora todo es EN PAPEL.

Expertos:
- Volatilidad: compara la volatilidad implícita (lo que cobra el mercado por la opción) con la que el papel tuvo de
  verdad en 20 y 60 ruedas. Prima cara → conviene vender opciones; barata → conviene comprar protección.
- Lanzador cubierto: si tenés 100 acciones o más de un papel, busca un call para vender arriba del precio
  (probabilidad de ejercicio 20-35%, 2 a 7 semanas) y calcula la renta que cobrás y hasta dónde te limita la suba.
- Protector: busca el put que funciona como seguro de lo que tenés (cuánto cuesta y desde qué precio te cubre).
- Liquidez: descarta opciones sin puntas, con diferencia compra/venta mayor a 15% o sin operaciones.
- Riesgo: lote de 100 acciones por contrato, comisión (~1% ida y vuelta + derechos), pérdida máxima.
- Comité de opciones: junta todo, consulta a la mesa principal (a favor / en contra del papel) y decide.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime

LOTE = 100
COMISION = 0.01  # ida y vuelta, aproximada (Cocos cobra hasta 1% en opciones)
MESES = {"EN": 1, "FE": 2, "MR": 3, "AB": 4, "MY": 5, "JU": 6, "JL": 7, "AG": 8, "SE": 9, "OC": 10, "NO": 11, "DI": 12}


# ---------- Black-Scholes ----------
def _N(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def bs(tipo: str, s: float, k: float, t: float, r: float, v: float) -> float:
    if t <= 0 or v <= 0:
        return max(0.0, s - k) if tipo == "C" else max(0.0, k - s)
    d1 = (math.log(s / k) + (r + v * v / 2) * t) / (v * math.sqrt(t)); d2 = d1 - v * math.sqrt(t)
    return s * _N(d1) - k * math.exp(-r * t) * _N(d2) if tipo == "C" else k * math.exp(-r * t) * _N(-d2) - s * _N(-d1)


def delta(tipo: str, s: float, k: float, t: float, r: float, v: float) -> float | None:
    if t <= 0 or v <= 0:
        return None
    d1 = (math.log(s / k) + (r + v * v / 2) * t) / (v * math.sqrt(t))
    return _N(d1) if tipo == "C" else _N(d1) - 1


def iv(tipo: str, precio: float, s: float, k: float, t: float, r: float) -> float | None:
    """Volatilidad implícita por bisección."""
    if not precio or t <= 0 or precio <= max(0.0, (s - k) if tipo == "C" else (k - s)) * 0.999:
        return None
    lo, hi = 0.01, 4.0
    for _ in range(80):
        m = (lo + hi) / 2
        if bs(tipo, s, k, t, r, m) > precio:
            hi = m
        else:
            lo = m
    v = (lo + hi) / 2
    return v if 0.02 < v < 3.9 else None


def vol_real(cierres: list[float], n: int) -> float | None:
    c = [x for x in cierres[-(n + 1):] if x]
    if len(c) < n * 0.8:
        return None
    r = [math.log(b / a) for a, b in zip(c, c[1:]) if a > 0 and b > 0]
    m = sum(r) / len(r)
    return math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1)) * math.sqrt(252)


# ---------- datos ----------
def metadatos(crudo: list[dict]) -> dict[str, dict]:
    """De /Titulos/{tk}/Opciones: símbolo -> {subyacente, tipo, strike, vence}."""
    out = {}
    for o in crudo or []:
        m = re.search(r"([\d.,]+)\s+Vencimiento", o.get("descripcion") or "")
        if not m or not o.get("simbolo"):
            continue
        out[o["simbolo"]] = {"subyacente": o.get("simboloSubyacente"), "tipo": "C" if (o.get("tipoOpcion") or "").lower().startswith("c") else "P",
                             "strike": float(m.group(1).replace(",", "")), "vence": str(o.get("fechaVencimiento"))[:10]}
    return out


def cadena(meta: dict[str, dict], panel: list[dict], subyacente: str, spot: float, hoy: date, r: float) -> list[dict]:
    """Une metadatos + precios del panel y calcula días, precio medio, volatilidad implícita y delta."""
    precios = {x.get("simbolo"): x for x in panel or []}
    out = []
    for sym, m in meta.items():
        if m["subyacente"] != subyacente:
            continue
        p = precios.get(sym) or {}
        pu = p.get("puntas") or {}
        bid, ask = pu.get("precioCompra") or None, pu.get("precioVenta") or None
        dias = (date.fromisoformat(m["vence"]) - hoy).days
        if dias <= 0:
            continue
        t = dias / 365
        mid = (bid + ask) / 2 if bid and ask else (p.get("ultimoPrecio") or None)
        v = iv(m["tipo"], mid, spot, m["strike"], t, r) if mid else None
        out.append({"simbolo": sym, **m, "dias": dias, "bid": bid, "ask": ask, "ultimo": p.get("ultimoPrecio"), "mid": mid,
                    "volumen": p.get("volumen") or 0, "operaciones": p.get("cantidadOperaciones") or 0,
                    "spread_pct": round((ask - bid) / ((ask + bid) / 2) * 100, 1) if bid and ask else None,
                    "iv": round(v, 3) if v else None, "delta": round(delta(m["tipo"], spot, m["strike"], t, r, v), 2) if v else None})
    return sorted(out, key=lambda x: (x["vence"], x["tipo"], x["strike"]))


# ---------- expertos ----------
def experto_liquidez(o: dict) -> tuple[bool, str]:
    if not o.get("bid") or not o.get("ask"):
        return False, "sin puntas de compra y venta"
    if (o.get("spread_pct") or 99) > 15:
        return False, f"diferencia compra/venta de {o['spread_pct']}%"
    if (o.get("operaciones") or 0) < 1 and (o.get("volumen") or 0) < 1:
        return False, "no operó hoy"
    return True, "líquida"


def experto_volatilidad(cad: list[dict], spot: float, cierres: list[float]) -> dict:
    hv20, hv60 = vol_real(cierres, 20), vol_real(cierres, 60)
    atm = [o for o in cad if o.get("iv") and 15 <= o["dias"] <= 60 and abs(o["strike"] / spot - 1) <= 0.06]
    iv_atm = sorted(o["iv"] for o in atm)[len(atm) // 2] if atm else None
    ref = max(x for x in (hv20, hv60) if x) if (hv20 or hv60) else None
    ratio = iv_atm / ref if iv_atm and ref else None
    lectura = ("primas CARAS: el mercado cobra más de lo que el papel se mueve; conviene vender opciones (lanzamiento cubierto)" if ratio and ratio >= 1.2
               else "primas BARATAS: conviene comprar protección (puts)" if ratio and ratio <= 0.85
               else "primas en precio normal" if ratio else "sin datos suficientes")
    return {"iv_atm": iv_atm, "hv20": round(hv20, 3) if hv20 else None, "hv60": round(hv60, 3) if hv60 else None,
            "ratio": round(ratio, 2) if ratio else None, "lectura": lectura}


def experto_lanzador(cad: list[dict], spot: float, acciones: int) -> dict | None:
    """Call para vender contra acciones que ya tenés (1 contrato = 100 acciones)."""
    lotes = acciones // LOTE
    if lotes < 1:
        return None
    cands = []
    for o in cad:
        ok, _ = experto_liquidez(o)
        if o["tipo"] != "C" or not ok or not (14 <= o["dias"] <= 50) or o["strike"] <= spot * 1.02 or not o.get("delta"):
            continue
        if not (0.15 <= o["delta"] <= 0.40):
            continue
        prima = o["bid"]  # vendés a la punta compradora
        renta = prima / spot
        cands.append({**o, "prima": prima, "renta_pct": round(renta * 100, 2), "renta_anual_pct": round(renta * 365 / o["dias"] * 100, 1),
                      "tope_pct": round((o["strike"] / spot - 1) * 100, 1), "prob_ejercicio": round(o["delta"] * 100),
                      "lotes": lotes, "cobras": round(prima * LOTE * lotes * (1 - COMISION / 2))})
    if not cands:
        return None
    return max(cands, key=lambda x: x["renta_anual_pct"] * (1 - x["delta"]))


def experto_protector(cad: list[dict], spot: float, acciones: int) -> dict | None:
    """Put que funciona como seguro: desde qué precio te cubre y cuánto cuesta."""
    cands = []
    for o in cad:
        ok, _ = experto_liquidez(o)
        if o["tipo"] != "P" or not ok or not (14 <= o["dias"] <= 70) or o["strike"] >= spot or not o.get("delta"):
            continue
        if not (-0.35 <= o["delta"] <= -0.12):
            continue
        costo = o["ask"] / spot
        cands.append({**o, "costo_pct": round(costo * 100, 2), "cubre_desde_pct": round((o["strike"] / spot - 1) * 100, 1),
                      "contratos": max(1, round(acciones / LOTE)) if acciones else 1,
                      "pagas": round(o["ask"] * LOTE * max(1, round(acciones / LOTE)) * (1 + COMISION / 2))})
    if not cands:
        return None
    # el seguro más barato por cada punto de cobertura
    return min(cands, key=lambda x: x["costo_pct"] / max(0.5, 15 + x["cubre_desde_pct"]))


def comite(tk: str, spot: float, cad: list[dict], cierres: list[float], acciones: int, mesa: dict | None) -> dict:
    """Junta a los expertos y consulta a la mesa principal (opinión del papel) para la decisión final."""
    vol = experto_volatilidad(cad, spot, cierres)
    lanz = experto_lanzador(cad, spot, acciones)
    prot = experto_protector(cad, spot, acciones) if acciones else None
    veredicto = (mesa or {}).get("veredicto")
    ideas = []
    if lanz:
        caro = (vol.get("ratio") or 0) >= 1.0
        ok = caro and veredicto != "a favor"  # si la mesa está muy a favor, no conviene limitar la suba
        ideas.append({"estrategia": "lanzamiento cubierto", "aprobada": ok, "opcion": lanz["simbolo"], "detalle": lanz,
                      "texto": (f"Vender {lanz['lotes']} call {lanz['simbolo']} (strike {lanz['strike']:,.0f}, vence {lanz['vence'][8:10]}/{lanz['vence'][5:7]}) "
                                f"a {lanz['prima']:,.2f}: cobrás ~${lanz['cobras']:,} ({lanz['renta_pct']}% en {lanz['dias']} días, {lanz['renta_anual_pct']}% anual). "
                                f"Si el papel pasa {lanz['strike']:,.0f} (+{lanz['tope_pct']}%) te ejercen y vendés ahí; probabilidad ~{lanz['prob_ejercicio']}%.").replace(",", "."),
                      "motivo": "" if ok else ("la mesa está a favor del papel: vender el call te limitaría la suba" if veredicto == "a favor"
                                               else "las primas no están caras: no paga ceder la suba")})
    if prot:
        barato = (vol.get("ratio") or 9) <= 1.1
        ok = barato and veredicto == "en contra"
        ideas.append({"estrategia": "put de protección", "aprobada": ok, "opcion": prot["simbolo"], "detalle": prot,
                      "texto": (f"Comprar {prot['contratos']} put {prot['simbolo']} (strike {prot['strike']:,.0f}, vence {prot['vence'][8:10]}/{prot['vence'][5:7]}) "
                                f"a {prot['ask']:,.2f}: pagás ~${prot['pagas']:,} ({prot['costo_pct']}% del valor) y quedás cubierto si cae más de {abs(prot['cubre_desde_pct'])}%.").replace(",", "."),
                      "motivo": "" if ok else ("la mesa no está en contra del papel: el seguro sería un gasto" if veredicto != "en contra"
                                               else "las primas están caras: el seguro sale demasiado")})
    liquidas = sum(1 for o in cad if experto_liquidez(o)[0])
    return {"ticker": tk, "spot": spot, "volatilidad": vol, "ideas": ideas, "opciones": len(cad), "liquidas": liquidas,
            "mesa": veredicto}


# ---------- en papel ----------
def abrir_papel(papel: list[dict], idea: dict, tk: str, hoy: date, hora: str) -> list[dict]:
    d = idea["detalle"]
    if any(p["opcion"] == idea["opcion"] and p["estado"] == "abierta" for p in papel):
        return papel
    lado = "venta" if idea["estrategia"] == "lanzamiento cubierto" else "compra"
    precio = d["bid"] if lado == "venta" else d["ask"]
    papel.append({"fecha": hoy.isoformat(), "hora": hora, "ticker": tk, "estrategia": idea["estrategia"], "opcion": idea["opcion"],
                  "lado": lado, "precio": precio, "strike": d["strike"], "tipo": d["tipo"], "vence": d["vence"], "contratos": d.get("lotes") or d.get("contratos") or 1,
                  "spot_entrada": None, "estado": "abierta"})
    return papel


def valuar_papel(papel: list[dict], precio_op, spot_de, hoy: date) -> list[dict]:
    """Marca a mercado cada posición en papel; al vencer, se liquida por valor intrínseco."""
    for p in papel:
        if p["estado"] != "abierta":
            continue
        s = spot_de(p["ticker"])
        if p["vence"] < hoy.isoformat():
            intr = max(0.0, (s - p["strike"]) if p["tipo"] == "C" else (p["strike"] - s)) if s else None
            ahora, p["estado"] = intr, "vencida"
        else:
            ahora = precio_op(p["opcion"])
        if ahora is None:
            continue
        signo = 1 if p["lado"] == "compra" else -1
        p["ahora"] = ahora
        p["resultado"] = round(signo * (ahora - p["precio"]) * LOTE * p["contratos"] - abs(p["precio"]) * LOTE * p["contratos"] * COMISION, 2)
    return papel
