from mesa.datos.cache import ajustar_splits


def test_split_10_a_1():
    v = [{"fecha": f"d{i:02d}", "cierre": 80000.0 + i, "apertura": 80000.0, "maximo": 81000.0, "minimo": 79000.0, "volumen": 10} for i in range(5)]
    v += [{"fecha": f"d{i:02d}", "cierre": 8000.0 + i, "apertura": 8010.0, "maximo": 8100.0, "minimo": 7900.0, "volumen": 100} for i in range(5, 10)]
    assert ajustar_splits(v) == ["d05 10:1"]
    assert max(x["maximo"] for x in v) < 9000 and v[0]["volumen"] == 100
    assert ajustar_splits(v) == []  # ya ajustado: no se toca dos veces


def test_caida_fuerte_no_es_split():
    v = [{"fecha": "a", "cierre": 100.0}, {"fecha": "b", "cierre": 60.0}]
    assert ajustar_splits(v) == [] and v[0]["cierre"] == 100.0
