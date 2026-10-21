from datetime import date, timedelta

from mesa.agentes import wallstreet


def _serie(n, f):
    d0 = date(2022, 1, 3)
    return [[(d0 + timedelta(days=i)).isoformat(), round(f(i), 4)] for i in range(n)]


def test_clima_y_senales_de_tendencia_y_momentum():
    idx = {"SPY": _serie(400, lambda i: 400 + i * 0.5), "^VIX": _serie(400, lambda i: 14.0), "^TNX": _serie(400, lambda i: 4.0)}
    precios = {f"T{k}": _serie(400, lambda i, k=k: 100 * (1 + (k - 5) / 1000) ** i) for k in range(12)}
    fecha = idx["SPY"][-1][0]
    cl = wallstreet.clima(idx, fecha)
    assert cl["riesgo"] >= 0.5 and "alcista" in cl["clase"][0]
    s = {x.ticker: x.direccion for x in wallstreet.senales_en(precios, cl, fecha)}
    assert s.get("T11") == 1 and s.get("T0") == -1


def test_entrenar_mide_y_no_mira_el_futuro():
    idx = {"SPY": _serie(500, lambda i: 400 + i * 0.5), "^VIX": _serie(500, lambda i: 18.0), "^TNX": _serie(500, lambda i: 4.0)}
    precios = {f"T{k}": _serie(500, lambda i, k=k: 100 * (1 + (k - 5) / 1000) ** i) for k in range(12)}
    r = wallstreet.entrenar({"indices": idx, "precios": precios})
    assert r["wallstreet"]["total"]["casos"] > 0 and r["ensenanza"]["clima_comprador"]["casos"] > 0


def test_ensenanza_contraria_si_el_miedo_rinde_mas():
    ens = {"clima_comprador": {"casos": 5000, "suma_ret": 5000.0}, "clima_defensivo": {"casos": 900, "suma_ret": 3300.0}}
    modo, _ = wallstreet.ensenanza_activa(ens)
    assert modo == "contrario"
    cl = {"riesgo": -0.5, "ensenanza_activa": modo}
    assert wallstreet.multiplicador(cl, "cedears", 1) == 1.1 and wallstreet.multiplicador(cl, "acciones", 1) == 1.0
