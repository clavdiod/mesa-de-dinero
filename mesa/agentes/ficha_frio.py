"""35. Ficha en frío: antes de comprar, lo que dicen los números de acá a un mes (y a un año), para decidir sin apuro.
Nace del 02/11 (YPFD): el análisis llegó después de la compra; tiene que estar antes.

- Rango normal a un mes (2 de cada 3 veces) según cómo se viene moviendo.
- Casos parecidos del MISMO papel en la historia guardada: misma distancia a su promedio de 20 ruedas (±3 puntos) y
  mismo movimiento de las últimas 20 ruedas (±6 puntos). Qué pasó 20 ruedas después.
- Chance de llegar al objetivo y de tocar el stop antes del plazo, en esos casos.
- El gráfico (cayendo / dejó de caer / alcista, mínimo anual) y los analistas en contra.
"""
from __future__ import annotations

import math
import statistics as st


def _ema(x: list[float], n: int) -> list[float]:
    k, out = 2 / (n + 1), [x[0]]
    for v in x[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def lecturas(c: list[float], grupo: str | None) -> dict:
    """Tendencia, estructura correctiva, RSI y MACD, con lo que rindió cada lectura en 10 años (probado 02/11)."""
    arg = grupo == "acciones"
    d = [b - a for a, b in zip(c[-200:], c[-199:])]
    au = _ema([max(x, 0) for x in d], 27)[-1]; ad = _ema([max(-x, 0) for x in d], 27)[-1]
    rsi = 100 - 100 / (1 + au / ad) if ad else 100
    m = [a - b for a, b in zip(_ema(c, 12), _ema(c, 26))]; sg = _ema(m, 9); h = [a - b for a, b in zip(m, sg)]
    m50, m200 = st.mean(c[-50:]), st.mean(c[-200:]) if len(c) >= 200 else st.mean(c)
    tend = "alcista" if c[-1] > m50 > m200 else "bajista" if c[-1] < m50 < m200 else "mixta"
    corr = c[-1] / max(c[-60:]) - 1
    correctiva = m50 > m200 and -0.20 <= corr <= -0.08
    out = {"rsi": round(rsi), "macd": "positivo" if h[-1] > 0 else "negativo", "macd_cruce": ("arriba" if h[-1] > 0 >= h[-2] else "abajo" if h[-1] < 0 <= h[-2] else None),
           "tendencia": tend, "correctiva": correctiva, "correccion_pct": round(corr * 100, 1)}
    t, buenas, malas = [], [], []
    t.append(f"Tendencia {tend} (precio contra sus promedios de 50 y 200 ruedas)")
    if correctiva:
        t.append(f"estructura correctiva: corrige {abs(corr) * 100:.0f}% dentro de una tendencia alcista")
    t.append(f"RSI {rsi:.0f}")
    t.append(f"MACD {out['macd']}" + (f" (cruzó hacia {out['macd_cruce']})" if out["macd_cruce"] else ""))
    if arg:  # acciones argentinas, 10 años, 20 ruedas
        if out["macd"] == "positivo":
            buenas.append("MACD positivo: en acciones argentinas rindió +2,2% a un mes contra +0,2% con MACD negativo")
        else:
            malas.append("MACD negativo: en acciones argentinas rindió +0,2% a un mes contra +2,2% con MACD positivo")
        if out["macd_cruce"] == "abajo":
            malas.append("el MACD acaba de cruzar hacia abajo (rindió -0,4% a un mes)")
        if rsi > 70:
            buenas.append("RSI arriba de 70: en acciones argentinas no es 'caro', rindió +2,6% (lo que sube sigue subiendo)")
        if correctiva and rsi < 40:
            buenas.append("corrección dentro de tendencia alcista con RSI bajo: rindió +7,4% promedio (pero solo 4 de cada 10 suben: pocas muy grandes)")
    else:  # CEDEARs
        if rsi < 30:
            buenas.append("RSI bajo 30 (sobrevendido): en CEDEARs rindió +2,0% a un mes contra +1,4% promedio")
        if rsi > 70:
            malas.append("RSI arriba de 70 (sobrecomprado): en CEDEARs rindió +1,0% contra +1,4% promedio")
        if out["macd_cruce"] == "arriba":
            buenas.append("el MACD acaba de cruzar hacia arriba (rindió +1,8%)")
    out.update(texto="; ".join(t), buenas=buenas, malas=malas)
    return out


def ficha(velas: list[dict], precio: float, plan: dict, estructura: dict | None, votos: list[dict], grupo: str | None = None,
          contexto: str | None = None, noticias: list[dict] | None = None, variacion: float | None = None) -> dict | None:
    c = [v["cierre"] for v in velas if v.get("cierre")] + [float(precio)]
    if len(c) < 80:
        return None
    r = [math.log(b / a) for a, b in zip(c[-64:], c[-63:]) if a > 0 and b > 0]
    s = st.pstdev(r) * math.sqrt(20) if len(r) > 20 else None
    out = {"rango_1m": [round(precio * math.exp(-s), 2), round(precio * math.exp(s), 2)] if s else None}
    m20 = st.mean(c[-20:]); d_hoy = c[-1] / m20 - 1; r_hoy = c[-1] / c[-21] - 1
    obj, stop = plan.get("objetivo"), plan.get("stop")
    casos = []
    for i in range(40, len(c) - 21):
        mm = st.mean(c[i - 19:i + 1])
        if abs(c[i] / mm - 1 - d_hoy) <= 0.03 and abs(c[i] / c[i - 20] - 1 - r_hoy) <= 0.06:
            fut = c[i + 1:i + 21]
            llega = obj and any(x / c[i] >= obj / precio for x in fut)
            toca = stop and any(x / c[i] <= stop / precio for x in fut)
            casos.append((fut[-1] / c[i] - 1, llega, toca))
    malas = []
    # 02/11 (regla de Clau): ¿el precio de entrada es razonable? ¿cuánto suele subir desde acá?
    subidas = []
    for i in range(40, len(c) - 21):
        mm = st.mean(c[i - 19:i + 1])
        if abs(c[i] / mm - 1 - d_hoy) <= 0.03 and abs(c[i] / c[i - 20] - 1 - r_hoy) <= 0.06:
            subidas.append(max(c[i + 1:i + 21]) / c[i] - 1)
    entrada = float(plan.get("entrada") or precio)
    hi60, lo60 = max(c[-60:]), min(c[-60:])
    pos60 = (entrada - lo60) / (hi60 - lo60) if hi60 > lo60 else 0.5
    estirado = entrada / m20 - 1
    caro = []
    if estirado >= 0.06:
        caro.append(f"la entrada está {estirado * 100:.0f}% arriba de su promedio de 20 ruedas (estirada)".replace(".", ","))
    if pos60 >= 0.85:
        caro.append(f"la entrada está en el {pos60 * 100:.0f}% más alto de su rango de 3 meses")
    if len(subidas) >= 8 and stop:
        sub = sorted(subidas)
        tip, buena = sub[len(sub) // 2], sub[int(len(sub) * 0.75)]
        riesgo = 1 - stop / entrada
        out["subida"] = {"tipica_pct": round(tip * 100, 1), "buena_pct": round(buena * 100, 1), "riesgo_pct": round(riesgo * 100, 1)}
        if tip < 1.5 * riesgo:
            caro.append(f"desde precios así suele subir {tip * 100:.1f}% en un mes (1 de cada 4 veces, {buena * 100:.1f}%) y arriesgás {riesgo * 100:.1f}% hasta el stop: no paga el riesgo".replace(".", ","))
    # 02/11 (revisión de las compras de Clau): el techo real es el máximo del último año. Si hasta ahí no hay al menos
    # 2 veces lo que se arriesga hasta el stop, la entrada no paga. Y el objetivo nunca puede estar arriba de ese techo.
    mx1 = max(c[-250:])
    hasta_max = mx1 / entrada - 1
    out["max_1a"] = round(mx1, 2); out["hasta_max_pct"] = round(hasta_max * 100, 1)
    pct1 = sum(1 for x in c[-250:] if x < entrada) / len(c[-250:]) * 100
    out["percentil_1a"] = round(pct1)
    if stop and hasta_max < 2 * (1 - stop / entrada):
        caro.append(f"hasta su máximo del último año ({mx1:,.0f}) hay solo {hasta_max * 100:.1f}% y arriesgás {(1 - stop / entrada) * 100:.1f}%: no paga".replace(",", "X").replace(".", ",").replace("X", "."))
    # probado el 02/11 (10 años): en CEDEARs, cerca del máximo del año rinde menos (+0,9% contra +1,6% a 20 ruedas);
    # en acciones argentinas NO (+1,6% contra +1,2%: ahí el que sube sigue subiendo). La regla vale solo para CEDEARs.
    if pct1 >= 80 and grupo != "acciones":
        caro.append(f"la entrada está en el {100 - pct1:.0f}% más alto de los precios del último año")
    # pisos y techos del gráfico (con 2+ toques)
    try:
        from .grafico import _niveles, _pivotes
        w = c[-251:-1]
        hi_, lo_ = _pivotes(w)
        sop = [d for d in _niveles([w[j] for j in lo_], entrada, True) if d["toques"] >= 2 and d["nivel"] < entrada]
        res = [d for d in _niveles([w[j] for j in hi_], entrada, False) if d["toques"] >= 2 and d["nivel"] > entrada]
        if sop:
            s_ = max(sop, key=lambda d: d["nivel"]); out["piso"] = s_
            if grupo == "acciones" and entrada <= s_["nivel"] * 1.03:
                malas.append(f"está pegada a un piso ({s_['nivel']:,.0f}) y en acciones argentinas los pisos se perforan 7 de cada 10 veces: el stop tiene que ir debajo".replace(",", "."))
        if res:
            out["techo"] = min(res, key=lambda d: d["nivel"])
    except Exception:
        pass
    # volumen: en acciones argentinas, un día con el doble de volumen rindió +2,8% a 20 ruedas contra +0,5% (probado 02/11)
    vols = [x.get("volumen") or 0 for x in velas[-21:]]
    if len(vols) >= 21 and sum(vols[:-1]) > 0:
        rel = vols[-1] / (sum(vols[:-1]) / 20)
        out["volumen_rel"] = round(rel, 1)
    if obj and obj > mx1 * 1.02:
        out["objetivo_irreal"] = True
        malas.append(f"el objetivo ({obj:,.0f}) está arriba del máximo del último año ({mx1:,.0f})".replace(",", "."))
    try:
        lec = lecturas(c, grupo)
        out["lecturas"] = lec
        malas.extend(lec["malas"])
    except Exception:
        pass
    out["contexto"] = contexto
    # noticias de la empresa (Corresponsal, Hechos del emisor, Calificadoras): explican movimientos raros de los indicadores
    nots = [n for n in noticias or [] if n.get("texto")]
    out["noticias"] = [{"dir": n.get("dir") or 0, "texto": str(n["texto"])[:220]} for n in nots[:3]]
    raro = abs(variacion or 0) >= 3 or (out.get("volumen_rel") or 0) >= 2
    if raro and nots:
        out["explica"] = str(max(nots, key=lambda n: abs(n.get("dir") or 0))["texto"])[:220]
    elif raro:
        out["explica"] = "se mueve fuerte sin una noticia de la empresa que lo explique: ojo, puede ser solo flujo de corto plazo"
    if any((n.get("dir") or 0) < 0 for n in nots) and not any((n.get("dir") or 0) > 0 for n in nots):
        malas.append("hay noticias de la empresa en contra")
    out["entrada_cara"] = caro
    # precio razonable: donde hasta el máximo del año hay al menos 2 veces el riesgo hasta el stop, y no estirado
    razon = min(m20 * 1.02, (mx1 + 2 * stop) / 3 if stop else m20)
    out["entrada_mejor"] = round(razon, 2) if caro and razon < entrada else None
    if len(casos) >= 8:
        v = sorted(x[0] for x in casos)
        out["historia"] = {"casos": len(casos), "mediana_pct": round(v[len(v) // 2] * 100, 1),
                           "arriba": round(sum(1 for x in v if x > 0) / len(v) * 100),
                           "llega_obj": round(sum(1 for x in casos if x[1]) / len(casos) * 100),
                           "toca_stop": round(sum(1 for x in casos if x[2]) / len(casos) * 100)}
    contra = [x["nombre"] for x in votos or [] if x.get("voto", 0) < 0]
    out["contra"] = contra
    out["grafico"] = (estructura or {}).get("estado")
    # veredicto simple: ¿los números acompañan?
    h = out.get("historia") or {}
    if h and h["toca_stop"] > h["llega_obj"]:
        malas.append(f"en casos parecidos tocó el stop más veces ({h['toca_stop']}%) que el objetivo ({h['llega_obj']}%)")
    if h and h["mediana_pct"] < 0:
        malas.append(f"el caso típico terminó en {str(h['mediana_pct']).replace('.', ',')}% a un mes")
    if out["rango_1m"] and obj and obj > out["rango_1m"][1] * 1.05:
        malas.append("el objetivo queda fuera del rango normal de un mes")
    if (estructura or {}).get("estado") == "cayendo":
        malas.append("el gráfico sigue cayendo")
    if len(contra) >= 2:
        malas.append(f"{len(contra)} analistas en contra")
    out["alertas"] = malas
    out["veredicto"] = "cara" if caro else "acompañan" if not malas else "dudosos" if len(malas) == 1 else "en contra"
    return out


def texto(f: dict | None) -> str:
    if not f:
        return ""
    n = lambda x: f"{x:,.0f}".replace(",", ".")
    p = []
    if f.get("rango_1m"):
        p.append(f"Rango normal a un mes: {n(f['rango_1m'][0])} a {n(f['rango_1m'][1])}.")
    h = f.get("historia")
    if h:
        p.append(f"En {h['casos']} momentos parecidos de este papel: terminó arriba {h['arriba']} de cada 100, caso típico {str(h['mediana_pct']).replace('.', ',')}% a un mes; "
                 f"llegó al objetivo {h['llega_obj']}%, tocó el stop {h['toca_stop']}%.")
    if f.get("subida"):
        u = f["subida"]
        p.append(f"Cuánto puede subir según la historia: lo típico {str(u['tipica_pct']).replace('.', ',')}% en un mes, y 1 de cada 4 veces {str(u['buena_pct']).replace('.', ',')}%; "
                 f"arriesgás {str(u['riesgo_pct']).replace('.', ',')}% hasta el stop.")
    if f.get("contexto"):
        p.append(f"Mercado: {f['contexto']}.")
    if f.get("noticias"):
        p.append("Noticias de la empresa: " + " · ".join(("🟢 " if n["dir"] > 0 else "🔴 " if n["dir"] < 0 else "⚪ ") + n["texto"] for n in f["noticias"][:2]))
    if f.get("explica"):
        p.append(f"Por qué se mueve hoy: {f['explica']}.")
    lec = f.get("lecturas")
    if lec:
        p.append(lec["texto"] + "." + (" A favor: " + "; ".join(lec["buenas"]) + "." if lec["buenas"] else ""))
    if f.get("max_1a"):
        p.append(f"Máximo del año {n(f['max_1a'])} ({str(f['hasta_max_pct']).replace('.', ',')}% arriba)" + (f"; próximo techo {n(f['techo']['nivel'])} ({f['techo']['toques']} toques)" if f.get("techo") else "")
                 + (f"; piso más cercano {n(f['piso']['nivel'])} ({f['piso']['toques']} toques)" if f.get("piso") else "") + ".")
    if (f.get("volumen_rel") or 0) >= 2:
        p.append(f"Hoy opera {str(f['volumen_rel']).replace('.', ',')} veces su volumen normal (en acciones argentinas eso rindió +2,8% a un mes contra +0,5%).")
    if f.get("contra"):
        p.append("En contra: " + ", ".join(f["contra"]) + ".")
    p.append({"cara": "❌ Entrada cara: " + "; ".join(f.get("entrada_cara") or []) + (f". Precio razonable: {n(f['entrada_mejor'])} o menos." if f.get("entrada_mejor") else "."),
              "acompañan": "✅ Los números acompañan.", "dudosos": "⚠️ Ojo: " + "; ".join(f["alertas"]) + ".",
              "en contra": "❌ Los números no acompañan: " + "; ".join(f["alertas"]) + "."}[f["veredicto"]])
    return " ".join(p)
