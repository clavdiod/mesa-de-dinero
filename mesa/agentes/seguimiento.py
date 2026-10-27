"""Seguimiento activo: en cada ronda, qué hacer con cada posición abierta y qué opina la mesa de lo que tenés.

Para cada propuesta en curso:
- salir: la idea se rompió (la mesa ahora está en contra o apareció un hecho grave).
- antes_balance: presenta balance antes del objetivo; conviene salir o achicar.
- subir_stop: ya ganó 1R (stop al precio de compra: no puede perder) o 2R (stop a +1R).
- cerca_stop: le falta poco para tocar el stop.
- cancelar: la orden límite todavía no entró y la mesa dejó de verla.
- mantener: todo en orden.
"""
from __future__ import annotations

from datetime import timedelta

ALERTA = {"salir", "antes_balance", "subir_stop", "cancelar"}


def _balance(ctx, tk: str, dias: int = 3) -> dict | None:
    lim = (ctx.fecha + timedelta(days=dias)).isoformat()
    return next((e for e in ctx.eventos if e.get("tipo") == "balance" and e.get("ticker") == tk
                 and ctx.fecha.isoformat() <= e.get("fecha", "") <= lim), None)


def consejo(p: dict, ctx, senales: list, puntaje: float) -> dict:
    seg, pl = p["seguimiento"], p["plan"]
    t = ctx.titulo(p["ticker"]) or {}
    ult = t.get("ultimo")
    contra = sorted((s for s in senales if s.direccion < 0 or s.veto), key=lambda s: -s.fuerza)
    if seg["estado"] == "pendiente":
        if any(s.veto for s in senales) or puntaje <= -0.3:
            return {"accion": "cancelar", "texto": f"Cancelá la orden: la mesa ya no la ve ({contra[0].texto if contra else 'cambió la opinión'})."}
        return {"accion": "esperar", "texto": f"Orden límite en {pl['entrada']:g}: todavía no entró."}
    if not ult:
        return {"accion": "mantener", "texto": "Sin precio en esta ronda."}
    entrada = seg.get("precio_entrada") or pl["entrada"]
    riesgo = entrada - pl["stop"]
    r = (ult - entrada) / riesgo if riesgo > 0 else 0
    if any(s.veto for s in senales) or puntaje <= -0.5:
        return {"accion": "salir", "r": round(r, 2),
                "texto": f"Salir: la idea se rompió. {contra[0].texto if contra else ''}".strip()}
    bal = _balance(ctx, p["ticker"])
    if bal:
        return {"accion": "antes_balance", "r": round(r, 2),
                "texto": f"Presenta balance el {bal['fecha'][8:10]}/{bal['fecha'][5:7]}: conviene salir o achicar antes ({r:+.1f}R ahora)."}
    if r >= 2:
        nuevo = round(entrada + riesgo, 4)
        return {"accion": "subir_stop", "r": round(r, 2), "stop_sugerido": nuevo,
                "texto": f"Va {r:+.1f}R: subí el stop a {nuevo:g} (asegura +1R)."}
    if r >= 1:
        return {"accion": "subir_stop", "r": round(r, 2), "stop_sugerido": entrada,
                "texto": f"Va {r:+.1f}R: subí el stop al precio de compra ({entrada:g}). Así ya no puede perder."}
    if r <= -0.7:
        return {"accion": "cerca_stop", "r": round(r, 2), "texto": f"Cerca del stop ({pl['stop']:g}): {r:+.1f}R. Respetalo si lo toca."}
    favor = sum(1 for s in senales if s.direccion > 0)
    return {"accion": "mantener", "r": round(r, 2),
            "texto": f"Mantener ({r:+.1f}R). La mesa hoy: {favor} a favor, {len(contra)} en contra."}


def revisar(reg, ctx, por_ticker: dict, puntaje_fn) -> list[dict]:
    """Actualiza el consejo de cada propuesta abierta. Devuelve alertas nuevas (solo de las que aprobaste)."""
    alertas = []
    for p in reg.abiertas():
        sen = por_ticker.get(p["ticker"], [])
        c = consejo(p, ctx, sen, puntaje_fn(sen))
        c["hora"] = ctx.hora
        previo = (p["seguimiento"].get("consejo") or {}).get("accion")
        if c["accion"] != previo:  # solo se actualiza si cambia el consejo (cuida las escrituras)
            p["seguimiento"]["consejo"] = c
        if c["accion"] in ALERTA and c["accion"] != previo and p.get("decision") == "aprobada":
            alertas.append({"fecha": ctx.fecha.isoformat(), "hora": ctx.hora, "ticker": f"{p['ticker']} ({c['accion']})",
                            "texto": f"{p['ticker']}: {c['texto']}"})
    return alertas


def _nom(a: str) -> str:
    from .revision import nombre
    return nombre(a)


def opinion_cartera(ctx, cartera: list[dict], por_ticker: dict, puntaje_fn) -> dict:
    """Qué opina la mesa de cada cosa que tenés (sin stop ni objetivo: solo el pulso)."""
    out = {}
    for c in cartera:
        tk = str(c.get("ticker", "")).upper()
        base = tk[:-1] if tk.endswith(("D", "C")) and ctx.titulo(tk[:-1]) else tk
        sen = por_ticker.get(tk, []) + (por_ticker.get(base, []) if base != tk else [])
        if not sen and not _balance(ctx, base, 7):
            continue
        pj = puntaje_fn(sen)
        bal = _balance(ctx, base, 7)
        out[tk] = {"favor": sum(1 for s in sen if s.direccion > 0), "contra": sum(1 for s in sen if s.direccion < 0),
                   "puntaje": round(pj, 2), "veredicto": "a favor" if pj >= 0.5 else "en contra" if pj <= -0.5 else "neutral",
                   "principal": (max(sen, key=lambda s: s.fuerza).texto if sen else ""),
                   "a_favor": sorted({_nom(s.agente) for s in sen if s.direccion > 0}),
                   "en_contra": sorted({_nom(s.agente) for s in sen if s.direccion < 0}),
                   "balance": bal["fecha"] if bal else None}
    return out
