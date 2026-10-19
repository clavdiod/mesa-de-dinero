import base64
import json
from datetime import date, datetime

import pytest

from mesa.nucleo.reloj import TZ
from tests.conftest import serie


def test_consumo_y_tope(almacen, monkeypatch):
    from mesa.datos.consumo import Consumo, PresupuestoAgotado
    c = Consumo(almacen)
    c.datos["total"] = 24999
    assert c.puede_consultar(1) and not c.puede_consultar(2)
    c.anotar("panel")
    with pytest.raises(PresupuestoAgotado):
        c.anotar("panel")
    c.guardar()
    assert Consumo(almacen).total == 25000
    assert c.solo_cierre() and c.factor_frecuencia() == 2


def test_frecuencia_adaptativa():
    from mesa.nucleo.reloj import toca_correr
    d = lambda h, m: datetime(2026, 10, 19, h, m, tzinfo=TZ)
    assert toca_correr(d(10, 30)) and toca_correr(d(10, 35)) and not toca_correr(d(10, 33))
    assert toca_correr(d(13, 30)) and not toca_correr(d(13, 35))          # mediodía cada 10
    assert toca_correr(d(16, 5))                                          # última hora cada 5
    assert not toca_correr(d(17, 30)) and not toca_correr(d(9, 0))
    assert not toca_correr(d(10, 35), factor=2) and toca_correr(d(10, 40), factor=2)


def test_cache_no_duplica_ni_repite(almacen):
    from mesa.datos.cache import CacheHistorico
    c = CacheHistorico(almacen)
    v = serie(50)
    assert c.agregar("GGAL", v) == 50
    assert c.agregar("GGAL", v[-5:]) == 0
    c.guardar()
    c2 = CacheHistorico(almacen)
    assert len(c2.velas("GGAL")) == 50 and c2.indice["GGAL"]["ruedas"] == 50


def test_seguimiento_en_r(almacen):
    from mesa.nucleo.registro import Registro
    r = Registro(almacen)
    r.nuevas([{"id": "x", "ticker": "CRES", "fecha": "2026-10-19", "decision": "aprobada",
               "plan": {"entrada": 1825, "stop": 1770, "objetivo": 1960, "vence": "2026-11-02"},
               "seguimiento": {"estado": "pendiente"}}])
    # el mínimo del día (1818) fue ANTES de proponer: no cuenta como entrada
    r.actualizar_seguimiento({"CRES": {"ultimo": 1829, "minimo": 1818, "maximo": 1869}}, date(2026, 10, 19))
    assert r.propuestas[0]["seguimiento"]["estado"] == "pendiente"
    r.actualizar_seguimiento({"CRES": {"ultimo": 1825, "minimo": 1818, "maximo": 1869}}, date(2026, 10, 19))
    assert r.propuestas[0]["seguimiento"]["estado"] == "abierta"
    # mismo día de entrada: un mínimo previo de 1760 (debajo del stop) tampoco cuenta
    r.actualizar_seguimiento({"CRES": {"ultimo": 1830, "minimo": 1760, "maximo": 1869}}, date(2026, 10, 19))
    assert r.propuestas[0]["seguimiento"]["estado"] == "abierta"
    r.actualizar_seguimiento({"CRES": {"ultimo": 1965, "minimo": 1900, "maximo": 1970}}, date(2026, 10, 22))
    s = r.propuestas[0]["seguimiento"]
    assert s["estado"] == "objetivo" and s["r"] == pytest.approx(2.45, abs=0.01) and s["r_neto"] < s["r"]
    assert r.esperanza_mesa()["casos"] == 1


def test_riesgo_frena_bancos_con_riesgo_pais_alto(almacen):
    from mesa.agentes import riesgo
    from mesa.datos.cache import CacheHistorico
    from mesa.nucleo.contexto import Contexto
    from mesa.nucleo.modelos import Plan
    cache = CacheHistorico(almacen)
    cache.agregar("GGAL", serie(120, 6000))
    ctx = Contexto(date(2026, 10, 19), "14:46", {"acciones": [{"simbolo": "GGAL", "ultimo": 5655, "compra": 5645,
                                                               "venta": 5655, "monto": 9e9}]},
                   riesgo_pais={"valor": 675}, cache=cache)
    r = riesgo.evaluar(ctx, Plan("GGAL", "compra", 5650, 5540, 5950), {"abiertas": [], "propuestas_hoy": []}, set())
    assert not r["ok"] and any("Riesgo país" in m for m in r["motivos"])


def test_ronda_simulada_completa(almacen):
    """La ronda entera sin IOL ni IA: agentes, Riesgo, Jefe de respaldo, registro y estado para la web."""
    from mesa.datos.cache import CacheHistorico
    from mesa.ronda import correr
    cache = CacheHistorico(almacen)
    for i, (tk, p) in enumerate({"GGAL": 5800, "CRES": 1800, "YPFD": 8400, "PAMP": 5100, "ALUA": 800,
                                 "AL30D": 55.5, "GD30D": 56.8}.items()):
        cache.agregar(tk, serie(260, p, semilla=i + 10))
    cache.guardar()
    almacen.put("usuario/lista", [{"ticker": "CRES", "precio": 1820}])
    res = correr(forzar=True, simular=True)
    assert res["corrio"] is True
    est = almacen.get("ui/estado")
    assert est["clima"] == "malo"                       # riesgo país +27
    assert est["indicadores"]["mep_al30"] == pytest.approx(85000 / 55.32, rel=1e-3)
    agentes = {s["agente"] for s in est["senales"]}
    assert {"macro_dolar", "cedears", "soberanos"} <= agentes
    assert any(s["agente"] == "cedears" and s["ticker"] == "KO" and s["direccion"] == 1 for s in est["senales"])
    for e in est["evaluados"]:
        if e["ticker"] in ("GGAL", "BMA"):
            assert not e["riesgo"]["ok"]                 # filtro de riesgo país
    assert almacen.get("ui/alertas")[0]["ticker"] == "CRES"   # tocó tu precio 1820
    props = almacen.get("registro/propuestas") or []
    assert len(props) <= 3
    for p in props:
        assert p["riesgo"]["ok"] and p["plan"]["stop"] < p["plan"]["entrada"] < p["plan"]["objetivo"]


def test_push_firma_vapid_valida(monkeypatch):
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
    from mesa.nucleo import push
    k = push.generar_claves()
    tok = push._jwt("https://fcm.googleapis.com", k["privada"], "mailto:x@y.z")
    h, b, s = tok.split(".")
    raw = push._b64u_dec(s)
    pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), push._b64u_dec(k["publica"]))
    pub.verify(encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big")),
               f"{h}.{b}".encode(), ec.ECDSA(hashes.SHA256()))
    assert json.loads(push._b64u_dec(b))["aud"] == "https://fcm.googleapis.com"


def test_normalizacion_iol():
    from mesa.datos.iol import normalizar_titulo
    t = normalizar_titulo({"simbolo": "GGAL", "ultimoPrecio": 5655, "variacionPorcentual": -2.58,
                           "puntas": {"cantidadCompra": 4131, "precioCompra": 5645, "precioVenta": 5655, "cantidadVenta": 5326},
                           "volumen": 1584377, "montoOperado": 9047417450})
    assert t["compra"] == 5645 and t["venta"] == 5655 and t["monto"] == 9047417450
    t2 = normalizar_titulo({"simbolo": "X", "ultimoPrecio": "1.829,50", "cierreAnterior": 1860,
                            "puntas": [{"precioCompra": 1829, "cantidadCompra": 38, "precioVenta": 1835, "cantidadVenta": 2579}]})
    assert t2["ultimo"] == 1829.5 and round(t2["variacion"], 2) == -1.64
