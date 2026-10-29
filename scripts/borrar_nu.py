"""Saca NU (Nubank) de todo lo del usuario: cartera, lista, decisiones y avisos de seguimiento."""
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
es_nu = lambda x: str((x.get("ticker") if isinstance(x, dict) else x) or "").upper() in ("NU", "NUD", "NUC")
for k in ("usuario/cartera", "usuario/lista"):
    v = a.get(k) or []
    n = [x for x in v if not es_nu(x)]
    a.put(k, n)
    print(f"::notice::{k}: {len(v) - len(n)} borrados · quedan " + ", ".join(str(x.get('ticker') if isinstance(x, dict) else x) for x in n))
for k in ("usuario/decisiones_cartera", "cartera/avisados"):
    d = a.get(k) or {}
    if isinstance(d, dict):
        for t in ("NU", "NUD", "NUC"):
            d.pop(t, None)
        a.put(k, d)
