"""20/11: prueba en seco de 'Tu cartera hoy' con el panel guardado (sin noticias, no avisa nada)."""
from datetime import date
from types import SimpleNamespace
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos.cache import CacheHistorico
from mesa.agentes import cartera_hoy as C
a = almacen_por_defecto()
pan = (a.get("ui/panel") or {}).get("titulos") or {}
tit = {tk: {"ultimo": x[0], "variacion": x[1], "compra": x[2], "venta": x[3], "grupo": x[4]} for tk, x in pan.items() if x and x[0]}
ctx = SimpleNamespace(fecha=date.today(), hora="11:10", por_simbolo=tit, titulo=lambda tk: tit.get(tk), cache=CacheHistorico(a))
r = C.armar(ctx, a, a.get("usuario/cartera") or [], date.today())
for l in (r or {}).get("lineas", []):
    print("::notice::" + l[:900])
