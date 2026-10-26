"""Completa los precios en EE.UU. de hoy (si faltan) y muestra la proyección de la cartera de la última ronda."""
import json
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
pl = a.get("profesionales/lista") or {}
if not pl.get("precios_usd"):
    est = a.get("ui/estado") or {}
    ced = [c["ticker"].upper() for c in (a.get("usuario/cartera") or []) if ((est.get("precios") or {}).get(c["ticker"].upper()) or {}).get("grupo") == "cedears"]
    pu = {}
    for tk in ced:
        s = gratis.yahoo(tk.replace(".", "-"), "1mo")
        if s:
            pu[tk] = s[-1][1]
    pl["precios_usd"] = pu
    a.put("profesionales/lista", pl)
    print("::notice::USD " + json.dumps(pu))
est = a.get("ui/estado") or {}
for k, x in (est.get("proyeccion_cartera") or {}).items():
    print(f"::notice::{est.get('hora')} {k} | {x.get('consejo')} | {x.get('motivo')} | obj {x.get('objetivo')} ({x.get('potencial_pct')}) {x.get('fuente_objetivo')} | piso {x.get('piso')} ({x.get('a_piso_pct')}) | rango {x.get('rango_1m')} | {x.get('proyeccion')} | res {x.get('resultado_pct')} | precio {x.get('precio')}")
