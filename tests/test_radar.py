from datetime import date

from mesa.agentes import radar
from mesa.nucleo.contexto import Contexto
from mesa.nucleo.modelos import Senal


class _Cache:
    def __init__(self, s):
        self.s, self.indice = s, {k: 1 for k in s}

    def velas(self, tk):
        return self.s.get(tk, [])


def _ctx(panel, cache=None, dol=None, rp=None):
    c = Contexto(date(2026, 10, 21), "12:00", panel, cache=cache or _Cache({}), dolares=dol or {}, riesgo_pais=rp or {})
    return c


def test_volumen_y_precio_anormal_se_marcan():
    velas = {"TXAR": [{"fecha": f"2026-10-{d:02d}", "cierre": 700, "volumen": 1000} for d in range(1, 21)]}
    panel = {"acciones": [{"simbolo": "TXAR", "ultimo": 740, "variacion": 5.0, "volumen": 1200, "monto": 50_000_000}]}
    a = radar.detectar(_ctx(panel, _Cache(velas)), 12 * 60)
    assert a and a[0]["ticker"] == "TXAR" and set(a[0]["tipos"]) == {"volumen", "precio"}


def test_adr_y_macro():
    dol = {"contadoconliqui": {"venta": 1680.0}, "cripto": {"venta": 1710.0}}
    a = radar.detectar(_ctx({}, dol=dol, rp={"valor": 700}), 12 * 60, {"GGAL": 2.0}, rp_ayer=670, ccl_ayer=1630.0)
    tks = {x["ticker"] for x in a}
    assert {"GGAL", "RIESGO PAÍS", "DÓLAR CCL", "DÓLAR CRIPTO"} <= tks


def test_investigar_junta_opiniones_noticias_y_conclusion():
    al = {"tipo": "volumen", "tipos": ["volumen"], "ticker": "TXAR", "grupo": "acciones", "valor": 3.0, "severidad": "alta", "texto": "TXAR: volumen"}
    por = {"TXAR": [Senal("tecnico", "TXAR", 1, 0.6, "Quiebra máximo"), Senal("wallstreet", "TXAR", -1, 0.4, "x")]}
    r = radar.investigar(al, _ctx({}), por, [{"titulo": "Ternium anuncia inversión", "link": "u"}], {"tecnico": "Técnico"})
    assert r["favor"] == 1 and r["contra"] == 1 and "Probable causa" in r["conclusion"] and r["opiniones"][0]["agente"] == "Técnico"
