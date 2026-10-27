"""Alertas de BAK (compra 27/10: 190 a $988)."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
lista = a.get("usuario/lista") or []
it = next((x for x in lista if x.get("ticker") == "BAK"), None)
if not it:
    it = {"ticker": "BAK", "precio": 988, "nota": "Compra 27/10: 190 a $988 (rebote de corto plazo)"}
    lista.append(it)
nuevas = [{"id": "bak-sube-1050", "tipo": "sube", "nivel": 1050, "moneda": "ARS", "creada": "2026-10-27", "nota": "+6,3%: subí el stop a tu precio de compra ($988)."},
          {"id": "bak-sube-1100", "tipo": "sube", "nivel": 1100, "moneda": "ARS", "creada": "2026-10-27", "nota": "+11%: tomar ganancia (al menos la mitad)."},
          {"id": "bak-baja-930", "tipo": "baja", "nivel": 930, "moneda": "ARS", "creada": "2026-10-27", "nota": "Ojo: se acerca al stop (−5,9%)."},
          {"id": "bak-baja-905", "tipo": "baja", "nivel": 905, "moneda": "ARS", "creada": "2026-10-27", "nota": "Stop (−8,4%, el cierre de ayer): salir."}]
ids = {x.get("id") for x in it.get("alertas") or []}
it.setdefault("alertas", []).extend(x for x in nuevas if x["id"] not in ids)
a.put("usuario/lista", lista)
print("::notice::" + json.dumps(it, ensure_ascii=False)[:1500])
