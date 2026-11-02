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
    malas = []
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
    out["veredicto"] = "acompañan" if not malas else "dudosos" if len(malas) == 1 else "en contra"
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
    if f.get("contra"):
        p.append("En contra: " + ", ".join(f["contra"]) + ".")
    p.append({"acompañan": "✅ Los números acompañan.", "dudosos": "⚠️ Ojo: " + "; ".join(f["alertas"]) + ".",
              "en contra": "❌ Los números no acompañan: " + "; ".join(f["alertas"]) + "."}[f["veredicto"]])
    return " ".join(p)
