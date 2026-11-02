"""36. Datos para dibujar el gráfico de cada papel de tu cartera, como los análisis técnicos: velas de un año,
máximo y mínimo del año, soportes (pisos donde rebotó), resistencias (techos), línea bajista o alcista, y tu plan
(compra, alarma de venta, objetivo). Lo dibuja la app (velas + líneas)."""
from __future__ import annotations


def _pivotes(c: list[float], n: int = 5):
    hi = [i for i in range(n, len(c) - n) if c[i] == max(c[i - n:i + n + 1])]
    lo = [i for i in range(n, len(c) - n) if c[i] == min(c[i - n:i + n + 1])]
    return hi, lo


def _niveles(vals: list[float], precio: float, abajo: bool, tol: float = 0.025) -> list[dict]:
    """Agrupa pivotes cercanos (±2,5%) en niveles y cuenta cuántas veces tocó cada uno."""
    xs = sorted(v for v in vals if (v < precio if abajo else v > precio))
    grupos: list[list[float]] = []
    for v in xs:
        if grupos and abs(v / grupos[-1][-1] - 1) <= tol:
            grupos[-1].append(v)
        else:
            grupos.append([v])
    out = [{"nivel": round(sum(g) / len(g), 2), "toques": len(g)} for g in grupos]
    out.sort(key=lambda d: abs(d["nivel"] / precio - 1))
    return out[:3]


def armar(velas: list[dict], precio: float, pos: dict | None = None, seg: dict | None = None) -> dict | None:
    v = [x for x in velas[-250:] if x.get("cierre")]
    if len(v) < 40:
        return None
    c = [x["cierre"] for x in v]
    hi, lo = _pivotes(c)
    out = {
        "velas": [[x["fecha"], round(x.get("apertura") or x["cierre"], 2), round(x.get("maximo") or x["cierre"], 2),
                   round(x.get("minimo") or x["cierre"], 2), round(x["cierre"], 2)] for x in v],
        "max_1a": round(max(x.get("maximo") or x["cierre"] for x in v), 2),
        "min_1a": round(min(x.get("minimo") or x["cierre"] for x in v), 2),
        "soportes": _niveles([c[i] for i in lo], precio, True),
        "resistencias": _niveles([c[i] for i in hi], precio, False),
    }
    # línea de tendencia: los dos últimos máximos (bajista) o los dos últimos mínimos (alcista)
    if len(hi) >= 2 and c[hi[-1]] < c[hi[-2]]:
        out["linea"] = {"tipo": "bajista", "p1": [v[hi[-2]]["fecha"], round(c[hi[-2]], 2)], "p2": [v[hi[-1]]["fecha"], round(c[hi[-1]], 2)]}
    elif len(lo) >= 2 and c[lo[-1]] > c[lo[-2]]:
        out["linea"] = {"tipo": "alcista", "p1": [v[lo[-2]]["fecha"], round(c[lo[-2]], 2)], "p2": [v[lo[-1]]["fecha"], round(c[lo[-1]], 2)]}
    if pos:
        out["compra"] = float(pos.get("precio") or 0) or None
        out["fecha_compra"] = pos.get("fecha")
    if seg:
        out["objetivo"] = seg.get("objetivo")
        out["alarma"] = next((o.get("nivel") for o in seg.get("opciones") or [] if o.get("accion") == "subir_stop"), None) or seg.get("piso")
    return out
