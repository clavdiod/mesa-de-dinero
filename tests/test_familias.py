"""22/11: los agentes que miran lo mismo cuentan una vez; el Jefe ve quién votó; el Vigía avisa si un agente se calla."""
from datetime import date

from mesa.agentes import comite
from mesa.nucleo import familias, vigia
from mesa.nucleo.contexto import Contexto
from mesa.nucleo.modelos import Senal


class _Reg:
    def peso(self, agente, fuerza=None):
        return 1.0


def _ctx():
    return Contexto(date(2026, 11, 20), "12:00", {"acciones": [{"simbolo": "GGAL", "ultimo": 4500.0}]})


def test_familia():
    assert familias.familia("tecnico") == familias.familia("acciones") == familias.familia("volumen_flujo")
    assert familias.familia("mundo") == familias.familia("noticias")
    assert familias.familia("historiador") == "historiador"


def test_puntaje_mismo_grafico_cuenta_una_vez():
    from mesa.ronda import puntaje_ticker
    s = [Senal("acciones", "GGAL", 1, 0.6, ""), Senal("tecnico", "GGAL", 1, 0.8, ""), Senal("volumen_flujo", "GGAL", 1, 0.5, "")]
    assert puntaje_ticker(s, _Reg(), _ctx()) == 0.8  # antes: 1,9
    s.append(Senal("historiador", "GGAL", 1, 0.5, ""))  # otro método sí suma
    assert puntaje_ticker(s, _Reg(), _ctx()) == 1.3


def test_puntaje_mismo_agente_dos_veces():
    from mesa.ronda import puntaje_ticker
    s = [Senal("mundo", "GGAL", 1, 0.4, "tema"), Senal("mundo", "GGAL", 1, 0.6, "papel")]
    assert puntaje_ticker(s, _Reg(), _ctx()) == 0.6


def test_puntaje_en_contra_dentro_de_familia():
    from mesa.ronda import puntaje_ticker
    s = [Senal("tecnico", "GGAL", 1, 0.3, ""), Senal("acciones", "GGAL", -1, 0.7, "")]
    assert puntaje_ticker(s, _Reg(), _ctx()) == -0.7  # vale la opinión más fuerte de la familia


def _cand(*votos):
    return {"ticker": "GGAL", "grupo": "acciones", "senales": [{"agente": a, "direccion": d, "fuerza": f, "texto": ""} for a, d, f in votos]}


def test_comite_dos_del_mismo_grafico_no_son_dos_analistas():
    v = comite.votar(_cand(("tecnico", 1, 0.8), ("acciones", 1, 0.7), ("volumen_flujo", 1, 0.6)), {})
    assert v["n_favor"] == 1 and not v["aprobada"]
    assert sum(1 for x in v["votos"] if not x["cuenta"]) == 2
    assert all(x["misma_familia"] == "Técnico" for x in v["votos"] if not x["cuenta"])
    v2 = comite.votar(_cand(("tecnico", 1, 0.8), ("acciones", 1, 0.7), ("historiador", 1, 0.6)), {})
    assert v2["n_favor"] == 2 and v2["aprobada"]


def test_jefe_recibe_votos_y_acierto():
    from mesa.agentes.con_ia import _votos_jefe
    vs = _votos_jefe(_cand(("tecnico", 1, 0.8), ("acciones", 1, 0.5)), {"tecnico": {"peso": 1.4, "acierto": 60}})
    assert vs[0]["quien"] == "Técnico" and vs[0]["acierto_en_vivo"] == "60%"
    assert vs[1]["repite_a"] == "Técnico"


def test_vigia_avisa_una_vez_cuando_se_calla():
    est, todos = None, {"tecnico", "historiador"}
    for i in range(20):
        est, av = vigia.actualizar(est, todos, "2026-11-20", f"12:{i:02d}")
        assert not av
    avisos = []
    for i in range(10):
        est, av = vigia.actualizar(est, {"historiador"}, "2026-11-20", f"13:{i:02d}")
        avisos += av
    assert len(avisos) == 1 and avisos[0]["agente"] == "tecnico" and "6 rondas" in avisos[0]["texto"]
    assert est["mudos"] == ["tecnico"]
    est, av = vigia.actualizar(est, todos, "2026-11-20", "14:00")
    assert est["mudos"] == [] and not av


def test_vigia_no_avisa_al_que_habla_poco():
    est = None
    for i in range(40):
        est, av = vigia.actualizar(est, {"historiador"} | ({"panico"} if i % 10 == 0 else set()), "2026-11-20", f"12:{i:02d}")
        assert not [a for a in av if a["agente"] == "panico"]
