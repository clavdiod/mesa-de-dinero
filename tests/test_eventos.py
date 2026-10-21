from datetime import date

from mesa.datos import eventos


def test_bonares_pagan_como_globales_y_se_corre_al_lunes():
    f = eventos.flujos_bonos()
    assert f["AL30"]["flujos"] == f["GD30"]["flujos"] and "AL30D" in f
    ev = eventos.cobros(date(2026, 12, 20), 30, {}, {"AL30"})
    pagos = [e for e in ev if e["ticker"] == "AL30"]
    # el 09/01/2027 es sábado: se cobra el lunes 11
    assert pagos and pagos[0]["fecha"] == "2027-01-11" and pagos[0]["monto_c100"] == 8.345
    assert any(e["ticker"] == "AL/GD" for e in ev)


def test_on_del_usuario_entra_en_el_calendario():
    ons = {"PN35D": {"flujos": [{"fecha": "2026-12-15", "interes": 4.0, "amortizacion": 0}]}}
    ev = eventos.cobros(date(2026, 12, 1), 30, ons, {"PN35D"})
    assert [e["fecha"] for e in ev if e["ticker"] == "PN35D"] == ["2026-12-15"]


def test_flujos_suman_100_de_amortizacion():
    for tk in ("GD29", "GD35", "GD38", "GD41", "GD46"):
        total = sum(x["amortizacion"] for x in eventos.flujos_bonos()[tk]["flujos"])
        assert total <= 100.01, tk
