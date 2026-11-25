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


def test_soporte_ignora_vela_rota_con_minimo_cero():
    from mesa.nucleo import calc
    from tests.conftest import serie
    vs = serie(120)
    vs[-30] = {**vs[-30], "minimo": 0.0}
    precio = min(v["minimo"] for v in vs if v["minimo"]) * 0.5  # todo lo sano queda arriba: antes el "soporte" era 0
    sop = calc.soporte_cercano(vs, precio)
    assert sop is None or sop["nivel"] > 0


def test_motivo_corto_con_precios():
    from mesa.agentes.ficha_frio import motivo_corto
    f = {"veredicto": "cara", "entrada_mejor": 8332.0, "entrada_cara": ["la entrada está en el 99% más alto de su rango de 3 meses"]}
    m = motivo_corto(f, 8880.9, 8850.0)
    assert m.startswith("entrada cara: precio actual 8.850; entrada del plan 8.881; precio razonable 8.332 o menos (5,9% más abajo)")
    assert "99%" in m
    f2 = {"veredicto": "dudosos", "alertas": ["el caso típico terminó en -3,3% a un mes"]}
    assert motivo_corto(f2, 100.0, 100.0) == "números flojos: precio actual 100; el caso típico terminó en -3,3% a un mes"


def test_parte_dice_cartera_o_lista():
    from mesa.ronda import _parte_ronda
    ctx = _ctx()
    al = [{"fecha": "2026-11-24", "ticker": "IBB (radar)", "tipo": "radar", "texto": "IBB: en Nueva York va +5%"}]
    p = _parte_ronda(ctx, date(2026, 11, 24), [], [], al, [], [], [], 3, [{"ticker": "GGAL"}])
    assert "novedad en tu lista" in p["titulo"]
    p = _parte_ronda(ctx, date(2026, 11, 24), [], [], al, [], [], [], 3, [{"ticker": "IBB"}])
    assert "novedad en tu cartera" in p["titulo"]


def test_vigia_no_avisa_fuera_de_horario():
    """24/11: Noche de Nueva York opina solo hasta las 13 h; callarse a la tarde no es estar caído."""
    est = None
    for i in range(12):
        est, av = vigia.actualizar(est, {"adr", "historiador"}, "2026-11-24", f"11:{30 + i:02d}")
    avisos = []
    for i in range(20):
        est, av = vigia.actualizar(est, {"historiador"}, "2026-11-24", f"14:{i:02d}")
        avisos += av
    assert not avisos and est["mudos"] == []


def test_adr_tras_feriado_mira_la_ultima_noche():
    """24/11: el lunes 23 fue feriado acá y Nueva York operó: la brecha tiene que incluir esa rueda."""
    from mesa.agentes import adr
    local = {"2026-11-19": 100.0, "2026-11-20": 98.0}
    ny = {"2026-11-19": 26.07, "2026-11-20": 25.29, "2026-11-23": 26.62}
    ccl = {"2026-11-19": 1800.0, "2026-11-20": 1800.0, "2026-11-23": 1800.0}
    b = adr.brecha_tras_feriado(local, ny, ccl, "2026-11-20", "2026-11-24")
    assert round(b, 1) == round((26.62 / 26.07 - 1) * 100 + 2.0, 1)  # +2,1% del ADR contra -2% local
    assert adr.brecha_tras_feriado(local, ny, ccl, "2026-11-20", "2026-11-23") == adr.brecha(local, ny, ccl, "2026-11-20")


def test_adr_en_vivo_tras_feriado_usa_base_local():
    from mesa.agentes import adr

    class _C:
        def velas(self, t):
            return [{"fecha": "2026-11-19"}, {"fecha": "2026-11-20"}]

    class _Ctx:
        cache = _C()
    fo = {"filas": {"GGAL": {"adr": 26.0, "adr_ant": 26.62, "loc": 4600.0, "loc_ant": 4400.0}}}
    fo = adr.base_feriado(fo, _Ctx(), {"GGAL": [["2026-11-20", 25.29], ["2026-11-23", 26.62]]}, {"2026-11-20": 1800.0}, "2026-11-24")
    assert fo["filas"]["GGAL"]["adr_ant"] == 25.29 and fo["ccl_ant"] == 1800.0


def test_alarma_de_mi_lista_opina_al_sonar(almacen):
    """24/11 (NVDA): la alarma de Mi lista no trae un "no es momento" escrito de antemano; la mesa mira al sonar.
    Las de tu cartera (alarma de venta) siguen con su nota."""
    from mesa.ronda import _alertas_niveles
    from tests.conftest import serie
    vs = serie(300)
    pr = vs[-1]["cierre"]

    class _C:
        def velas(self, t):
            return vs
    ctx = Contexto(date(2026, 10, 17), "12:00", {"cedears": [{"simbolo": "NVDA", "ultimo": pr}], "acciones": [{"simbolo": "GGAL", "ultimo": pr}]})
    ctx.cache = _C()
    lista = [{"ticker": "NVDA", "alertas": [{"id": "a1", "tipo": "baja", "nivel": pr * 1.1, "nota": "no es momento de entrar"}]}]
    cart = [{"ticker": "GGAL", "alertas": [{"id": "a2", "tipo": "baja", "nivel": pr * 1.1, "nota": "Alarma de venta"}]}]
    out = _alertas_niveles(ctx, lista + cart, almacen, False, de_lista={id(lista[0])})
    t = {o["ticker"]: o["texto"] for o in out}
    assert "no es momento" not in t["NVDA"] and "La mesa lo mira ahora" in t["NVDA"]
    assert "Alarma de venta" in t["GGAL"] and "La mesa" not in t["GGAL"]


def test_posicion_respeta_la_alarma_del_plan():
    """25/11 (TGSU2): comprada ayer a 7.000 por una posición a 3 meses (alarma 5.284). A 6.985 no es "perforó el piso"."""
    from mesa.agentes import proyeccion
    from tests.conftest import serie
    vs = [{**v, "cierre": v["cierre"] * 7 , "maximo": v["maximo"] * 7, "minimo": v["minimo"] * 7} for v in serie(120)]
    pr = 6985.0
    cart = [{"ticker": "TGSU2", "cantidad": 33, "precio": 7000.0, "fecha": "2026-11-24", "propuesta_id": "bceb78f8c2",
             "alertas": [{"id": "s", "tipo": "baja", "nivel": 5283.75, "nota": "Alarma de venta (-24.5% de tu compra): la idea no se dio."}]}]
    props = [{"id": "bceb78f8c2", "ticker": "TGSU2", "linea": "posicion", "meses": 3, "decision": "pendiente",
              "plan": {"entrada": 7045.0, "stop": 5283.75, "objetivo": 8806.25}}]
    out = proyeccion.para_cartera(cart, lambda t: {"ultimo": pr, "grupo": "acciones"}, lambda t: vs, {}, props, {}, {}, [], [],
                                  hora="11:10")
    x = out["TGSU2"]
    assert x["piso"] == 5283.75 and x["consejo"] != "Vender" and "posición a 3 meses" in x["fuente_objetivo"]
