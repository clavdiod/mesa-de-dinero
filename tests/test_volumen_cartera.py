from mesa.agentes import volumen_cartera as vc


def _velas(n=40, vol=1000, ultimo=None):
    v = [{"fecha": f"2026-10-{i + 1:02d}" if i < 31 else f"2026-11-{i - 30:02d}", "cierre": 100.0, "volumen": vol} for i in range(n)]
    if ultimo:
        v[-1].update(ultimo)
    return v


def test_venta_fuerte_avisa_una_vez():
    tit = lambda tk: {"grupo": "acciones", "ultimo": 96, "cierre_anterior": 100, "maximo": 101, "minimo": 95.5, "volumen": 3000}
    av = {}
    r = vc.avisos([{"ticker": "TRAN"}], tit, lambda tk: _velas(), "2026-11-11", "13:45", av)
    assert len(r) == 1 and "vendedores fuertes" in r[0]["texto"] and "alarma" in r[0]["texto"]
    assert vc.avisos([{"ticker": "TRAN"}], tit, lambda tk: _velas(), "2026-11-11", "14:00", av) == []  # no repite


def test_agotamiento():
    tit = lambda tk: {"grupo": "acciones", "ultimo": 95, "cierre_anterior": 94, "maximo": 96, "minimo": 93.5, "volumen": 900}
    vel = _velas(ultimo={"cierre": 94.0, "volumen": 5000})
    r = vc.avisos([{"ticker": "TRAN"}], tit, lambda tk: vel, "2026-11-11", "15:30", {})
    assert len(r) == 1 and "agotarse" in r[0]["texto"]


def test_nada_antes_del_mediodia_ni_en_cedears():
    tit = lambda tk: {"grupo": "acciones", "ultimo": 96, "cierre_anterior": 100, "maximo": 101, "minimo": 95.5, "volumen": 3000}
    assert vc.avisos([{"ticker": "TRAN"}], tit, lambda tk: _velas(), "2026-11-11", "11:30", {}) == []
    ced = lambda tk: {**tit(tk), "grupo": "cedears"}
    assert vc.avisos([{"ticker": "IBB"}], ced, lambda tk: _velas(), "2026-11-11", "13:45", {}) == []
