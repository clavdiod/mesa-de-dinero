from datetime import date

from mesa.nucleo.almacen import AlmacenLocal
from mesa.nucleo.simulacion import Simulador


class Ctx:
    def __init__(self, grupo="acciones"):
        self.g = grupo

        self.extra, self.dolares = {"mep_al30": 1500.0}, {}

    def titulo(self, tk):
        return {"grupo": self.g}


def op(tk="GGAL", entrada=100.0, stop=95.0, obj=110.0, semaforo="verde"):
    return {"ticker": tk, "setup": "Rebote en soporte", "semaforo": semaforo, "mesa": {"aprobada": True},
            "plan": {"entrada": entrada, "stop": stop, "objetivo": obj, "vence": "2026-11-03"}}


def test_objetivo_gana_plata_con_comision(tmp_path):
    s = Simulador(AlmacenLocal(tmp_path))
    assert s.abrir({"corto": [op()]}, [], Ctx(), {}, date(2026, 10, 20), "11:00") == 1
    # misma oportunidad en otra ronda del mismo día: no se duplica
    assert s.abrir({"corto": [op()]}, [], Ctx(), {}, date(2026, 10, 20), "11:05") == 0
    s.actualizar({"GGAL": {"ultimo": 108, "maximo": 111, "minimo": 99}}, date(2026, 10, 21))
    p = s.pos[0]
    assert p["estado"] == "objetivo" and p["salida"] == 110
    # 1000 acciones: +10.000 bruto, menos 0,6% de 100.000 y 0,6% de 110.000
    assert p["ganancia"] == 10000 - 600 - 660
    r = s.resumen()
    assert r["total"]["cerradas"] == 1 and r["total"]["ganadoras_pct"] == 100


def test_bonos_cotizan_cada_100_y_stop_gana_al_objetivo_el_mismo_dia(tmp_path):
    s = Simulador(AlmacenLocal(tmp_path))
    s.abrir({"corto": [op("AL30D")]}, [], Ctx("soberanos"), {}, date(2026, 10, 20), "11:00")
    s.actualizar({"AL30D": {"ultimo": 100, "maximo": 112, "minimo": 94}}, date(2026, 10, 22))
    p = s.pos[0]
    # AL30D cotiza en dólares: se pasa a pesos con el MEP de la compra (1.500)
    assert p["moneda"] == "USD" and p["estado"] == "stop" and round(p["ganancia"], 2) == round((-50 - 6 - 5.7) * 1500, 2)


def test_el_dia_de_compra_solo_cuenta_el_ultimo(tmp_path):
    s = Simulador(AlmacenLocal(tmp_path))
    s.abrir({"corto": [op()]}, [], Ctx(), {}, date(2026, 10, 20), "11:00")
    s.actualizar({"GGAL": {"ultimo": 101, "maximo": 101, "minimo": 90}}, date(2026, 10, 20))
    assert s.pos[0]["estado"] == "abierta" and s.pos[0]["ganancia_actual"] < 1000


def test_limite_del_jefe_que_no_se_da(tmp_path):
    s = Simulador(AlmacenLocal(tmp_path))
    nueva = {"id": "x", "ticker": "CRES", "plan": {"entrada": 1800, "stop": 1750, "objetivo": 1960, "vence": "2026-11-03"}}
    s.abrir({}, [nueva], Ctx(), {}, date(2026, 10, 20), "11:00")
    s.actualizar({"CRES": {"ultimo": 1850, "maximo": 1860, "minimo": 1820}}, date(2026, 10, 29))
    assert s.pos[0]["estado"] == "no_se_dio"
