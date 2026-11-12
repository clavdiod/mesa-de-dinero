"""Análisis al llegar a tu precio de salida (12/11). Pedido de Clau: "cuando llegue analicemos qué conviene, no solo vender
para sacarla de encima: para eso están todos los agentes".

Cuando un papel llega al precio de salida con ganancia, se mira si conviene vender o dejarlo correr con la ganancia asegurada.
Cada factor usa lo que mostró la historia (acciones argentinas, 10 años):
- MACD positivo: +2,2% a un mes contra +0,2% con negativo.
- RSI arriba de 70: +2,6% (lo que sube sigue subiendo); en CEDEARs, al revés (+1,0% contra +1,4%).
- Compra fuerte hoy (volumen 2 veces o más, cerca del máximo): 49 de cada 100 suben a un mes contra 42.
- Venta fuerte hoy: la semana siguiente -1,5%.
- Gráfico: alcista o cayendo.
- Lo que dice la mesa (analistas a favor y en contra).
- Recorrido: si el próximo techo está a menos de 3%, queda poco para ganar.
La combinación no está probada como un todo: es una revisión ordenada, no una garantía. Nunca deja volver a pérdida.
"""
from __future__ import annotations

import statistics as st


def _n(x: float, d: int = 0) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def analizar(tk: str, precio: float, compra: float, salida: float, velas: list[dict], titulo: dict | None,
             grupo: str | None, a_favor: list | None = None, en_contra: list | None = None, hora: str = "13:00") -> dict:
    from . import ficha_frio, estructura
    t = titulo or {}
    c = [v["cierre"] for v in velas if v.get("cierre")] + [precio]
    buenas, malas = [], []
    try:
        lec = ficha_frio.lecturas(c, grupo)
        if lec["macd"] == "positivo":
            buenas.append("MACD positivo (históricamente +2,2% a un mes)")
        else:
            malas.append("MACD negativo (históricamente +0,2% a un mes)")
        if lec["rsi"] > 70:
            (buenas if grupo == "acciones" else malas).append(f"RSI {lec['rsi']}" + (": en acciones argentinas lo que sube sigue subiendo" if grupo == "acciones" else ": sobrecomprado"))
    except Exception:
        pass
    try:
        e = estructura.leer(velas, precio, grupo) or {}
        if e.get("estado") in ("alcista", "confirmado"):
            buenas.append("el gráfico es alcista")
        elif e.get("estado") == "cayendo":
            malas.append("el gráfico sigue cayendo")
    except Exception:
        pass
    vols = [v.get("volumen") or 0 for v in velas[-20:] if v.get("volumen")]
    if vols and t.get("volumen") and st.mean(vols):
        h, m = (int(x) for x in (hora or "13:00").split(":")[:2])
        rel = t["volumen"] / min(1.0, max(0.15, (h * 60 + m - 630) / 390)) / st.mean(vols)
        hi, lo = t.get("maximo") or precio, t.get("minimo") or precio
        pos = (precio - lo) / (hi - lo) if hi > lo else 0.5
        if rel >= 2 and pos >= 0.7 and (t.get("variacion") or 0) > 0:
            buenas.append(f"compradores fuertes hoy ({_n(rel, 1)} veces el volumen normal)")
        elif rel >= 2 and pos <= 0.3 and (t.get("variacion") or 0) < 0:
            malas.append(f"vendedores fuertes hoy ({_n(rel, 1)} veces el volumen normal)")
    nf, nc = len(a_favor or []), len(en_contra or [])
    if nf > nc:
        buenas.append(f"la mesa está a favor ({nf} contra {nc})")
    elif nc > nf:
        malas.append(f"la mesa está en contra ({nc} contra {nf})")
    # recorrido hasta el próximo techo (máximo de las últimas 60 ruedas por encima del precio)
    arriba = sorted(x for x in c[-120:-1] if x > precio * 1.005)
    techo = None
    if arriba:
        techo = max(c[-60:]) if max(c[-60:]) > precio * 1.005 else arriba[0]
        if techo / precio - 1 < 0.03:
            malas.append(f"el próximo techo ({_n(techo)}) está a menos de 3%")
        elif techo / precio - 1 >= 0.08:
            buenas.append(f"hay recorrido hasta {_n(techo)} (+{_n((techo / precio - 1) * 100)}%)")
    puntaje = len(buenas) - len(malas)
    # la alarma para lo que quede: nunca debajo de una ganancia neta (compra + comisiones) ni a más de 3% del precio de hoy
    alarma = round(max(compra * 1.015, salida * 0.985, precio * 0.97), 2)
    gan_neta = (alarma / compra - 1 - 0.012) * 100
    obj = round(techo if techo and techo > precio * 1.03 else precio * 1.08, 2)
    if puntaje >= 2:
        accion, txt = "dejar_correr", (f"Llegó a tu precio con ganancia y la mayoría de los agentes ve que puede seguir: DEJALA CORRER. "
                                       f"Subí la alarma de venta a {_n(alarma)} (si baja hasta ahí, vendés igual con +{_n(gan_neta, 1)}% neto: no volvés a pérdida). "
                                       f"Próximo objetivo: {_n(obj)}.")
    elif puntaje <= -1:
        accion, txt = "vender_todo", "Llegó a tu precio con ganancia y los agentes ven más motivos para que baje que para que siga: VENDÉ y asegurá la ganancia."
    else:
        accion, txt = "vender_mitad", (f"Llegó a tu precio con ganancia y los agentes están divididos: VENDÉ LA MITAD y dejá correr el resto "
                                       f"con alarma en {_n(alarma)} (no vuelve a pérdida) hacia {_n(obj)}.")
    return {"accion": accion, "texto": txt, "a_favor": buenas, "en_contra": malas, "alarma": alarma, "objetivo": obj, "puntaje": puntaje}
