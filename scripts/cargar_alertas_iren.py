"""Suma a IREN las alertas en pesos (precio del CEDEAR en BYMA), pedido del usuario 22/10."""
import json

from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
lista = a.get("usuario/lista") or []
it = next((x for x in lista if x.get("ticker") == "IREN"), None)
if not it:
    it = {"ticker": "IREN", "precio": None, "nota": "Compra 22/10"}
    lista.append(it)
nuevas = [{"id": "iren-ars-sube-3830", "tipo": "sube", "nivel": 3830, "moneda": "ARS", "creada": "2026-10-22", "nota": "En pesos: +9,6% sobre tu compra (zona para sumar)."},
          {"id": "iren-ars-baja-3205", "tipo": "baja", "nivel": 3205, "moneda": "ARS", "creada": "2026-10-22", "nota": "En pesos: zona de stop (−8,3%)."},
          {"id": "iren-ars-baja-2845", "tipo": "baja", "nivel": 2845, "moneda": "ARS", "creada": "2026-10-22", "nota": "En pesos: objetivo bajista (−18,6%)."}]
ids = {x.get("id") for x in it.get("alertas") or []}
it.setdefault("alertas", []).extend(x for x in nuevas if x["id"] not in ids)
a.put("usuario/lista", lista)
print("::notice::" + json.dumps(it, ensure_ascii=False)[:2500])
