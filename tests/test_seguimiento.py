from datetime import date

from mesa.agentes import seguimiento
from mesa.nucleo.contexto import Contexto
from mesa.nucleo.modelos import Senal


def _p(estado="abierta"):
    return {"ticker": "TXAR", "decision": "aprobada",
            "plan": {"entrada": 700.0, "stop": 670.0, "objetivo": 790.0},
            "seguimiento": {"estado": estado, "precio_entrada": 700.0}}


def _ctx(ult, eventos=()):
    return Contexto(date(2026, 10, 21), "12:00", {"acciones": [{"simbolo": "TXAR", "ultimo": ult}]}, eventos=list(eventos))


def test_sube_stop_a_cero_al_ganar_1r():
    c = seguimiento.consejo(_p(), _ctx(731), [], 0.0)
    assert c["accion"] == "subir_stop" and c["stop_sugerido"] == 700.0


def test_sale_si_la_idea_se_rompe():
    contra = [Senal("macro_dolar", "TXAR", -1, 0.8, "Riesgo país se dispara")]
    c = seguimiento.consejo(_p(), _ctx(705), contra, -0.8)
    assert c["accion"] == "salir" and "Riesgo país" in c["texto"]


def test_avisa_antes_del_balance():
    ev = [{"tipo": "balance", "ticker": "TXAR", "fecha": "2026-10-23"}]
    assert seguimiento.consejo(_p(), _ctx(705, ev), [], 0.0)["accion"] == "antes_balance"


def test_cancela_orden_pendiente_si_la_mesa_ya_no_la_ve():
    assert seguimiento.consejo(_p("pendiente"), _ctx(720), [], -0.4)["accion"] == "cancelar"
