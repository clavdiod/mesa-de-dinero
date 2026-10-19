from datetime import date

import pytest

from mesa.nucleo import calc
from mesa.nucleo.modelos import Plan
from tests.conftest import serie


def test_rsi_extremos():
    assert calc.rsi(list(range(1, 30))) == 100.0
    assert calc.rsi(list(range(30, 1, -1))) == pytest.approx(0.0)


def test_tir_bono_a_la_par():
    # bono a 1 año que paga 8 de interés + 100 de capital, comprado a 100 → TIR 8%
    hoy = date(2026, 1, 1)
    flujo = [{"fecha": "2027-01-01", "total": 108}]
    assert calc.tir(100, flujo, hoy) == pytest.approx(8.0, abs=0.01)


def test_simulador_ejemplo_del_chat():
    # ON inventada del chat: 8% anual semestral, 2 años, comprada a 102 con US$1.000
    on = {"lamina_minima": 1, "flujos": [
        {"fecha": "2027-04-19", "interes": 4, "amortizacion": 0},
        {"fecha": "2027-10-19", "interes": 4, "amortizacion": 0},
        {"fecha": "2028-04-19", "interes": 4, "amortizacion": 0},
        {"fecha": "2028-10-19", "interes": 4, "amortizacion": 100}]}
    r = calc.simular_on(on, 102, date(2026, 10, 19), capital=1000)
    assert r["nominales"] == 980
    assert [f["total"] for f in r["flujo"]] == [39.2, 39.2, 39.2, 1019.2]
    assert r["total_cobrar"] == pytest.approx(1136.8)
    assert r["costo"] == pytest.approx(999.6)


def test_plan_r_como_en_la_sesion():
    # CRES de la sesión del 19/10: entrada 1825, stop 1770, objetivo 1960 → 2,45R bruto
    p = Plan("CRES", "compra", 1825, 1770, 1960)
    assert p.r_bruto == pytest.approx(2.4545, abs=1e-3)
    assert p.riesgo_pct == pytest.approx(3.01, abs=0.01)
    assert p.recompensa_pct == pytest.approx(7.40, abs=0.01)
    assert p.r_neto(1.2) < p.r_bruto


def test_patrones_sin_mirar_el_futuro():
    c = [v["cierre"] for v in serie(300)]
    r = calc.patrones_parecidos(c, 20, 0.8, (5, 10))
    assert r["casos"] >= 1
    assert set(r["horizontes"]) <= {5, 10}


def test_soporte_y_resistencia():
    v = serie(200, semilla=3)
    precio = v[-1]["cierre"]
    s = calc.soporte_cercano(v, precio)
    r = calc.resistencia_cercana(v, precio)
    assert s is None or s["nivel"] <= precio * 1.005
    assert r is None or r["nivel"] >= precio * 1.01
