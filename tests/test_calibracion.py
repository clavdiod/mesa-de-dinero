import math
import random

from mesa.nucleo import calibracion


def test_factor_castiga_al_que_promete_mas_de_lo_que_acierta():
    # dice "fuerte" (0,8) y acierta 52%: casi una moneda
    flojo = {"casos": 100, "aciertos": 52, "suma_ret": 20.0, "suma_fuerza": 80.0}
    # dice "media" (0,5) y acierta 66% con buena esperanza
    bueno = {"casos": 100, "aciertos": 66, "suma_ret": 150.0, "suma_fuerza": 50.0}
    perdedor = {"casos": 100, "aciertos": 60, "suma_ret": -30.0, "suma_fuerza": 60.0}
    assert calibracion.factor(flojo) == 0.3
    assert calibracion.factor(bueno) == 1.07
    # acierta 60% pero gana 0,5% promedio: no alcanza para pagar la comisión de 1,2%
    assert calibracion.factor({"casos": 100, "aciertos": 60, "suma_ret": 50.0, "suma_fuerza": 50.0}) == 0.3
    assert calibracion.factor(perdedor) == 0.3


def test_entrenar_con_historia_no_mira_el_futuro_y_devuelve_bandas():
    random.seed(1)
    series, grupos = {}, {}
    for k in range(10):
        p, vs = 100.0, []
        for i in range(320):
            p *= 1 + 0.002 * (k - 4) / 4 + random.gauss(0, 0.015) + 0.01 * math.sin(i / 9)
            vs.append({"fecha": f"2025-{1 + i // 28:02d}-{1 + i % 28:02d}", "cierre": p, "maximo": p * 1.01, "minimo": p * 0.99, "volumen": 1000})
        series[f"T{k}"], grupos[f"T{k}"] = vs, "acciones"
    st = calibracion.entrenar_con_historia(series, grupos, {})
    assert "tecnico" in st and st["tecnico"]["total"]["casos"] > 0
    assert set(st["tecnico"]["bandas"]) <= {"debil", "media", "fuerte"}
    cal = calibracion.calibrar({}, st)
    assert all(0.3 <= c["factor"] <= 1.5 for c in cal.values())
