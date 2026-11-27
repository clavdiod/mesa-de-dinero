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


def test_devolver_ganancia_lo_deciden_los_agentes():
    """26/11: PAMP llegó a +7,2% (4.600) y volvió a +3,1%: la mesa mandó 'VENDÉ LA MITAD'. Clau: que decidan los analistas."""
    hoy = date(2026, 11, 26)
    v = _velas(date(2025, 11, 1), 250, 4000, 0.0003)
    pos = {"ticker": "PAMP", "cantidad": 20, "precio": 4290, "fecha": "2026-11-24"}
    t = {"ultimo": 4423, "grupo": "acciones", "variacion": -1.0, "maximo": 4600, "fecha": f"{hoy.isoformat()}T11:00:00",
         "cierre_anterior": 4440, "volumen": 10000}
    pr = P.para_cartera([pos], lambda tk: t, lambda tk: v, {}, [], {}, {}, None, [], hora="11:00")
    pr["PAMP"]["max_desde_compra"] = 4600
    sigue = lambda *a: {"accion": "dejar_correr", "puntaje": 2, "a_favor": ["MACD positivo", "el gráfico es alcista"], "en_contra": []}
    cae = lambda *a: {"accion": "vender_todo", "puntaje": -2, "a_favor": [], "en_contra": ["el gráfico sigue cayendo", "MACD negativo"]}
    out, av = S.armar([pos], pr, {}, [], [], {}, {}, hoy, "11:00", [], {}, analizar_salida=sigue)
    assert out["PAMP"]["sugerida"] == "mantener" and not av
    out, av = S.armar([pos], pr, {}, [], [], {}, {}, hoy, "11:00", [], {}, analizar_salida=cae)
    assert out["PAMP"]["sugerida"] == "vender_todo" and "más motivos para que siga bajando" in av[0]["texto"]


def test_posicion_larga_no_vende_por_devolver_un_dia():
    """27/11: EDN (posición a 3 meses, comprada el 26/11 a 1.087) llegó a 1.152 y volvió a +1,4%: 'VENDÉ TODO AHORA'."""
    hoy = date(2026, 11, 27)
    v = _velas(date(2025, 11, 1), 250, 1000, 0.0003)
    pos = {"ticker": "EDN", "cantidad": 55, "precio": 1087, "fecha": "2026-11-26", "propuesta_id": "ee0",
           "alertas": [{"tipo": "baja", "nivel": 817.5, "moneda": "ARS", "nota": "Alarma de venta, stop del plan"}]}
    props = [{"id": "ee0", "ticker": "EDN", "linea": "posicion", "meses": 3, "decision": "pendiente",
              "plan": {"entrada": 1090, "stop": 817.5, "objetivo": 1362.5, "vence": "2027-02-24"}}]
    t = {"ultimo": 1102, "grupo": "acciones", "variacion": -1.0, "maximo": 1152, "fecha": f"{hoy.isoformat()}T14:10:00",
         "cierre_anterior": 1110, "volumen": 10000}
    pr = P.para_cartera([pos], lambda tk: t, lambda tk: v, {}, props, {}, {}, None, [], hora="14:10")
    pr["EDN"]["max_desde_compra"] = 1152
    out, av = S.armar([pos], pr, {}, props, [], {}, {}, hoy, "14:10", [], {})
    assert out["EDN"]["sugerida"] not in ("vender_todo", "vender_mitad") and not av


def test_posicion_larga_no_vende_la_mitad_porque_la_mesa_este_en_contra():
    """27/11 15:50: METR (posición a 3 meses, compra 1.668, hoy 1.865): 'VENDÉ LA MITAD: la mesa hoy está en contra'."""
    hoy = date(2026, 11, 27)
    v = _velas(date(2025, 11, 1), 250, 1700, 0.0003)
    pos = {"ticker": "METR", "cantidad": 44, "precio": 1668, "fecha": "2026-11-25", "propuesta_id": "513", "objetivo_idea": 2087.5,
           "alertas": [{"tipo": "baja", "nivel": 1252.5, "moneda": "ARS", "nota": "Alarma de venta, stop del plan"}]}
    props = [{"id": "513", "ticker": "METR", "linea": "posicion", "meses": 3, "decision": "pendiente",
              "plan": {"entrada": 1670, "stop": 1252.5, "objetivo": 2087.5, "vence": "2027-02-23"}}]
    t = {"ultimo": 1865, "grupo": "acciones", "variacion": 1.0, "maximo": 1880, "fecha": f"{hoy.isoformat()}T15:50:00",
         "cierre_anterior": 1846, "volumen": 10000}
    op = {"METR": {"veredicto": "en contra", "a_favor": [], "en_contra": ["Técnico", "Economista"]}}
    pr = P.para_cartera([pos], lambda tk: t, lambda tk: v, op, props, {}, {}, None, [], hora="15:50")
    assert pr["METR"]["consejo"] == "Tomar parte"
    nots = {"METR": [{"dir": -1, "fuerza": 0.5, "texto": "Titular en contra", "agente": "noticias"}]}
    out, av = S.armar([pos], pr, op, props, [], {}, {}, hoy, "15:50", [], nots)
    assert out["METR"]["sugerida"] not in ("vender_todo", "vender_mitad") and not any("VEND" in a["ticker"] for a in av)


def test_posicion_larga_el_balance_no_corta_el_plazo():
    """27/11: en una posición a 3 meses el balance del trimestre no puede terminar en 'se cumplió el plazo: vendé'."""
    from mesa.agentes.seguimiento_cartera import replantear_plazo
    hoy = date(2026, 11, 27)
    ev = [{"tipo": "balance", "ticker": "EDN", "fecha": "2026-12-03"}]
    v, mot = replantear_plazo("EDN", "2027-02-24", date(2026, 11, 26), hoy, {}, {}, ev, [])
    assert v == "2027-02-24" and not mot
    v, mot = replantear_plazo("EDN", "2026-12-15", date(2026, 11, 26), hoy, {}, {}, ev, [])  # idea corta: sí lo corta
    assert v < "2026-12-03" and "balance" in mot[0]
