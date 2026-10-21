from datetime import date

from mesa.agentes import adr
from mesa.nucleo.contexto import Contexto


def test_brecha_sin_ratio():
    local = {"2026-10-19": 6000.0, "2026-10-20": 6000.0}
    adr_s = {"2026-10-19": 40.0, "2026-10-20": 41.2}      # +3% en NY
    ccl = {"2026-10-19": 1600.0, "2026-10-20": 1600.0}
    assert adr.brecha(local, adr_s, ccl, "2026-10-20") == 3.0


def test_entrenar_mide_desde_la_apertura():
    velas, adrs, ccl = [], [], {}
    p = 100.0
    for i in range(60):
        f = f"2026-0{1 + i // 28}-{1 + i % 28:02d}"
        velas.append({"fecha": f, "apertura": p * 1.01, "cierre": p, "maximo": p * 1.02, "minimo": p * 0.98})
        adrs.append([f, p * (1.03 if i % 5 == 0 else 1.0) / 10])
        ccl[f] = 1000.0
    st = adr.entrenar({"GGAL": velas}, {"GGAL": adrs}, ccl)
    assert st["por_horizonte"]["cierre_sig"]["casos"] > 0


class _Cache:
    def __init__(self, v):
        self.v = v
        self.indice = {"GGAL": 1}

    def velas(self, tk):
        return self.v if tk == "GGAL" else []


def test_senal_en_la_manana_descuenta_lo_que_ya_se_movio():
    velas = [{"fecha": "2026-10-19", "cierre": 6000.0}, {"fecha": "2026-10-20", "cierre": 6000.0}]
    datos = {"adrs": {"GGAL": [["2026-10-19", 40.0], ["2026-10-20", 41.2]]}}
    ccl = {"2026-10-19": 1600.0, "2026-10-20": 1600.0}
    ctx = Contexto(date(2026, 10, 21), "10:40", {"acciones": [{"simbolo": "GGAL", "ultimo": 6060.0}]}, cache=_Cache(velas))
    sen, tabla = adr.senales_en(ctx, datos, ccl, 640)
    assert tabla[0]["resta"] == 2.0 and sen and sen[0].direccion == 1
    assert adr.senales_en(ctx, datos, ccl, 14 * 60)[0] == []


def test_estadistica_propia_de_durante_el_dia():
    def fo(h, adr_p, loc_p):
        return {"hora": h, "ccl": 1600.0, "filas": {"GGAL": {"adr": adr_p, "adr_ant": 40.0, "loc": loc_p, "loc_ant": 6000.0}}}
    # 11:00 el ADR sube 3% y la local no se movió; a las 11:30 la local subió 2%
    fotos = [fo("11:00", 41.2, 6000.0), fo("11:30", 41.2, 6120.0), fo("12:00", 41.2, 6150.0), fo("16:55", 41.0, 6150.0)]
    est = adr.estadistica_del_dia(fotos, 1600.0)
    assert est["30"]["casos"] >= 1 and est["30"]["suma_ret"] > 0
    tot = adr.acumular({}, est)
    assert tot["30"]["casos"] == est["30"]["casos"]
