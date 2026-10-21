from datetime import date

from mesa.agentes import mae
from mesa.datos.gratis import ticker_mae_a_byma


def test_tickers():
    assert ticker_mae_a_byma("AL30", "$") == "AL30"
    assert ticker_mae_a_byma("AL30", "D") == "AL30D"
    assert ticker_mae_a_byma("YM44O", "D", {"YM44D"}) == "YM44D"
    assert ticker_mae_a_byma("YM44O", "C", {"YM44C"}) == "YM44C"


def test_comparar_y_alertas():
    tit = {"AL30": {"ultimo": 85360, "grupo": "soberanos", "volumen": 1}, "AE38D": {"ultimo": 73.0, "grupo": "soberanos", "volumen": 1},
           "GGAL": {"ultimo": 6000, "grupo": "acciones", "volumen": 1}}
    rows = [{"ticker": "AL30", "moneda": "$", "plazo": "001", "ultimo": 855.75, "monto": 3e9},
            {"ticker": "AL30", "moneda": "$", "plazo": "000", "ultimo": 859.0, "monto": 1e9},
            {"ticker": "AE38", "moneda": "D", "plazo": "000", "ultimo": 0.75, "monto": 3_200_000},
            {"ticker": "GGAL", "moneda": "$", "plazo": "000", "ultimo": 58.45, "monto": 1e9}]
    pares = mae.comparar(tit, rows)
    al = next(p for p in pares if p["ticker"] == "AL30")
    assert al["plazo_mae"] == "24 h" and abs(al["dif"] - 0.25) < 0.01   # se elige la de 24 h
    ae = next(p for p in pares if p["ticker"] == "AE38D")
    assert abs(ae["mae"] - 75.0) < 1e-9 and ae["dif"] > 2.7          # escala x100 para dólares
    assert not any(p["ticker"] == "GGAL" for p in pares)               # solo renta fija
    al_ = mae.alertas(pares)
    assert [a["ticker"] for a in al_] == ["AE38D"] and "más barato en BYMA" in al_[0]["texto"]
    assert mae.resumen(pares)["soberanos"]["n"] == 2


def test_historico_y_velas():
    class A(dict):
        def put(self, k, v): self[k] = v
    a = A()
    rows = [{"fecha": "2026-10-20T00:00:00", "codTitulo": "AL30", "moneda": "$", "plazo": "001", "precioCierre": 850, "volumen": 10, "precioMaximo": 855, "precioMinimo": 840},
            {"fecha": "2026-10-21T00:00:00", "codTitulo": "AL30", "moneda": "D", "plazo": "001", "precioCierre": 0.55, "volumen": 10}]
    assert mae.guardar_historico(a, rows) == 2
    rows.append({"fecha": "2026-10-20T00:00:00", "codTitulo": "AL30", "moneda": "$", "plazo": "001", "precioCierre": 700, "volumen": 1e12, "codsegmento": "RT"})
    mae.guardar_historico(a, rows)
    assert a["mae/hist/2026"]["AL30"]["2026-10-20"][0] == 85000   # el pase (RT) no pisa el precio de mercado
    assert a["mae/hist/2026"]["AL30D"]["2026-10-21"][0] == 55.0
    v = mae.historico(a, "AL30", ["2026"])
    assert v[0]["cierre"] == 85000 and v[0]["maximo"] == 85500


def test_pagos_y_avisos():
    docs = [{"fecha": "2026-10-21T03:00:00Z", "empresa": "GENERACION MEDITERRANEA S.A.", "titulo": "GEMSA-ON-Clase 15-pago 28-10-26.pdf", "url": "u"},
            {"fecha": "2026-10-21T03:00:00Z", "empresa": "X S.A.", "titulo": "X-ON-pago 01-10-26.pdf", "url": "u"}]
    ev = mae.pagos(docs, date(2026, 10, 21), ["Generación Mediterránea"])
    assert len(ev) == 1 and ev[0]["fecha"] == "2026-10-28" and ev[0]["mio"] and "GEMSA ON Clase 15" in ev[0]["nombre"]
    b = [{"fecha": "2026-10-19T03:00:00Z", "titulo": "MP A3-RES-ON LOMA NEGRA Clase 7 - Aviso de Resultados 19-10-2026.pdf", "url": "r"},
         {"fecha": "2026-10-20T03:00:00Z", "titulo": "MPA3-ANU-ON BI PYME GAR COLGAS CLASE I-Aviso de Colocacion 20-10-26.pdf", "url": "c"},
         {"fecha": "2026-10-20T03:00:00Z", "titulo": "MPA3-ANU-ON BI PYME GAR COLGAS CLASE I-Prospecto 22-06-26.pdf", "url": "p"}]
    av = mae.avisos_licitacion(b, date(2026, 10, 21))
    assert av["resultados"][0]["titulo"].startswith("ON LOMA NEGRA") and len(av["anuncios"]) == 1
