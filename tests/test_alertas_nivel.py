from datetime import date

from mesa import ronda


class Ctx:
    fecha, hora = date(2026, 10, 22), "12:30"
    def titulo(self, tk):
        return {"IREN": {"ultimo": 3470, "minimo": 3400, "maximo": 3600}}.get(tk)


class A(dict):
    def put(self, k, v): self[k] = v


def test_alertas_de_nivel(monkeypatch):
    monkeypatch.setattr(ronda.gratis, "yahoo_varios", lambda tks, prepost=False: {"IREN": {"precio": 24.9}})
    lista = [{"ticker": "IREN", "alertas": [{"id": "a", "tipo": "baja", "nivel": 25.6, "moneda": "USD"},
                                            {"id": "b", "tipo": "sube", "nivel": 27.5, "moneda": "USD"},
                                            {"id": "c", "tipo": "baja", "nivel": 3450, "moneda": "ARS"}]}]
    al = A()
    out = ronda._alertas_niveles(Ctx(), lista, al, False)
    assert {x["id"] for x in out} == {"a", "c"} and "bajó de US$" in out[0]["texto"]
    assert ronda._alertas_niveles(Ctx(), lista, al, False) == []   # avisa una sola vez


def test_alarma_creada_hoy_no_suena_con_el_minimo_de_antes():
    """25/11: METR, alarma subida a 1.737,5 después de la caída de las 13:10; sonó con el mínimo del día y el precio en 1.801."""
    class C(Ctx):
        def titulo(self, tk):
            return {"METR": {"ultimo": 1801, "minimo": 1630, "maximo": 1830}}.get(tk)
    hoy = C.fecha.isoformat()
    cart = [{"ticker": "METR", "alertas": [{"id": "n", "tipo": "baja", "nivel": 1737.5, "moneda": "ARS", "creada": hoy},
                                           {"id": "v", "tipo": "baja", "nivel": 1700, "moneda": "ARS", "creada": "2026-10-01"}]}]
    out = ronda._alertas_niveles(C(), cart, A(), False)
    assert [x["id"] for x in out] == ["v"]
