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
