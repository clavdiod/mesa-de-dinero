"""24. Reunión de la mesa: el Jefe y los analistas revisan todo lo que miraron en los últimos días.

Para cada papel que pasó por la mesa (señales de los analistas, propuestas del Jefe, oportunidades, pronósticos,
radar, anticipos, noticias) se compara lo que se dijo con lo que hizo el precio después. Sale:
- Quién acertó y quién no, analista por analista (y en qué tipo de papel).
- Los casos que más enseñan: la mejor idea, el peor error, lo que se escapó.
- Puntos ciegos: papeles que se movieron mucho y nadie marcó.
- Lecciones y ajustes: si un analista viene errando mucho con suficientes casos, su voto baja un poco por una
  semana (y vuelve solo); si viene acertando mucho, sube un poco. Nunca más de ±30% y siempre con casos suficientes.
"""
from __future__ import annotations

import statistics as st
from datetime import date, timedelta

NOMBRES = {"tecnico": "Técnico", "historiador": "Historiador", "fuerza_relativa": "Fuerza relativa", "volumen_flujo": "Volumen y flujo",
           "economista": "Economista", "wallstreet": "Wall Street", "cripto": "Cripto", "adr": "Noche de Nueva York",
           "panico": "Comprador de pánico", "anticipo": "Anticipo NY", "anticipador": "Anticipador", "mundo": "Corresponsal", "ministro": "Ministro", "ganadores": "Cazador de ganadores",
           "noticias": "Noticias", "hechos_emisor": "Hechos del emisor", "calificadoras": "Calificadoras", "macro_dolar": "Macro / dólar",
           "acciones": "Acciones", "cedears": "CEDEARs", "soberanos": "Soberanos", "ons": "ONs", "pesos_tasas": "Pesos y tasas",
           "oportunidades_corto": "Oportunidades (corto)", "oportunidades_mediano": "Oportunidades (mediano)", "jefe": "Jefe"}
COMISION = 1.2  # ida y vuelta


def nombre(a: str) -> str:
    return NOMBRES.get(a, a)


def _precio_en(velas: list[dict], fecha: str) -> float | None:
    vs = [v for v in velas if v["fecha"] <= fecha and v.get("cierre")]
    return vs[-1]["cierre"] if vs else None


def reunir(almacen, cache, panel: dict[str, list], hoy: date, dias: int = 7) -> dict:
    """Junta todo lo que pasó por la mesa en los últimos `dias` corridos y lo mide contra el precio de hoy."""
    desde = hoy - timedelta(days=dias)
    fechas = [(desde + timedelta(days=i)).isoformat() for i in range(dias + 1)]
    precio_hoy = {tk: x[0] for tk, x in panel.items() if x and x[0]}
    grupo = {tk: x[4] for tk, x in panel.items() if x}

    def ahora(tk):
        return precio_hoy.get(tk)

    # 1) señales de los analistas (una por agente, papel y día; precio del momento)
    senales = []
    for f in fechas:
        for s in (almacen.get(f"senales/{f}") or {}).values():
            p1 = ahora(s["ticker"])
            if not s.get("precio") or not p1 or f == hoy.isoformat():
                continue
            ret = (p1 / s["precio"] - 1) * 100
            if abs(ret) > 40:  # en días no se mueve tanto: es un dato roto (cambio de línea o de ratio), no se cuenta
                continue
            senales.append({**s, "fecha": f, "ret": round(ret, 2), "a_favor": round(ret * s["dir"], 2), "grupo": grupo.get(s["ticker"])})

    # 2) por analista
    por_ag: dict[str, dict] = {}
    for s in senales:
        a = por_ag.setdefault(s["agente"], {"casos": 0, "aciertos": 0, "suma": 0.0, "fuertes": [0, 0], "por_grupo": {}})
        a["casos"] += 1
        a["aciertos"] += int(s["a_favor"] > 0)
        a["suma"] += s["a_favor"]
        if (s.get("fuerza") or 0) >= 0.6:
            a["fuertes"][0] += 1
            a["fuertes"][1] += int(s["a_favor"] > 0)
        g = a["por_grupo"].setdefault(s.get("grupo") or "otro", [0, 0, 0.0])
        g[0] += 1
        g[1] += int(s["a_favor"] > 0)
        g[2] += s["a_favor"]
    agentes = sorted(({"agente": k, "nombre": nombre(k), "casos": v["casos"], "acierto_pct": round(v["aciertos"] / v["casos"] * 100, 1),
                       "promedio_pct": round(v["suma"] / v["casos"], 2),
                       "fuertes": f"{v['fuertes'][1]}/{v['fuertes'][0]}" if v["fuertes"][0] else "—",
                       "por_grupo": {g: {"casos": x[0], "acierto_pct": round(x[1] / x[0] * 100, 1), "promedio_pct": round(x[2] / x[0], 2)}
                                     for g, x in v["por_grupo"].items() if x[0] >= 3}}
                      for k, v in por_ag.items()), key=lambda x: -x["casos"])

    # 3) por papel: lo que dijo la mesa (consenso) contra lo que pasó
    por_tk: dict[str, dict] = {}
    for s in senales:
        t = por_tk.setdefault(s["ticker"], {"ticker": s["ticker"], "grupo": s.get("grupo"), "primera": s["fecha"], "precio_primera": s["precio"],
                                            "favor": set(), "contra": set(), "votos": 0.0})
        if s["fecha"] < t["primera"]:
            t["primera"], t["precio_primera"] = s["fecha"], s["precio"]
        (t["favor"] if s["dir"] > 0 else t["contra"]).add(s["agente"])
        t["votos"] += s["dir"] * float(s.get("fuerza") or 0.5)
    papeles = []
    for tk, t in por_tk.items():
        p1 = ahora(tk)
        if not p1 or not t["precio_primera"]:
            continue
        velas = cache.velas(tk) if cache else []
        tramo = [v for v in velas if v["fecha"] >= t["primera"]]
        mx = max([v.get("maximo") or v["cierre"] for v in tramo] + [p1])
        mn = min([v.get("minimo") or v["cierre"] for v in tramo] + [p1])
        ret = (p1 / t["precio_primera"] - 1) * 100
        if abs(ret) > 40:
            continue
        dir_mesa = 1 if t["votos"] > 0.3 else -1 if t["votos"] < -0.3 else 0
        papeles.append({"ticker": tk, "grupo": t["grupo"], "desde": t["primera"], "precio_desde": t["precio_primera"], "precio_hoy": p1,
                        "ret": round(ret, 2), "max": round((mx / t["precio_primera"] - 1) * 100, 2), "min": round((mn / t["precio_primera"] - 1) * 100, 2),
                        "mesa": dir_mesa, "acerto": (ret * dir_mesa > 0) if dir_mesa else None,
                        "favor": sorted(nombre(a) for a in t["favor"]), "contra": sorted(nombre(a) for a in t["contra"])})
    papeles.sort(key=lambda p: -abs(p["ret"]))

    # 4) propuestas del Jefe, simulación y pronósticos
    props = [p for p in (almacen.get("registro/propuestas") or []) if p.get("fecha", "") >= desde.isoformat()]
    jefe = []
    for p in props:
        p1 = ahora(p["ticker"])
        pl = p.get("plan") or {}
        if p1 and pl.get("entrada"):
            jefe.append({"ticker": p["ticker"], "fecha": p["fecha"], "entrada": pl["entrada"], "hoy": p1,
                         "ret": round((p1 / pl["entrada"] - 1) * 100, 2), "estado": (p.get("seguimiento") or {}).get("estado")})
    sim = almacen.get("sim/resumen") or {}
    libreta = almacen.get("pronosticos/libreta") or []
    pron: dict[str, dict] = {}
    for x in libreta:
        r = pron.setdefault(x["origen"], {"se_dio": 0, "fallo": 0, "no_se_dio": 0, "en_curso": 0, "esperando": 0, "va": []})
        r[x["estado"]] += 1
        if x["estado"] == "en_curso":
            r["va"].append(x.get("ahora_pct") or 0)
    for r in pron.values():
        r["va_promedio"] = round(st.mean(r["va"]), 2) if r["va"] else None
        r.pop("va")

    # 5) puntos ciegos: lo que más se movió y nadie marcó (acciones y CEDEARs con historial)
    revisados = set(por_tk)
    ciegos = []
    for tk, g in grupo.items():
        if g not in ("acciones", "cedears") or tk in revisados or tk[-1:] in ("D", "C") and tk[:-1] in grupo:
            continue
        velas = cache.velas(tk) if cache else []
        p0 = _precio_en(velas, desde.isoformat())
        p1 = ahora(tk)
        if p0 and p1:
            r = (p1 / p0 - 1) * 100
            if abs(r) >= 8:
                ciegos.append({"ticker": tk, "grupo": g, "ret": round(r, 2)})
    ciegos.sort(key=lambda x: -x["ret"])

    return {"fecha": hoy.isoformat(), "desde": desde.isoformat(), "senales": len(senales), "agentes": agentes, "papeles": papeles[:40],
            "jefe": jefe, "simulacion": {k: sim.get(k) for k in ("total", "todas", "abiertas", "latente")}, "pronosticos": pron,
            "ciegos": ciegos[:12]}


def ajustes(reunion: dict, previos: dict | None = None, minimo: int = 25) -> dict:
    """Ajuste de voto por una semana según lo que pasó: solo con casos suficientes y diferencias claras."""
    from .riesgo import plazo_de
    out = {}
    for a in reunion["agentes"]:
        # una semana alcanza para juzgar ideas de días, no las de 1 a 3 meses (Economista, Wall Street, Pánico)
        if a["casos"] < minimo or plazo_de(a["agente"]) > 10:
            continue
        if a["acierto_pct"] <= 40 and a["promedio_pct"] < -COMISION:
            f = 0.7
        elif a["acierto_pct"] <= 45 and a["promedio_pct"] < 0:
            f = 0.85
        elif a["acierto_pct"] >= 62 and a["promedio_pct"] > COMISION:
            f = 1.2
        elif a["acierto_pct"] >= 56 and a["promedio_pct"] > COMISION / 2:
            f = 1.1
        else:
            continue
        out[a["agente"]] = {"factor": f, "hasta": (date.fromisoformat(reunion["fecha"]) + timedelta(days=7)).isoformat(),
                            "motivo": f"{a['acierto_pct']:.0f}% de aciertos y {a['promedio_pct']:+.1f}% promedio en {a['casos']} señales de la semana"}
    return out


def lecciones(r: dict) -> list[str]:
    """Conclusiones automáticas en castellano simple (la mesa las muestra; las importantes se pasan a la bitácora)."""
    out = []
    buenos = [a for a in r["agentes"] if a["casos"] >= 15 and a["acierto_pct"] >= 58 and a["promedio_pct"] > 0]
    malos = [a for a in r["agentes"] if a["casos"] >= 15 and a["acierto_pct"] <= 42 and a["promedio_pct"] < 0]
    if buenos:
        out.append("Acertaron esta semana: " + ", ".join(f"{a['nombre']} ({a['acierto_pct']:.0f}% en {a['casos']}, {a['promedio_pct']:+.1f}%)" for a in buenos[:4]) + ".")
    if malos:
        out.append("Erraron esta semana: " + ", ".join(f"{a['nombre']} ({a['acierto_pct']:.0f}% en {a['casos']}, {a['promedio_pct']:+.1f}%)" for a in malos[:4]) + ".")
    for a in r["agentes"]:
        for g, x in a["por_grupo"].items():
            if x["casos"] >= 10 and (x["acierto_pct"] <= 35 or x["acierto_pct"] >= 70):
                out.append(f"{a['nombre']} en {g}: {x['acierto_pct']:.0f}% en {x['casos']} casos ({x['promedio_pct']:+.1f}%).")
    con = [p for p in r["papeles"] if p["mesa"]]
    if con:
        ok = sum(1 for p in con if p["acerto"])
        out.append(f"Cuando la mesa tuvo opinión clara sobre un papel, acertó la dirección en {ok} de {len(con)}.")
    if r["ciegos"]:
        out.append("Se nos escaparon (se movieron 8% o más y nadie los marcó): " + ", ".join(f"{c['ticker']} {c['ret']:+.0f}%" for c in r["ciegos"][:6]) + ".")
    return out
