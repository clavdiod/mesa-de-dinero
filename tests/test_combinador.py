import random
from datetime import date, timedelta

from mesa.nucleo import combinador


def test_aprende_una_combinacion_que_gana_y_se_activa():
    random.seed(3)
    registro, series, fechas = [], {}, {}
    d0 = date(2022, 1, 3)
    for k in range(40):
        tk = f"T{k}"
        precios = [100.0]
        for i in range(600):
            precios.append(precios[-1] * (1 + random.gauss(0, 0.01)))
        dias = [(d0 + timedelta(days=i)).isoformat() for i in range(601)]
        for i in range(0, 560, 7):
            ws = random.choice([0, 0.6])
            cr = random.choice([0, 0.5])
            ruido = random.random() < 0.3   # técnico + economista muy convencidos... y pierden
            if ws:
                registro.append((tk, dias[i], "wallstreet", ws))
            if cr:
                registro.append((tk, dias[i], "cripto", cr))
            if ruido:
                registro.append((tk, dias[i], "tecnico", 0.9))
                registro.append((tk, dias[i], "economista", 0.9))
                for j in range(i + 1, i + 21):
                    precios[j] = precios[j - 1] * 0.998
            elif ws and cr:  # la combinación gana: el precio sube 5% en las 20 ruedas siguientes
                for j in range(i + 1, i + 21):
                    precios[j] = precios[j - 1] * 1.0025
        series[tk], fechas[tk] = precios, {f: n for n, f in enumerate(dias)}
    datos = combinador.armar_datos(registro, series, fechas, lambda f: {})
    m = combinador.entrenar(datos)
    assert m["activo"] and m["prueba"]["modelo"]["prom"] > m["prueba"]["suma_votos"]["prom"]
    p_combo = combinador.probabilidad(m, {"wallstreet": 0.6, "cripto": 0.5}, {})
    p_solo = combinador.probabilidad(m, {"wallstreet": 0.6}, {})
    assert p_combo > p_solo


def test_con_pocos_casos_no_se_activa():
    assert combinador.entrenar([])["activo"] is False
