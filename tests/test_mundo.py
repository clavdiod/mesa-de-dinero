from mesa.agentes import mundo


def n(t, f="reuters.com"):
    return {"titulo": t, "resumen": "", "link": "x", "fuente": f}


def test_temas_golfo_y_petroleo():
    tit = [n("Iran fires missiles at tanker in Strait of Hormuz"), n("Escalada en Medio Oriente: ataque con drones en el Golfo Pérsico", "ambito.com"),
           n("Oil prices jump as Middle East tension rises"), n("Apple lanza nuevo iPhone")]
    temas = mundo.detectar_temas(tit)
    claves = [t["tema"] for t in temas]
    assert claves[0] == "tension_golfo" and "petroleo_sube" not in claves
    existe = lambda tk: tk in {"YPFD", "VIST", "XOM", "GLD", "SPY"}
    s = {x.ticker: x for x in mundo.senales(temas, [], existe)}
    assert s["YPFD"].direccion == 1 and s["GLD"].direccion == 1 and s["SPY"].direccion == -1 and "NOC" not in s


def test_un_solo_titular_chico_no_alcanza():
    assert mundo.detectar_temas([n("La OPEP recorta producción", "blogcualquiera.com")]) == []
    assert mundo.detectar_temas([n("La OPEP recorta producción", "reuters.com")])[0]["tema"] == "opep_recorta"


def test_empresas_rumor_y_hecho():
    cl = mundo.claves_empresas({"GGAL": {"nombre": "Grupo Financiero Galicia", "clave": "Galicia"}, "AL30": {"nombre": "Bonar", "sector": "soberanos"}})
    emp = mundo.detectar_empresas([n("Trascendió que Galicia cierra sucursales en el interior"), n("Nvidia announces breakthrough chip, record revenue"),
                                   n("Galicia y el clima del fin de semana")], cl)
    e = {x["ticker"]: x for x in emp}
    assert e["GGAL"]["dir"] < 0 and e["GGAL"]["rumor"] and e["NVDA"]["dir"] > 0 and not e["NVDA"]["rumor"]
    s = {x.ticker: x for x in mundo.senales([], emp, lambda tk: True)}
    assert s["GGAL"].fuerza < s["NVDA"].fuerza


def test_aprende_y_silencia():
    stats = {"tension_golfo": {"casos": 12, "aciertos": 3, "suma_ret": -10}}
    assert mundo.factor_tema(stats, "tension_golfo") == 0.0
    log = []
    sen = mundo.senales([{"tema": "fmi", "nombre": "FMI", "explica": "", "efectos": {"AL30": 1}, "n": 3, "fuerza": 0.4, "titulares": [{"titulo": "x"}]}], [], lambda t: True)
    assert mundo.anotar(log, sen, lambda tk: 100.0, "2026-10-01") and not mundo.anotar(log, sen, lambda tk: 100.0, "2026-10-01")
    quedan, st = mundo.evaluar(log, {}, lambda tk: 103.0, "2026-10-09")
    assert quedan == [] and st["fmi"]["aciertos"] == 1
