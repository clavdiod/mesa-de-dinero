"""LRCX: compra real del usuario el 26/10 a $7.050 (otro broker). Aprueba la propuesta del Jefe con su precio real
y deja alertas en pesos: +1R (subir el stop), objetivo y stop."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
cart = [x for x in (a.get("usuario/cartera") or []) if str(x.get("ticker", "")).upper() == "LRCX"]
print("::notice::CARTERA " + json.dumps(cart, ensure_ascii=False))
props = a.get("registro/propuestas") or []
p = next((x for x in reversed(props) if x["ticker"] == "LRCX" and x["fecha"] == "2026-10-26"), None)
if p:
    p["decision"] = "aprobada"
    p["plan"]["entrada_plan"] = p["plan"]["entrada"]
    p["plan"]["entrada"] = 7050.0
    p["seguimiento"].update(estado="abierta", fecha_entrada="2026-10-26", precio_entrada=7050.0)
    p["seguimiento"].pop("consejo", None)
    a.put("registro/propuestas", props)
    print("::notice::PROPUESTA " + json.dumps({k: p.get(k) for k in ("decision", "plan", "seguimiento")}, ensure_ascii=False))
lista = a.get("usuario/lista") or []
it = next((x for x in lista if x.get("ticker") == "LRCX"), None)
if not it:
    it = {"ticker": "LRCX", "precio": 7050, "nota": "Compra 26/10 a $7.050 (propuesta del Jefe)"}
    lista.append(it)
nuevas = [{"id": "lrcx-sube-8045", "tipo": "sube", "nivel": 8045, "moneda": "ARS", "creada": "2026-10-26", "nota": "+1R: subí el stop a tu precio de compra ($7.050)."},
          {"id": "lrcx-sube-9231", "tipo": "sube", "nivel": 9231, "moneda": "ARS", "creada": "2026-10-26", "nota": "Objetivo del plan (+30,9%): vender."},
          {"id": "lrcx-baja-6450", "tipo": "baja", "nivel": 6450, "moneda": "ARS", "creada": "2026-10-26", "nota": "Ojo: cerca del stop (−8,5%)."},
          {"id": "lrcx-baja-6055", "tipo": "baja", "nivel": 6055, "moneda": "ARS", "creada": "2026-10-26", "nota": "Stop del plan (−14,1%): salir."}]
ids = {x.get("id") for x in it.get("alertas") or []}
it.setdefault("alertas", []).extend(x for x in nuevas if x["id"] not in ids)
a.put("usuario/lista", lista)
print("::notice::LISTA " + json.dumps(it, ensure_ascii=False)[:1500])
