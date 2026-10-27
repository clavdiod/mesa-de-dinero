"""BAK pasó $1.050 (máximo 1.210 el 27/10): el stop sube a $988, el precio de compra."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
lista = a.get("usuario/lista") or []
it = next((x for x in lista if x.get("ticker") == "BAK"), None)
it["alertas"] = [x for x in it.get("alertas") or [] if x.get("id") not in ("bak-baja-905", "bak-baja-930", "bak-sube-1050")]
it["alertas"] += [{"id": "bak-baja-1020", "tipo": "baja", "nivel": 1020, "moneda": "ARS", "creada": "2026-10-27", "nota": "Ojo: se acerca a tu precio de compra."},
                  {"id": "bak-baja-988", "tipo": "baja", "nivel": 988, "moneda": "ARS", "creada": "2026-10-27", "nota": "Stop en tu precio de compra (ya pasó $1.050): salir sin perder."}]
a.put("usuario/lista", lista)
print("::notice::" + json.dumps(it, ensure_ascii=False)[:1500])
