"""Informe de la semana (14/11). Pedido de Clau tras ver el informe semanal de ScreenerMatic: el de la mesa, con lectura,
junto con lo que aprendieron los analistas en el reentrenamiento del viernes.

Se arma el último día hábil de la semana, después de reentrenar. Secciones:
mercado (riesgo país y dólar en la semana), sectores argentinos, tu cartera, operaciones de la semana,
lo que aprendieron los agentes (cambios de peso, bajas, aprendizajes nuevos), bonos (ley local contra Nueva York,
asimetría, dólar/tasas/inflación esperada) y lo que viene (cobros y vencimientos).
"""
from __future__ import annotations

import statistics as st
from datetime import date, timedelta


def _p(x: float | None, d: int = 1, signo: bool = True) -> str:
    if x is None:
        return "—"
    s = f"{x:+.{d}f}" if signo else f"{x:.{d}f}"
    return s.replace(".", ",") + "%"


def _n(x: float, d: int = 0) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _cambio(serie: dict[str, float], desde: str) -> tuple[float | None, float | None]:
    fs = sorted(f for f in serie if f)
    if not fs:
        return None, None
    ult = serie[fs[-1]]
    ant = [f for f in fs if f <= desde]
    return ult, (serie[ant[-1]] if ant else None)


def ley_local_vs_ny(panel: dict, flujos: dict, hoy: date) -> dict | None:
    """TIR del AL30 contra el GD30 (mismos pagos): cuánto paga de más (o de menos) la ley argentina."""
    from . import renta_fija as rf
    out = {}
    for tk in ("AL30", "GD30", "AL35", "GD35"):
        x = panel.get(tk + "D") or panel.get(tk + "C")
        fl = (flujos.get(tk) or {}).get("flujos")
        if x and x[0] and fl:
            liq = rf.liquidacion(hoy)
            t = rf.tir(rf.futuros(fl, liq), float(x[0]), liq)
            if t is not None:
                out[tk] = round(t, 2)  # ya viene en %
    if "AL30" in out and "GD30" in out:
        out["spread_30_pb"] = round((out["AL30"] - out["GD30"]) * 100)
    if "AL35" in out and "GD35" in out:
        out["spread_35_pb"] = round((out["AL35"] - out["GD35"]) * 100)
    return out or None


def armar(a, hoy: date, panel: dict, velas, sector, flujos: dict, macro: dict, aprendizajes: list[dict]) -> dict:
    lunes = hoy - timedelta(days=hoy.weekday())
    viernes_ant = (lunes - timedelta(days=3)).isoformat()
    semana = f"{lunes.strftime('%d/%m')} al {hoy.strftime('%d/%m')}"
    secciones, destacado = [], []
    previo = a.get("informe/semanal") or {}
    estado = a.get("ui/estado") or {}

    # 1. mercado
    try:
        rp, rp0 = _cambio(macro.get("riesgo_pais") or {}, viernes_ant)
        ccl, ccl0 = _cambio(macro.get("ccl") or {}, viernes_ant)
        of, of0 = _cambio(macro.get("oficial") or {}, viernes_ant)
        l = []
        if rp is not None:
            l.append(f"Riesgo país {_n(rp)}" + (f" ({'+' if rp - rp0 >= 0 else ''}{_n(rp - rp0)} puntos en la semana)" if rp0 else ""))
        if ccl:
            l.append(f"dólar CCL ${_n(ccl)}" + (f" ({_p((ccl / ccl0 - 1) * 100)})" if ccl0 else ""))
        if of:
            l.append(f"oficial ${_n(of)}" + (f" ({_p((of / of0 - 1) * 100)})" if of0 else ""))
        if l:
            secciones.append({"titulo": "🇦🇷 Mercado", "lineas": ["; ".join(l) + "."]})
            if rp is not None and rp0:
                destacado.append(f"riesgo país {'bajó' if rp < rp0 else 'subió'} {_n(abs(rp - rp0))} puntos")
    except Exception as ex:
        print(f"[informe] mercado: {ex}")

    # 2. sectores argentinos (cierre de hoy contra el viernes anterior)
    try:
        por_sec, papeles = {}, []
        for tk, x in panel.items():
            if not x or len(x) < 5 or x[4] != "acciones" or not x[0]:
                continue
            vs = [v for v in velas(tk) if v.get("cierre") and v.get("fecha", "") <= viernes_ant]
            if not vs:
                continue
            r = (float(x[0]) / vs[-1]["cierre"] - 1) * 100
            if abs(r) > 60:
                continue  # dato raro (split o error)
            papeles.append((r, tk))
            por_sec.setdefault(sector(tk), []).append(r)
        if papeles:
            sec = sorted(((st.mean(v), s) for s, v in por_sec.items() if len(v) >= 2), reverse=True)
            papeles.sort(reverse=True)
            sube = sum(1 for r, _ in papeles if r > 0)
            lin = [f"{sube} de {len(papeles)} acciones subieron. Promedio del panel: {_p(st.mean(r for r, _ in papeles))}."]
            if sec:
                k = min(3, len(sec) // 2) or 1
                lin.append("Mejores sectores: " + ", ".join(f"{s} {_p(r)}" for r, s in sec[:k]) + ". Peores: " + ", ".join(f"{s} {_p(r)}" for r, s in sec[-k:][::-1]) + ".")
            lin.append("Más subieron: " + ", ".join(f"{tk} {_p(r)}" for r, tk in papeles[:3]) + ". Más bajaron: " + ", ".join(f"{tk} {_p(r)}" for r, tk in papeles[-3:][::-1]) + ".")
            secciones.append({"titulo": "📊 Acciones argentinas en la semana", "lineas": lin})
    except Exception as ex:
        print(f"[informe] sectores: {ex}")

    # 3. tu cartera y operaciones
    try:
        cart = a.get("usuario/cartera") or []
        lin = []
        for c in cart:
            tk = str(c.get("ticker") or "").upper()
            x = panel.get(tk)
            if not x or not x[0] or (len(x) > 4 and x[4] not in ("acciones", "cedears")):
                continue
            pr = float(x[0])
            vs = [v for v in velas(tk) if v.get("cierre") and v.get("fecha", "") <= viernes_ant]
            sem = (pr / vs[-1]["cierre"] - 1) * 100 if vs else None
            tot = (pr / float(c["precio"]) - 1) * 100 if c.get("precio") else None
            lin.append(f"{tk}: {_p(sem)} en la semana, {_p(tot)} desde tu compra (${_n(pr, 2)}).")
        ops = [o for o in (a.get("usuario/operaciones") or []) if isinstance(o, dict) and (o.get("fecha") or "") >= lunes.isoformat()]
        if ops:
            tot_ops = sum(o.get("ganancia") or 0 for o in ops)
            lin.append("Operaciones cerradas en la semana: " + ", ".join(f"{o['ticker']} {'+' if (o.get('ganancia') or 0) >= 0 else '−'}${_n(abs(o.get('ganancia') or 0))}" for o in ops)
                       + f". Total {'+' if tot_ops >= 0 else '−'}${_n(abs(tot_ops))}.")
            destacado.append(f"cerraste {len(ops)} {'operaciones' if len(ops) > 1 else 'operación'} ({'+' if tot_ops >= 0 else '−'}${_n(abs(tot_ops))})")
        if lin:
            secciones.append({"titulo": "💼 Tu cartera", "lineas": lin})
    except Exception as ex:
        print(f"[informe] cartera: {ex}")

    # 4. lo que aprendieron los agentes
    pesos = ((estado.get("comite") or {}).get("pesos")) or {}
    try:
        from .revision import nombre
    except Exception:
        nombre = lambda k: k
    try:
        lin = []
        ant = previo.get("pesos") or {}
        cambios = []
        for k, v in pesos.items():
            p0 = (ant.get(k) or {}).get("peso")
            if p0 is not None and abs((v.get("peso") or 0) - p0) >= 0.15:
                cambios.append((v["peso"] - p0, k, p0, v["peso"], v.get("acierto")))
        for d_, k, p0, p1, ac in sorted(cambios, reverse=True):
            lin.append(f"{nombre(k)}: su voto pasó de x{_n(p0, 1)} a x{_n(p1, 1)} (acierta {ac}%).")
        bajas = [nombre(k) for k, v in pesos.items() if v.get("baja")]
        if bajas:
            lin.append("Dados de baja por acertar poco (no votan): " + ", ".join(bajas) + ".")
        top = sorted(((v.get("peso") or 0, k, v.get("acierto")) for k, v in pesos.items() if not v.get("baja")), reverse=True)[:3]
        if top:
            lin.append("Los que más pesan hoy: " + ", ".join(f"{nombre(k)} (acierta {ac}%)" for _, k, ac in top) + ".")
        nuevos = [x for x in aprendizajes if str(x.get("fecha") or "") >= lunes.isoformat()]
        if nuevos:
            lin.append(f"{len(nuevos)} aprendizajes nuevos esta semana:")
            lin += [f"• {x.get('caso')}: {x.get('cambio') or x.get('leccion')}"[:260] for x in nuevos]
        if lin:
            secciones.append({"titulo": "🧠 Lo que aprendieron los analistas", "lineas": lin})
    except Exception as ex:
        print(f"[informe] aprendizaje: {ex}")

    # 5. bonos, dólar y tasas
    try:
        lin = []
        ley = ley_local_vs_ny(panel, flujos, hoy)
        if ley and ley.get("spread_30_pb") is not None:
            s = ley["spread_30_pb"]
            lin.append(f"Ley argentina contra Nueva York: AL30 rinde {_p(ley['AL30'], 2, False)} y GD30 {_p(ley['GD30'], 2, False)} "
                       f"({'+' if s >= 0 else ''}{s} puntos básicos para la ley local"
                       + (f"; en los 35: {'+' if ley['spread_35_pb'] >= 0 else ''}{ley['spread_35_pb']})." if ley.get("spread_35_pb") is not None else ").")
                       + (" La ley local paga MENOS que la de Nueva York: el mercado no le cobra el riesgo legal extra." if s < 0 else " La ley local paga más: el mercado cobra el riesgo legal."))
        asi = estado.get("asimetria") or {}
        if asi.get("resumen"):
            lin.append(asi["resumen"].split(" Ojo:")[0])
        cur = estado.get("curvas") or a.get("macro/curvas") or {}
        lin += [l_ for l_ in (cur.get("lineas") or []) if l_.startswith(("Pesos contra", "Inflación que espera", "Dólar mayorista"))]
        if lin:
            secciones.append({"titulo": "💵 Bonos, dólar y tasas", "lineas": lin})
    except Exception as ex:
        print(f"[informe] bonos: {ex}")

    # 6. lo que viene
    try:
        lim = (hoy + timedelta(days=9)).isoformat()
        cob = [c for c in (estado.get("cobros") or []) if hoy.isoformat() < str(c.get("fecha") or "") <= lim]
        lin = []
        if cob:
            lin.append("Cobrás: " + "; ".join(f"{str(c['fecha'])[8:10]}/{str(c['fecha'])[5:7]} {c.get('ticker') or c.get('nombre') or ''}" for c in cob[:8]) + ".")
        evs = [e for e in (estado.get("eventos") or []) if hoy.isoformat() < str(e.get("fecha") or "") <= lim and e.get("tipo") in ("balance", "dato", "licitacion", "feriado")]
        if evs:
            lin.append("En la agenda: " + "; ".join(f"{str(e['fecha'])[8:10]}/{str(e['fecha'])[5:7]} {e.get('nombre') or e.get('ticker') or e.get('tipo')}" for e in evs[:8]) + ".")
        if lin:
            secciones.append({"titulo": "📅 La semana que viene", "lineas": lin})
    except Exception as ex:
        print(f"[informe] agenda: {ex}")

    titulo = f"Informe de la semana ({semana})"
    resumen = (destacado[0][:1].upper() + destacado[0][1:] + (", " + ", ".join(destacado[1:]) if destacado[1:] else "") + ".") if destacado else "Mirá cómo te fue y qué aprendió la mesa."
    return {"fecha": hoy.isoformat(), "semana": semana, "titulo": titulo, "resumen": resumen, "secciones": secciones, "pesos": pesos}
