import math
import random
from datetime import date, timedelta

from mesa.agentes import anticipo
from mesa.nucleo.contexto import Contexto


def test_cedear_atrasado_antes_de_abrir():
    ctx = Contexto(date(2026, 10, 21), "10:40", {"cedears": [{"simbolo": "MSTR", "ultimo": 20000, "variacion": 0.0}]})
    vivo = {"MSTR": {"precio": 155.13, "anterior": 142.72}}
    a = anticipo.atrasos(ctx, vivo, 1632.0, 1630.0, 10 * 60 + 40)
    assert a and a[0]["antes_de_abrir"] and 8.5 < a[0]["atraso"] < 9.2 and a[0]["severidad"] == "alta"
    s = anticipo.senales_atraso(a)
    assert s[0].direccion == 1 and "Antes de que abra BYMA" in s[0].texto


def test_si_el_cedear_ya_se_acomodo_no_avisa():
    ctx = Contexto(date(2026, 10, 21), "12:00", {"cedears": [{"simbolo": "MSTR", "ultimo": 21700, "variacion": 8.5}]})
    assert anticipo.atrasos(ctx, {"MSTR": {"precio": 155.13, "anterior": 142.72}}, 1632.0, 1630.0, 12 * 60) == []


def test_modelo_aprende_precursor_y_mide_contra_azar():
    random.seed(7)
    d0 = date(2022, 1, 3)
    series = {}
    for k in range(30):
        f, p = [], 100.0
        acumula = 0
        for i in range(500):
            v = 1000.0
            if acumula > 0:      # 3 días de volumen alto sin mover precio... y después sube
                v, acumula = 4000.0, acumula - 1
                if acumula == 0:
                    p *= 1.08
            elif random.random() < 0.03:
                acumula = 3
            p *= 1 + random.gauss(0, 0.008)
            f.append({"fecha": (d0 + timedelta(days=i)).isoformat(), "c": p, "h": p * 1.01, "l": p * 0.99, "v": v})
        series[f"T{k}"] = f
    m = anticipo.entrenar(series, {}, {}, {})
    assert m["prueba"]["top10_pct"] > m["prueba"]["base_pct"]
    lista = anticipo.puntuar(m, series, {})
    assert lista and 0 <= lista[0]["prob"] <= 1
