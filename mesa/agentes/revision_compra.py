"""20/11 (pedido de Clau con el aviso de TRAN): "no me avises; que revise automáticamente el Comité antes, y después si
entro o no me avisás".

Cuando aparece una compra grande en una acción argentina que no tenés, la mesa la revisa sola antes de avisarte, con lo
mismo que usa para cualquier propuesta:
- la ficha en frío (rango normal, historia de casos parecidos, MACD, techo/piso): tiene que dar "acompañan";
- las noticias de la empresa (Corresponsal): si hay noticias fuertes en contra, no;
- la punta compradora/vendedora: si la diferencia es grande (más de 1,5%), entrar y salir cuesta demasiado.
Si pasa todo, te llega "ENTRAR" con precio límite, cantidad (según tu capital y riesgo), alarma de venta, objetivo y
plazo. Si no pasa, te llega "NO ENTRAR" con el motivo, sin sonar como importante.

Plazo y números: probado 06/11 (66 acciones, 10 años, en dólares, neto): compras así después de una caída de 20%+
subieron 54 de cada 100 veces en el mes siguiente (+4,5% promedio; 1 de cada 3, más de 10%).
"""
from __future__ import annotations

import statistics as st

SPREAD_MAX = 1.5


def _n(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def revisar(ctx, almacen, aviso: dict, noticias_de=None) -> dict:
    """Devuelve el aviso reescrito con el veredicto de la mesa (tipo 'compra_grande_rev', campo 'entrar')."""
    from . import ficha_frio, estructura
    tk = str(aviso.get("ticker") or "").split(" ")[0].upper()
    t = ctx.titulo(tk) or {}
    pr = t.get("ultimo")
    base = {**aviso, "tipo": "compra_grande_rev", "entrar": False}
    vel = ctx.cache.velas(tk) if ctx.cache else []
    if not pr or len(vel) < 120:
        base["ticker"] = f"{tk}: compra grande → no entrar"
        base["texto"] = "La mesa no pudo revisarla (faltan datos de precio o historia), así que no la propone. " + aviso.get("texto", "")
        return base
    motivos = []
    # 1) punta: entrar y salir no puede costar de más
    c_, v_ = t.get("compra"), t.get("venta")
    spread = (v_ / c_ - 1) * 100 if c_ and v_ and v_ >= c_ else None
    if spread is not None and spread > SPREAD_MAX:
        motivos.append(f"entre la punta compradora y la vendedora hay {_n(spread, 1)}%: entrar y salir cuesta demasiado")
    # 2) plan: alarma a 2 veces el movimiento diario normal (entre 5% y 12%), objetivo 2 veces el riesgo, ~1 mes
    atr = st.mean([v["maximo"] - v["minimo"] for v in vel[-14:] if v.get("maximo") and v.get("minimo")] or [pr * 0.03])
    dist = min(0.12, max(0.05, 2 * atr / pr))
    entrada = round(v_ if v_ and spread is not None and spread <= SPREAD_MAX else pr, 2)
    stop, obj = round(entrada * (1 - dist), 2), round(entrada * (1 + 2 * dist), 2)
    plan = {"ticker": tk, "entrada": entrada, "stop": stop, "objetivo": obj}
    # 3) noticias
    nots, sen = [], None
    if noticias_de:
        try:
            sen = next(iter(noticias_de([tk])), None)
        except Exception:
            sen = None
    if sen is not None and abs(sen.direccion):
        nots = [{"dir": sen.direccion, "texto": sen.texto}]
        if sen.direccion < 0 and sen.fuerza >= 0.4:
            motivos.append("noticias fuertes en contra: " + sen.texto[:140])
    # 4) ficha en frío
    f = None
    try:
        f = ficha_frio.ficha(vel[-400:], entrada, plan, estructura.leer(vel[-300:], entrada, "acciones") or {}, [], "acciones",
                             None, nots, t.get("variacion"))
    except Exception as ex:
        print(f"[revision compra] ficha {tk}: {ex}")
    if not f:
        motivos.append("no se pudo armar la ficha en frío")
    elif f.get("veredicto") != "acompañan":
        motivos.append("la revisión en frío no acompaña (" + ("; ".join(f.get("alertas") or []) or f.get("veredicto")) + ")")
    # cantidad según tu capital (usuario/capital: riesgo por idea y tope por posición)
    cap = almacen.get("usuario/capital") or {}
    monto = float(cap.get("monto_ars") or 1_000_000)
    riesgo_ars = monto * float(cap.get("riesgo_pct") or 1.5) / 100
    cant = int(riesgo_ars / (entrada - stop)) if entrada > stop else 0
    tope = monto * float(cap.get("tope_posicion_pct") or 25) / 100
    if cant * entrada > tope:
        cant = int(tope / entrada)
    nota_n = (" Noticias: " + nots[0]["texto"][:140] + ".") if nots else ""
    if motivos:
        base["ticker"] = f"{tk}: compra grande → no entrar"
        base["texto"] = (f"La mesa la revisó y NO conviene entrar: " + "; ".join(motivos) + f". Precio {_n(pr, 2)}." + nota_n
                         + " Lo que vio el radar: " + aviso.get("texto", "").split(" Precio ")[0].replace("⭐🟢 ", "").replace("🟢 ", ""))
        return base
    base["entrar"] = True
    base["ticker"] = f"⭐ {tk}: la mesa dice ENTRAR"
    base["plan"] = {**plan, "cantidad": cant}
    base["texto"] = (f"Compra grande revisada por la mesa: ✅ entrar. Comprá {cant} {tk} con límite {_n(entrada, 2)} (≈ ${_n(cant * entrada)}). "
                     f"Alarma de venta {_n(stop, 2)} (-{_n(dist * 100, 1)}%: si llega, perdés ≈ ${_n(cant * (entrada - stop))}, "
                     f"{_n(riesgo_ars / monto * 100, 1)}% de tu capital). Objetivo {_n(obj, 2)} (+{_n(2 * dist * 100, 1)}%: ≈ +${_n(cant * (obj - entrada))}). "
                     "⏳ Plazo: alrededor de un mes (en 10 años, compras así después de una caída subieron 54 de cada 100 veces en el mes siguiente; "
                     "1 de cada 3, más de 10%)." + nota_n + " " + ficha_frio.texto(f))
    return base
