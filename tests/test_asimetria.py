from datetime import date
from mesa.agentes import asimetria as asi
from mesa.datos.eventos import flujos_bonos


def test_ao28_como_la_tabla():
    fl = flujos_bonos()["AO28"]["flujos"]
    r = asi.analizar("AO28", 80.4, fl, date(2026, 10, 29))  # la tabla de Tealdi: paridad 80,4%
    assert abs(r["escenarios"]["pesimista"] - (-49.0)) < 1.5 and abs(r["escenarios"]["optimista"] - 19.3) < 1.5
    assert r["cobras_hasta_salida"] == 6.0 and r["residual_salida"] == 100


def test_ao27_vence_antes():
    fl = flujos_bonos()["AO27"]["flujos"]
    r = asi.analizar("AO27", 102.4, fl, date(2026, 11, 12))
    assert r["residual_salida"] == 0 and "pase lo que pase" in r["lectura"]


def test_mas_barato_mas_asimetrico():
    fl = flujos_bonos()["AO29"]["flujos"]
    caro, barato = asi.analizar("AO29", 77, fl, date(2026, 11, 12)), asi.analizar("AO29", 50, fl, date(2026, 11, 12))
    assert barato["ratio"] > caro["ratio"]
