from datetime import date
from mesa.agentes import opciones as OP


def test_bs_e_iv_ida_y_vuelta():
    p = OP.bs("C", 5200, 5400, 45 / 365, 0.2, 0.55)
    assert abs(OP.iv("C", p, 5200, 5400, 45 / 365, 0.2) - 0.55) < 0.01


def test_metadatos_y_cadena():
    crudo = [{"simbolo": "GFGC5800DI", "simboloSubyacente": "GGAL", "tipoOpcion": "Call", "fechaVencimiento": "2026-12-18T15:30:00",
              "descripcion": "Call GGAL 5,800.00 Vencimiento: 18/12/2026"}]
    meta = OP.metadatos(crudo)
    assert meta["GFGC5800DI"]["strike"] == 5800 and meta["GFGC5800DI"]["tipo"] == "C"
    panel = [{"simbolo": "GFGC5800DI", "puntas": {"precioCompra": 198, "precioVenta": 200}, "ultimoPrecio": 199, "volumen": 859, "cantidadOperaciones": 40}]
    cad = OP.cadena(meta, panel, "GGAL", 5215, date(2026, 11, 3), 0.2)
    assert cad and cad[0]["iv"] and 0.3 < cad[0]["iv"] < 0.8 and 0.2 < cad[0]["delta"] < 0.5


def test_lanzador_necesita_100_acciones():
    cad = [{"simbolo": "X", "tipo": "C", "strike": 5800, "vence": "2026-12-18", "dias": 45, "bid": 198, "ask": 200, "spread_pct": 1,
            "operaciones": 10, "volumen": 100, "delta": 0.3, "iv": 0.5}]
    assert OP.experto_lanzador(cad, 5215, 50) is None
    l = OP.experto_lanzador(cad, 5215, 250)
    assert l and l["lotes"] == 2 and l["renta_pct"] > 3


def test_spread_alcista_con_perdida_limitada():
    mk = lambda k, b, a: {"simbolo": f"C{k}", "tipo": "C", "strike": k, "vence": "2026-12-18", "dias": 45, "bid": b, "ask": a,
                         "spread_pct": 3, "operaciones": 10, "volumen": 100, "delta": 0.5, "iv": 0.5}
    cad = [mk(5200, 428, 448), mk(5600, 265, 275), mk(5800, 198, 200), mk(6000, 147, 155)]
    sp = OP.experto_spread(cad, 5215, "a favor")
    assert sp and sp["costo"] > 0 and sp["gana_max"] / sp["costo"] >= 1.3
