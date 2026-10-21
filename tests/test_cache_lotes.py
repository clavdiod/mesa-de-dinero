from mesa.datos.cache import CacheHistorico
from mesa.nucleo.almacen import AlmacenDelDia, AlmacenLocal


def _v(f, c):
    return {"fecha": f, "cierre": c, "maximo": c, "minimo": c, "volumen": 1}


def test_historiales_agrupados_por_letra_y_migracion(tmp_path):
    a = AlmacenLocal(tmp_path)
    a.put("cache/diario/AMD", [_v("2026-10-19", 100)])          # formato viejo
    a.put("cache/indice", {"AMD": {"ruedas": 1}})
    c = CacheHistorico(a)
    assert c.velas("AMD")[0]["cierre"] == 100                   # lo lee del formato viejo
    c.agregar("AAPL", [_v("2026-10-20", 200)])
    c.agregar("MSFT", [_v("2026-10-20", 300)])
    c.guardar()
    assert set(a.get("cache/lote/A")) == {"AMD", "AAPL"} and "MSFT" in a.get("cache/lote/M")
    c2 = CacheHistorico(a)
    assert c2.velas("AAPL")[0]["cierre"] == 200 and c2.velas("AMD")[0]["cierre"] == 100


def test_claves_del_dia_van_dentro_del_estado(tmp_path):
    base = AlmacenLocal(tmp_path)
    dia = {"fecha": "2026-10-21"}
    a = AlmacenDelDia(base, dia)
    a.put("adr/fotos/2026-10-21", [1, 2])
    a.put("otra/clave", 5)
    assert dia["adr/fotos/2026-10-21"] == [1, 2] and base.get("adr/fotos/2026-10-21") is None and base.get("otra/clave") == 5
