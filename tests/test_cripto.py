from datetime import date, timedelta

from mesa.agentes import cripto
from mesa.nucleo.contexto import Contexto
from mesa.nucleo.modelos import Senal


def _serie(n, f):
    d0 = date(2022, 1, 1)
    return [[(d0 + timedelta(days=i)).isoformat(), f(i)] for i in range(n)]


def test_btc_alcista_opina_en_cedears_cripto_y_aprende_del_mejor():
    btc = cripto.lectura_btc(_serie(300, lambda i: 30000 + i * 100), "2022-12-31")
    assert btc["estado"] == "alcista"
    ctx = Contexto(date(2026, 10, 21), "12:00", {"cedears": [{"simbolo": "IBIT", "ultimo": 100}, {"simbolo": "MSTR", "ultimo": 100}]})
    otras = {"MSTR": [Senal("wallstreet", "MSTR", -1, 0.6, "bajista")]}
    s = {x.ticker: x for x in cripto.senales_en(btc, None, ctx, ["IBIT", "MSTR"], {}, otras, "wallstreet")}
    assert s["IBIT"].direccion == 1 and s["IBIT"].fuerza == 0.5
    assert s["MSTR"].fuerza == 0.25 and "opina distinto" in s["MSTR"].texto


def test_brecha_cripto_solo_se_usa_si_la_historia_la_valida():
    ctx = Contexto(date(2026, 10, 21), "12:00", {"cedears": [{"simbolo": "AAPL", "ultimo": 100}]})
    assert cripto.senales_en(None, 2.0, ctx, ["AAPL"], {}) == []
    s = cripto.senales_en(None, 2.0, ctx, ["AAPL"], {"brecha": {"sirve": True}})
    assert s and s[0].direccion == 1


def test_entrenar_devuelve_veredictos():
    btc = _serie(700, lambda i: 30000 * (1.002 ** i))
    precios = {"IBIT": _serie(700, lambda i: 30 * (1.002 ** i)), "AAPL": _serie(700, lambda i: 150 + i * 0.1)}
    ccl = {d: 1000 + k for k, (d, _) in enumerate(_serie(700, lambda i: 0))}
    cr = {d: v * 1.02 for d, v in ccl.items()}
    r = cripto.entrenar(btc, precios, cr, ccl)
    assert r["cripto"]["total"]["casos"] > 0 and "veredicto" in r["ensenanza"]["btc"]
