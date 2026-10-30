"""34. Estructura del gráfico (el análisis clásico de tendencia): máximos y mínimos, promedio de 20 ruedas, línea bajista
y soporte. Se muestra como lectura para evaluar cada papel; NO vota sola.

Probado el 30/10 (10 años de acciones argentinas en dólares y 5 de CEDEARs, 20 ruedas): en general, un papel
"cayendo" (máximos y mínimos descendentes y debajo de un promedio que baja) NO rindió peor que el resto (acciones +2,1%
contra +1,2% de todos; CEDEARs +3,1% contra +1,7%: muchas veces rebota). Donde sí sirvió es en un susto argentino:
esperar a que el líder deje de caer rindió +4,3% contra +1,6% de comprar en plena caída. Por eso esa regla está en
el Comprador de pánico, y acá queda como lectura.
"""
from __future__ import annotations

import statistics as st


def _pivotes(c: list[float], n: int = 5) -> tuple[list[int], list[int]]:
    hi = [i for i in range(n, len(c) - n) if c[i] == max(c[i - n:i + n + 1])]
    lo = [i for i in range(n, len(c) - n) if c[i] == min(c[i - n:i + n + 1])]
    return hi, lo


def leer(velas: list[dict], precio: float | None = None) -> dict | None:
    c = [v["cierre"] for v in velas[-130:] if v.get("cierre")]
    if precio:
        c = c + [float(precio)]
    if len(c) < 40:
        return None
    hi, lo = _pivotes(c)
    hi, lo = [h for h in hi if h < len(c) - 5], [l for l in lo if l < len(c) - 5]
    m20, ant = st.mean(c[-20:]), st.mean(c[-25:-5])
    baj = len(hi) >= 2 and len(lo) >= 2 and c[hi[-1]] < c[hi[-2]] and c[lo[-1]] < c[lo[-2]]
    alc = len(hi) >= 2 and len(lo) >= 2 and c[hi[-1]] > c[hi[-2]] and c[lo[-1]] > c[lo[-2]]
    p = c[-1]
    if baj and p < m20 and m20 < ant:
        est, txt = "cayendo", "máximos y mínimos cada vez más bajos y debajo de su promedio de 20 ruedas, que baja"
    elif p > m20 and m20 >= ant:
        est, txt = ("alcista", "máximos y mínimos cada vez más altos, arriba de su promedio de 20 ruedas") if alc else \
                   ("confirmado", "dejó de caer: arriba de su promedio de 20 ruedas, que dejó de bajar")
    else:
        est, txt = "lateral", "sin tendencia clara"
    out = {"estado": est, "texto": txt, "promedio20": round(m20, 2), "vs_promedio_pct": round((p / m20 - 1) * 100, 1)}
    # línea bajista: une los dos últimos máximos descendentes, proyectada a hoy (si el precio la cruza, rompe la baja)
    if baj:
        i1, i2 = hi[-2], hi[-1]
        pend = (c[i2] - c[i1]) / (i2 - i1)
        out["linea_bajista"] = round(c[i2] + pend * (len(c) - 1 - i2), 2)
        out["rompe_linea"] = p > out["linea_bajista"]
    # soporte: el mínimo más bajo de los pivotes debajo del precio (donde rebotó antes)
    abajo = sorted((c[l] for l in lo if c[l] < p), reverse=True)
    if abajo:
        out["soporte"] = round(abajo[0], 2)
        out["a_soporte_pct"] = round((abajo[0] / p - 1) * 100, 1)
    return out


def frase(e: dict | None) -> str:
    if not e:
        return ""
    t = {"cayendo": "📉 Cayendo", "confirmado": "✅ Dejó de caer", "alcista": "📈 Alcista", "lateral": "↔️ Lateral"}[e["estado"]] + ": " + e["texto"]
    if e.get("linea_bajista"):
        t += f". Línea bajista en {e['linea_bajista']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + (" (ya la rompió)" if e.get("rompe_linea") else " (si la supera, se corta la baja)")
    if e.get("soporte"):
        t += f". Soporte en {e['soporte']:,.2f} ({e['a_soporte_pct']:+.1f}%)".replace(",", "X").replace(".", ",").replace("X", ".")
    return t + "."
