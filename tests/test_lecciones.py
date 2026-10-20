"""Lecciones del 20/10 convertidas en pruebas, para que no se repitan."""
from mesa.agentes import analistas


class Ctx:
    def __init__(self, titulos):
        self.t, self.extra = titulos, {}

    def grupo(self, nombre):
        return self.t


def _par(s, pesos, usd, vol_c=1000):
    return [{"simbolo": s, "ultimo": pesos, "volumen": 500},
            {"simbolo": s + "C", "ultimo": usd, "volumen": vol_c}]


def test_cedear_con_linea_en_dolares_sin_operar_no_es_senal():
    t = []
    for i, s in enumerate(["AAPL", "MSFT", "KO", "XOM", "MELI", "GOOGL"]):
        t += _par(s, 1600 * (10 + i), 10 + i)        # todos con dólar implícito 1.600
    t += _par("CAR", 6490, 18.0, vol_c=0)           # dólar implícito 360: precio viejo en dólares
    out = analistas.cedears(Ctx(t))
    assert not any(s.ticker == "CAR" for s in out)


def test_desvio_imposible_se_descarta():
    t = []
    for i, s in enumerate(["AAPL", "MSFT", "KO", "XOM", "MELI", "GOOGL"]):
        t += _par(s, 1600 * (10 + i), 10 + i)
    t += _par("NG", 1100 * 40, 40)                  # 31% abajo: no es arbitraje, es un dato raro
    t += _par("PLD", 1540 * 5, 5)                   # 3,75% abajo: sí es señal
    out = {s.ticker for s in analistas.cedears(Ctx(t))}
    assert "NG" not in out and "PLD" in out
