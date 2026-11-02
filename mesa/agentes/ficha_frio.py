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


def ficha(velas: list[dict], precio: float, plan: dict, estructura: dict | None, votos: list[dict]) -> dict | None:
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
    if pct1 >= 80:
        caro.append(f"la entrada está en el {100 - pct1:.0f}% más alto de los precios del último año")
    if obj and obj > mx1 * 1.02:
        out["objetivo_irreal"] = True
        malas.append(f"el objetivo ({obj:,.0f}) está arriba del máximo del último año ({mx1:,.0f})".replace(",", "."))
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
    if f.get("contra"):
        p.append("En contra: " + ", ".join(f["contra"]) + ".")
    p.append({"cara": "❌ Entrada cara: " + "; ".join(f.get("entrada_cara") or []) + (f". Precio razonable: {n(f['entrada_mejor'])} o menos." if f.get("entrada_mejor") else "."),
              "acompañan": "✅ Los números acompañan.", "dudosos": "⚠️ Ojo: " + "; ".join(f["alertas"]) + ".",
              "en contra": "❌ Los números no acompañan: " + "; ".join(f["alertas"]) + "."}[f["veredicto"]])
    return " ".join(p)
