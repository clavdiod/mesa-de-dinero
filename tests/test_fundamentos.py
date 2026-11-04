from mesa.agentes import fundamentos as fu
from mesa.agentes import ficha_frio as ff


def test_frase_y_sin_voto():
    f = {"eps_12m": 6.0, "pe": 30.0, "crec": 0.10, "peg": 3.0, "fcf_rinde": 3.2, "ciclica": False}
    t = fu.frase(f)
    assert "P/E 30" in t and "cara para lo que crece" in t and "sin voto" in t
    assert fu.frase(None) == ""
    velas = [{"fecha": f"2026-{1 + i // 28:02d}-{1 + i % 28:02d}", "o": 100 + i * 0.1, "h": 101 + i * 0.1, "l": 99 + i * 0.1, "c": 100 + i * 0.1, "v": 1000} for i in range(260)]
    plan = {"entrada": 126, "stop": 118, "objetivo": 135}
    sin = ff.ficha(velas, 126, plan, None, [], "cedears")
    con = ff.ficha(velas, 126, plan, None, [], "cedears", fundamentos=f)
    assert con["veredicto"] == sin["veredicto"] and con["alertas"] == sin["alertas"]  # no vota
    assert "Fundamentos" in ff.texto(con)
    assert "fundamentos" not in (ff.ficha(velas, 126, plan, None, [], "acciones", fundamentos=f) or {}) or not ff.ficha(velas, 126, plan, None, [], "acciones", fundamentos=f).get("fundamentos")
