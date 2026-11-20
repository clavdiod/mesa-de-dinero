from mesa.nucleo.almacen import almacen_por_defecto
from mesa.agentes import biblioteca as B
from mesa.agentes.fundamentos import _ciks
a = almacen_por_defecto(); f = a.get("fundamentos/cedears") or {}; t = a.get(B.CLAVE) or {}
c = _ciks()
for k in ("NVDA", "MU", "KO", "MSFT"):
    s = B.datos_sec(c[k])
    print(f"::notice::{k} fund={ {x: (f.get(k) or {}).get(x) for x in ('precio_usd', 'eps_12m', 'fecha')} } bib={t.get(k)} sec_eps={len((s or {}).get('eps') or [])} ultimos={(s or {}).get('eps', [])[-3:]}")
print(f"::notice::con precio_usd: {sum(1 for v in f.values() if v.get('precio_usd'))} de {len(f)} · bib sin_datos {sum(1 for v in t.values() if v.get('sin_datos'))}")
