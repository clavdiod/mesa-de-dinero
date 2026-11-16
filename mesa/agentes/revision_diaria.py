"""Revisión diaria al cierre (16/11). Pedido de Clau: que la mesa revise sola todos los días y avise SOLO si pasa algo
que valga la pena. Si no pasa nada, no escribe.

Qué mira:
- Pronósticos sobre tus papeles que se cerraron hoy (se dieron, fallaron o vencieron).
- Analistas: si a alguno se le cayó el acierto 10 puntos o más (con 10 casos o más), si quedó dado de baja o si volvió.
- Tu cartera: papeles a menos de 3% de la alarma de venta o a menos de 2% del precio de salida con ganancia.
"""
from __future__ import annotations

from datetime import date


def _base(tk: str) -> str:
    tk = str(tk or "").upper()
    return tk[:-1] if tk[-1:] in ("D", "C") and len(tk) > 3 else tk


def armar(a, hoy: date, panel: dict) -> list[str]:
    h = hoy.isoformat()
    puntos = []
    cart = a.get("usuario/cartera") or []
    mios = {_base(c.get("ticker")) for c in cart} | {str(c.get("ticker") or "").upper() for c in cart}

    # 1. pronósticos sobre tus papeles cerrados hoy
    try:
        from .revision import nombre
    except Exception:
        nombre = lambda k: k
    vistos = set()
    for x in a.get("pronosticos/libreta") or []:
        if x.get("fecha_cierre") != h or str(x.get("ticker") or "").upper() not in mios and _base(x.get("ticker")) not in mios:
            continue
        clave = (_base(x.get("ticker")), x.get("origen"), x.get("estado"))
        if clave in vistos:
            continue  # el mismo pronóstico anotado en pesos y en dólares (YPFD / YPFDD)
        vistos.add(clave)
        est = {"se_dio": "✅ se cumplió", "fallo": "❌ falló (tocó el stop)", "no_se_dio": "⌛ venció sin cumplirse"}.get(x.get("estado"), x.get("estado"))
        puntos.append(f"{x.get('ticker')}: el pronóstico de {nombre(x.get('origen') or '')} {est}"
                      + (f" (iba a {'+' if (x.get('objetivo_pct') or 0) >= 0 else ''}{str(x.get('objetivo_pct')).replace('.', ',')}%)" if x.get("objetivo_pct") is not None else "") + ".")

    # 2. salud de los analistas (pesos del Comité de hoy contra los de ayer)
    est = a.get("ui/estado") or {}
    pesos = ((est.get("comite") or {}).get("pesos")) or {}
    prev = (a.get("revision/pesos") or {}).get("pesos") or {}
    for k, v in pesos.items():
        p = prev.get(k) or {}
        if not p:
            continue
        if v.get("baja") and not p.get("baja"):
            puntos.append(f"🔻 {nombre(k)} quedó dado de baja: acierta {v.get('acierto')}% en {v.get('casos')} casos. Ya no vota.")
        elif p.get("baja") and not v.get("baja"):
            puntos.append(f"🔺 {nombre(k)} volvió a votar: subió a {v.get('acierto')}% de acierto.")
        elif (v.get("casos") or 0) >= 10 and p.get("acierto") is not None and v.get("acierto") is not None and v["acierto"] - p["acierto"] <= -10:
            puntos.append(f"⚠️ {nombre(k)} empezó a fallar: su acierto bajó de {p['acierto']}% a {v['acierto']}% ({v.get('casos')} casos). Su voto ya pesa menos.")
    if pesos:
        a.put("revision/pesos", {"fecha": h, "pesos": pesos})

    # 3. tu cartera cerca de una alarma o del precio de salida
    for c in cart:
        tk = str(c.get("ticker") or "").upper()
        x = panel.get(tk)
        if not x or not x[0]:
            continue
        pr = float(x[0])
        for al in c.get("alertas") or []:
            if al.get("moneda", "ARS") != "ARS" or not al.get("nivel"):
                continue
            n = float(al["nivel"])
            if al.get("tipo") == "baja" and pr > n and (pr / n - 1) < 0.03:
                puntos.append(f"🟠 {tk} cerró en {pr:,.2f}, a {(pr / n - 1) * 100:.1f}% de su alarma ({n:,.0f}). Mañana puede saltar.".replace(",", "X").replace(".", ",").replace("X", "."))
            elif al.get("tipo") == "sube" and pr < n and (n / pr - 1) < 0.02:
                puntos.append(f"🟢 {tk} cerró en {pr:,.2f}, a {(n / pr - 1) * 100:.1f}% de tu precio de salida ({n:,.0f}). Si llega, los agentes analizan si vender o dejar correr.".replace(",", "X").replace(".", ",").replace("X", "."))
    return puntos


def avisar(a, hoy: date, puntos: list[str]) -> bool:
    """Si hay algo, deja el aviso en la campanita y manda la notificación. Si no hay nada, no hace nada."""
    if not puntos:
        return False
    from ..nucleo import push
    al = a.get("ui/alertas") or []
    al = [x for x in al if not (x.get("tipo") == "revision" and x.get("fecha") == hoy.isoformat())]
    a.put("ui/alertas", ([{"fecha": hoy.isoformat(), "hora": "17:15", "ticker": "🔎 Revisión del día", "tipo": "revision",
                           "texto": " ".join(puntos)}] + al)[:60])
    subs = a.get("push/suscripciones") or []
    if subs:
        print(f"[revision diaria] push: {push.enviar(subs)}")
    return True
