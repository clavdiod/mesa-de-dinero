"""20/11: prueba de la revisión automática de compras grandes con TRAN (aviso de las 12:10) y otras acciones."""
from types import SimpleNamespace
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos.cache import CacheHistorico
from mesa.agentes import revision_compra
a = almacen_por_defecto(); cache = CacheHistorico(a)
panel = (a.get("ui/panel") or {}).get("titulos") or {}
tit = lambda tk: (lambda x: {"ultimo": x[0], "variacion": x[1], "compra": x[2], "venta": x[3], "grupo": x[4]} if x else None)(panel.get(tk))
ctx = SimpleNamespace(titulo=tit, cache=cache, hora="12:10")
for tk in ("TRAN", "GGAL", "TGSU2", "ALUA"):
    av = {"fecha": "2026-11-20", "hora": "12:10", "ticker": f"{tk} (compra grande)", "texto": f"⭐🟢 {tk}: alguien grande compra después de la caída. Precio x", "tipo_aviso": "volumen_mercado"}
    r = revision_compra.revisar(ctx, a, av)
    print(f"::notice::{r['ticker']} | entrar={r['entrar']} | {r['texto'][:900]}")
