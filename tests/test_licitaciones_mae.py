from datetime import date

from mesa.datos import eventos, gratis


class R:
    def __init__(self, j): self.j = j
    def json(self): return self.j
    def raise_for_status(self): pass


def test_licitaciones_mae(monkeypatch):
    lista = {"events": [
        {"id": -1003, "title": "ON BAJO IMPACTO COLGAS CLASE I", "start": "2026-10-21T13:00:00Z", "end": "2026-10-21T19:00:00Z"},
        {"id": -266, "title": "LICITACION DEL MINISTERIO DE ECONOMÍA DE ACUERDO AL CRONOGRAMA", "start": "2026-10-28T03:00:00Z", "end": "2026-10-28T03:00:00Z"}]}
    det = {"emisor": "COLGAS S.A.", "moneda": "USD", "montoaLicitar": 5000000, "variableLicitar": "TASA",
           "fechaLiquidacion": "2026-10-24T03:00:00Z", "estado": "Activa"}

    def get(url, **k):
        return R(lista if url.endswith("licitaciones") else det)
    monkeypatch.setattr(gratis._S, "get", get)
    evs = gratis.licitaciones_mae(date(2026, 10, 20), date(2026, 11, 30))
    on, tes = evs
    assert on["clase"] == "ON" and on["fecha"] == "2026-10-21" and on["hora_cierre"] == "16:00"
    assert on["emisor"] == "COLGAS S.A." and "en dólares" in on["nombre"] and "liquida 24/10" in on["nombre"]
    assert tes["clase"] == "Tesoro" and tes["fecha"] == "2026-10-28" and not tes["hora_cierre"]

    class A(dict):
        def put(self, k, v): self[k] = v
    a = A()
    monkeypatch.setattr(gratis, "licitaciones_mae", lambda d, h: evs)
    eventos.actualizar_licitaciones(a, date(2026, 10, 21), "10:00")
    cal = eventos.armar(a, date(2026, 10, 21), 45, set())
    assert any(e["tipo"] == "licitacion" and e["mio"] for e in cal)
