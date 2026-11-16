from datetime import date
from mesa.agentes import revision_diaria as rd


class A(dict):
    def get(self, k, d=None):
        return super().get(k, d)

    def put(self, k, v):
        self[k] = v


def test_avisa_solo_si_hay_algo():
    a = A({"usuario/cartera": [{"ticker": "CEPU", "precio": 1791, "alertas": [{"tipo": "sube", "nivel": 1850, "moneda": "ARS"}, {"tipo": "baja", "nivel": 1345, "moneda": "ARS"}]}],
           "pronosticos/libreta": [{"ticker": "CEPU", "origen": "mundo", "estado": "se_dio", "fecha_cierre": "2026-11-16", "objetivo_pct": 3.0},
                                   {"ticker": "GGAL", "origen": "mundo", "estado": "fallo", "fecha_cierre": "2026-11-16"}],
           "ui/estado": {"comite": {"pesos": {"mundo": {"acierto": 40, "casos": 30}, "panico": {"acierto": 5, "casos": 90, "baja": True}}}},
           "revision/pesos": {"pesos": {"mundo": {"acierto": 56, "casos": 27}, "panico": {"acierto": 5, "casos": 87, "baja": True}}}})
    pts = rd.armar(a, date(2026, 11, 16), {"CEPU": [1830.0]})
    txt = " ".join(pts)
    assert "CEPU" in txt and "se cumplió" in txt and "GGAL" not in txt  # solo tus papeles
    assert "empezó a fallar" in txt and "panico" not in txt.lower()  # el que ya estaba de baja no se repite
    assert "precio de salida" in txt
    vacio = A({"usuario/cartera": [], "ui/estado": {}})
    assert rd.armar(vacio, date(2026, 11, 16), {}) == [] and rd.avisar(vacio, date(2026, 11, 16), []) is False
