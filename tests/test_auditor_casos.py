"""El auditor se examina con cada caso real de config/auditor_casos.yaml: los que estaban mal no pueden salir,
y los que eran correctos no se pueden bloquear."""
import math
from datetime import date, timedelta

import pytest
import yaml

from mesa.agentes import proyeccion as P, seguimiento_cartera as S
from mesa.nucleo.config import RAIZ

CASOS = yaml.safe_load((RAIZ / "config" / "auditor_casos.yaml").read_text(encoding="utf-8"))


def _velas(hasta: date, compra: float, fecha_compra: str, maximo_previo: float | None):
    out, d, p = [], hasta - timedelta(days=380), compra * 0.85
    while d < hasta:
        if d.weekday() < 5:
            p *= 1 + 0.0007 + 0.003 * math.sin(len(out) / 4)
            x = {"fecha": d.isoformat(), "cierre": p, "maximo": p * 1.005, "minimo": p * 0.995, "apertura": p, "volumen": 5000}
            out.append(x)
        d += timedelta(days=1)
    # el tramo desde la compra: sube hasta el máximo previo y vuelve
    desde = [x for x in out if x["fecha"] > fecha_compra]
    if maximo_previo and len(desde) >= 2:
        desde[len(desde) // 2]["maximo"] = maximo_previo
    for x in desde:
        x["cierre"] = x["apertura"] = compra * 1.01
        x["maximo"] = max(x["maximo"], x["cierre"]); x["minimo"] = x["cierre"] * 0.99
    return out


@pytest.mark.parametrize("c", CASOS, ids=[c["caso"][:60] for c in CASOS])
def test_auditor_caso_real(c):
    hoy = date.fromisoformat(c["hoy"])
    velas = _velas(hoy, c["compra"], c["fecha_compra"], c.get("maximo_previo"))
    pos = {"ticker": c["ticker"], "cantidad": 50, "precio": c["compra"], "fecha": c["fecha_compra"]}
    if c.get("stop"):
        pos["alertas"] = [{"tipo": "baja", "nivel": c["stop"], "moneda": "ARS", "nota": "stop del plan"}]
    t = {"ultimo": c["precio"], "grupo": "acciones", "variacion": 0.0, "maximo": c.get("maximo_dia") or c["precio"],
         "fecha": c.get("fecha_precio") or f"{c['hoy']}T{c['hora']}", "cierre_anterior": c.get("cierre_anterior") or c["precio"],
         "volumen": c.get("volumen", 10000)}
    tit = lambda tk: t
    pr = P.para_cartera([pos], tit, lambda tk: velas, {}, [], {}, {}, None, [], hora=c["hora"])
    _, av = S.armar([pos], pr, {}, [], [], {}, {}, hoy, c["hora"], [], {})
    dec = {c["ticker"]: {"fecha": c["hoy"], "accion": c["decision_hoy"]}} if c.get("decision_hoy") else {}
    ok, fuera = S.auditar(av, tit, hoy, c["hora"], dec)
    ok = [a for a in ok if "VEND" in str(a.get("ticker", "")).upper() + str(a.get("texto", "")).upper()]  # avisos de venta
    if c["esperado"] == "avisar":
        assert ok, f"{c['caso']}: el aviso era correcto y no salió ({fuera or 'no se generó'})"
    else:
        assert not ok, f"{c['caso']}: el aviso estaba mal y salió igual"
