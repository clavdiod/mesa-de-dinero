from mesa.agentes import salida


def _velas(sube=True):
    return [{"fecha": f"d{i:03d}", "cierre": 100 + (i * 0.5 if sube else -i * 0.3) + (i % 3), "volumen": 1000} for i in range(220)]


def test_nunca_vuelve_a_perdida_y_decide():
    v = _velas(True)
    p = v[-1]["cierre"] * 1.01
    r = salida.analizar("CEPU", p, compra=p / 1.04, salida=p / 1.005, velas=v, titulo={"volumen": 3000, "maximo": p, "minimo": p * 0.97, "variacion": 2},
                        grupo="acciones", a_favor=["a", "b"], en_contra=[], hora="15:00")
    assert r["accion"] == "dejar_correr" and r["alarma"] >= (p / 1.04) * 1.015
    vb = _velas(False); pb = vb[-1]["cierre"] * 0.99
    r2 = salida.analizar("CEPU", pb, compra=pb / 1.04, salida=pb / 1.005, velas=vb, titulo={"volumen": 3000, "maximo": pb * 1.04, "minimo": pb * 0.995, "variacion": -2},
                         grupo="acciones", a_favor=[], en_contra=["a", "b"], hora="15:00")
    assert r2["accion"] == "vender_todo"
