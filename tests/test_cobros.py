from datetime import date

from mesa.datos import cobros as c


def test_calculo_y_avisos():
    fuentes = {"AL30": {"moneda": "USD", "flujos": [{"fecha": "2026-10-23", "interes": 0.24, "amortizacion": 8}]},
               "TTD26": {"moneda": "ARS", "descripcion": "DUAL", "flujos": [{"fecha": "2026-12-15", "interes": 54.32, "amortizacion": 100}]}}
    cart = [{"ticker": "AL30", "cantidad": 1000}, {"ticker": "TTD26", "cantidad": 750000}, {"ticker": "S13N6", "cantidad": 100000}]
    cs = c.proximos(cart, fuentes, date(2026, 10, 22), 60) + c.vencimientos_lecap(cart, None, date(2026, 10, 22), 60)
    al = next(x for x in cs if x["ticker"] == "AL30")
    assert al["total"] == 82.4 and al["moneda"] == "USD"
    assert next(x for x in cs if x["ticker"] == "TTD26")["total"] == 1157400.0
    assert next(x for x in cs if x["ticker"] == "S13N6")["fecha"] == "2026-11-13"
    av = c.avisos(cs, date(2026, 10, 22))
    assert av[0]["cuando"] == "mañana" and "US$ 82,40 de AL30" in av[0]["texto"]


def test_candidatos():
    assert c.candidatos("YM34D") == ["YM34D", "YM34O", "YM34"]
    assert c.candidatos("al30d")[1:] == ["AL30O", "AL30"]
