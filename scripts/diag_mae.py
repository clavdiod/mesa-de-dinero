import json
from mesa.datos import cobros
from mesa.datos.gratis import _S
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
fl = a.get("cobros/flujos") or {}
malos = [t for t, v in fl.items() if v.get("sin_datos") and t.endswith("D")][:6]
print("::notice::sin datos ej: " + ", ".join(malos) + f" (total {sum(1 for v in fl.values() if v.get('sin_datos'))})")
for t in malos[:4]:
    for c in cobros.candidatos(t) + [t[:-1] + "D", t[:-1] + "C"]:
        try:
            r = _S.get(cobros._MAE + f"emisiones/flujofondos/{c}", headers=cobros._H, timeout=20)
            j = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            print(f"::notice::{t} → {c}: {r.status_code} detalle {len(j.get('detalle') or [])} especie {j.get('especie')} | {r.text[:150]}")
        except Exception as ex:
            print(f"::notice::{t} → {c}: ERR {ex}")
