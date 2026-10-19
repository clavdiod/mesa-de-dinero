from mesa.agentes import supervisor


def s(ag, d, f, t="x", veto=False):
    return {"agente": ag, "direccion": d, "fuerza": f, "texto": t, "veto": veto}


PLAN = {"entrada": 100.0, "stop": 95.0, "objetivo": 110.0}


def test_compra_cuando_riesgo_ok_y_puntaje_alto():
    op = supervisor.opinion([s("tecnico", 1, 0.8, "rebote")], 0.8, PLAN, {"ok": True, "r_neto": 1.5, "tamano_r": 1}, 101)
    assert op["veredicto"] == "comprar"


def test_veto_manda_evitar():
    op = supervisor.opinion([s("tecnico", 1, 0.9), s("hechos_emisor", -1, 1, "renunció el CEO", True)], 0.5, PLAN, None, 100)
    assert op["veredicto"] == "evitar"


def test_esperar_sugiere_precio_mas_bajo_si_no_paga_el_riesgo():
    riesgo = {"ok": False, "motivos": ["Relación neta 1.10R, menor al mínimo 1.3R."]}
    op = supervisor.opinion([s("tecnico", 1, 0.5)], 0.5, {**PLAN, "objetivo": 106.0}, riesgo, 100)
    assert op["veredicto"] == "esperar" and op["precio_sugerido"] < 100


def test_mayoria_en_contra():
    op = supervisor.opinion([s("noticias", -1, 0.7), s("macro_dolar", -1, 0.5)], -0.9, PLAN, None, 100)
    assert op["veredicto"] == "evitar"
