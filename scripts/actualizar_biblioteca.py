"""20/11: llena ya la tabla de Graham (sin esperar al cierre) y muestra cómo quedan algunos CEDEARs."""
from datetime import date
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
from mesa.agentes import biblioteca as B
a = almacen_por_defecto()
a.put(B.CLAVE, {})  # se recalcula todo (20/11: ganancia total en vez de por acción, por los desdoblamientos)
t = B.actualizar(a, _universo_cedears(a), date.today(), maximo=500)
top = sorted(((v["ev"]["cumple"], v["ev"].get("margen_pct") or -999, k) for k, v in t.items() if v.get("ev")), reverse=True)
print(f"::notice::{sum(1 for v in t.values() if v.get('ev'))} empresas con datos · más 'de Graham': " + " | ".join(f"{k} {c}/7 margen {m}%" for c, m, k in top[:15]))
for k in ("NVDA", "MU", "KO", "COST", "AMZN", "MSFT", "JNJ", "PG"):
    print(f"::notice::{k}: {(t.get(k) or {}).get('frase')}")
