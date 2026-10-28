import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
est = a.get("ui/estado") or {}
pre = est.get("precios") or {}
print(f"::notice::ronda {est.get('fecha')} {est.get('hora')}")
for x in (est.get("anticipos") or [])[:10]:
    p = pre.get(x["ticker"]) or {}
    print(f"::notice::{x['ticker']} atraso {x['atraso']} spread {x.get('spread')} neto {x.get('neto')} compra {p.get('compra')} venta {p.get('venta')} ultimo {p.get('ultimo')}")
