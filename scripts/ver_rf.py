import json, collections
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
pan = (a.get("ui/panel") or {}).get("titulos") or {}
c = collections.Counter(x[4] for x in pan.values() if x and len(x) > 4)
print("::notice::grupos " + json.dumps(c))
for g in ("ons", "soberanos", "provinciales", "bonos", "letras"):
    xs = [(tk, x) for tk, x in pan.items() if x and len(x) > 4 and x[4] == g]
    print(f"::notice::{g} {len(xs)}: " + json.dumps(xs[:12], ensure_ascii=False)[:900])
fl = a.get("cobros/flujos") or {}
print("::notice::flujos guardados " + str(len(fl)) + ": " + ", ".join(list(fl)[:40]))
k = next((t for t, v in fl.items() if v.get("flujos")), None)
print("::notice::ejemplo " + json.dumps({k: fl.get(k)}, ensure_ascii=False)[:900])
print("::notice::ui/panel claves " + json.dumps(list((a.get("ui/panel") or {}).keys())))
