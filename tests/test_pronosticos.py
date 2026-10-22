from datetime import date

from mesa.nucleo import pronosticos as pr


def test_ciclo_completo():
    lib = []
    lista = {"fecha": "2026-10-21", "lista": [{"ticker": "IREN", "prob": 0.95, "razones": ["sobrevendido"]}]}
    assert pr.anotar(lib, pr.desde_anticipador(lista, date(2026, 10, 21), "20:10")[0])
    assert not pr.anotar(lib, pr.desde_anticipador(lista, date(2026, 10, 22), "11:00")[0])  # no duplica
    x = lib[0]
    assert x["estado"] == "esperando"
    pr.actualizar(lib, {"IREN": {"ultimo": 100}}, date(2026, 10, 22), byma_abierto=True)
    assert x["estado"] == "en_curso" and x["ref"] == 100
    pr.actualizar(lib, {"IREN": {"ultimo": 103, "maximo": 106, "minimo": 99}}, date(2026, 10, 23), True)
    assert x["estado"] == "se_dio" and x["mejor"] == 6.0


def test_anticipo_y_stop():
    lib = []
    pr.anotar(lib, pr.desde_anticipos([{"ticker": "MSTR", "atraso": -4.0, "us": -5, "antes_de_abrir": False, "precio_cedear": 50}], date(2026, 10, 22), "11:10")[0])
    pr.actualizar(lib, {"MSTR": {"ultimo": 49.5}}, date(2026, 10, 22), True)
    assert lib[0]["estado"] == "en_curso" and lib[0]["ahora_pct"] == 1.0
    assert pr.cerrar_dia(lib, date(2026, 10, 22)) and lib[0]["estado"] == "no_se_dio"
    p = pr.desde_plan("jefe", "GGAL", {"entrada": 100, "objetivo": 110, "stop": 95}, date(2026, 10, 22), "12:00", "x")
    pr.anotar(lib, p)
    pr.actualizar(lib, {"GGAL": {"ultimo": 96, "minimo": 94}}, date(2026, 10, 23), True)
    assert lib[0]["estado"] == "fallo"
    r = pr.resumen(lib)
    assert r["jefe"]["fallo"] == 1 and r["anticipo"]["cerrados"] == 1
