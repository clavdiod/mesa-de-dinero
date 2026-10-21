from datetime import date, timedelta

from mesa.agentes import panico


def _serie(n, f):
    d0 = date(2022, 1, 3)
    return [[(d0 + timedelta(days=i)).isoformat(), f(i)] for i in range(n)]


def test_panico_en_wall_street_compra_indices():
    idx = {"SPY": _serie(300, lambda i: 500 if i < 280 else 440), "^VIX": _serie(300, lambda i: 35.0)}
    precios = {"SPY": idx["SPY"], "AAPL": _serie(300, lambda i: 100 + i * 0.2)}
    s = panico.senales_cedears(precios, idx, idx["SPY"][-1][0])
    assert any(x.ticker == "SPY" and x.datos["tipo"] == "indice" for x in s)


def test_capitulacion_de_cedear_sano():
    idx = {"SPY": _serie(300, lambda i: 500.0), "^VIX": _serie(300, lambda i: 15.0)}
    precios = {"NVDA": _serie(300, lambda i: 100 + i * 0.5 if i < 290 else (100 + 290 * 0.5) * 0.8)}
    s = panico.senales_cedears(precios, idx, precios["NVDA"][-1][0])
    assert s and s[0].datos["tipo"] == "capitulacion_cedear"


def test_susto_argentino_y_entrenar():
    velas = {tk: [{"fecha": f, "cierre": 100.0 - (k % 3)} for k, (f, _) in enumerate(_serie(80, lambda i: 0))] for tk in panico.LIDERES_MERVAL}
    fechas = [v["fecha"] for v in velas["GGAL"]]
    rp = {f: (600.0 if k < 40 else 700.0) for k, f in enumerate(fechas)}
    s = panico.senales_locales(velas, rp, fechas[45])
    assert any(x.datos["tipo"] == "susto_argentino" for x in s)
    st = panico.entrenar({}, {"SPY": []}, velas, rp)
    assert st["por_tipo"].get("susto_argentino", {}).get("casos", 0) > 0
