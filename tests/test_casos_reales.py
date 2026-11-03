"""Casos reales que fallaron (28/10 al 03/11). Si alguno vuelve a fallar, la mesa no se publica."""
import math
from datetime import date, timedelta

from mesa.agentes import proyeccion as P, seguimiento_cartera as S


def _velas(desde: date, n: int, precio: float, paso: float = 0.0):
    out, d, p = [], desde, precio
    while len(out) < n:
        if d.weekday() < 5:
            p *= 1 + paso + 0.004 * math.sin(len(out) / 3)
            out.append({"fecha": d.isoformat(), "cierre": p, "maximo": p * 1.01, "minimo": p * 0.99, "apertura": p})
        d += timedelta(days=1)
    return out


def _correr(pos, precio, velas, hoy, hora, maximo=None, opinion=None, noticias=None, extra_titulo=None):
    t = {"ultimo": precio, "grupo": "acciones", "variacion": 0.5, "maximo": maximo or precio,
         "fecha": f"{hoy.isoformat()}T{hora}:00", "cierre_anterior": precio, "volumen": 10000, **(extra_titulo or {})}
    tit = lambda tk: t
    pr = P.para_cartera([pos], tit, lambda tk: velas, opinion or {}, [], {}, {}, None, [], hora=hora)
    out, av = S.armar([pos], pr, opinion or {}, [], [], {}, {}, hoy, hora, [], noticias or {})
    av, fuera = S.auditar(av, tit, hoy, hora, {})
    return out[pos["ticker"]], av, fuera


def test_tran_dia_de_compra_no_dice_vender():
    """28/10: TRAN tocó 2.300 a la mañana ANTES de la compra (2.158): no hay ganancia 'devuelta' el mismo día."""
    hoy = date(2026, 10, 28)
    v = _velas(date(2025, 11, 1), 250, 2000, 0.0005)
    g, av, _ = _correr({"ticker": "TRAN", "cantidad": 84, "precio": 2158, "fecha": hoy.isoformat()}, 2168, v, hoy, "15:10", maximo=2300)
    assert g["sugerida"] not in ("vender_todo", "vender_mitad") and not av


def test_antes_de_las_11_no_hay_alarmas():
    """03/11 10:30: IBB figuraba a 12.400 (precio viejo) y mandó 'VENDÉ TODO'."""
    hoy = date(2026, 11, 3)
    v = _velas(date(2025, 11, 1), 250, 11000, 0.0006)
    g, av, fuera = _correr({"ticker": "IBB", "cantidad": 10, "precio": 12700, "fecha": "2026-10-22"}, 12400, v, hoy, "10:30", maximo=13650)
    assert not av


def test_rozar_el_nivel_por_poco_no_dispara():
    """03/11 10:35: IBB tocó por $5 el nivel de 'asegurar la mitad' y rebotó."""
    hoy = date(2026, 11, 3)
    v = _velas(date(2025, 11, 1), 250, 11000, 0.0006)
    v[-3]["maximo"] = 13650
    g, av, _ = _correr({"ticker": "IBB", "cantidad": 10, "precio": 12700, "fecha": "2026-10-22"}, 13170, v, hoy, "11:10", maximo=13300)
    assert g["sugerida"] not in ("vender_todo", "vender_mitad")


def test_plan_largo_no_se_acorta_por_tema_general():
    """30/10: YPFD (plan de 20 ruedas) pasó a 'salir mañana' por un titular de la Fed."""
    hoy = date(2026, 10, 30)
    v = _velas(date(2025, 11, 1), 250, 7000, 0.0003)
    pos = {"ticker": "YPFD", "cantidad": 36, "precio": 8135, "fecha": "2026-10-29", "vence": "2026-11-26",
           "alertas": [{"tipo": "baja", "nivel": 7470, "moneda": "ARS", "nota": "stop del plan"}]}
    nots = {"YPFD": [{"dir": -1, "fuerza": 0.8, "texto": "La Reserva Federal sube tasas o se endurece", "agente": "mundo"}]}
    op = {"YPFD": {"veredicto": "en contra", "a_favor": [], "en_contra": ["Técnico", "Economista", "Corresponsal"]}}
    g, av, _ = _correr(pos, 7800, v, hoy, "15:00", opinion=op, noticias=nots)
    assert g["vence"] >= "2026-11-20"


def test_precio_viejo_se_descarta():
    hoy = date(2026, 11, 3)
    av = [{"ticker": "IBB (VENDER)", "texto": "🚨 IBB: VENDÉ"}]
    ok, fuera = S.auditar(av, lambda tk: {"fecha": "2026-11-02T16:59:00", "ultimo": 12400}, hoy, "11:30", {})
    assert not ok and "viejo" in fuera[0]


def test_decision_de_mantener_se_respeta():
    hoy = date(2026, 11, 3)
    av = [{"ticker": "TRAN (VENDER)", "texto": "🚨 TRAN: VENDÉ TODO"}]
    ok, fuera = S.auditar(av, lambda tk: {"fecha": f"{hoy.isoformat()}T11:20:00", "ultimo": 2180}, hoy, "11:25",
                          {"TRAN": {"fecha": hoy.isoformat(), "accion": "mantener"}})
    assert not ok
