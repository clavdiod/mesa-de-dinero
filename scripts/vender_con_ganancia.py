"""12/11: Clau decide esperar y vender TRAN, CEPU e YPFD solo con ganancia ('no tengo urgencia').
Precio de salida = compra +3,2% (1,2% de comisiones de ida y vuelta + ~2% de ganancia neta). Sin plazo corto.
La alarma de abajo deja de ser 'vendé' y pasa a ser de revisión (-25% de la compra): si llega ahí, algo grave cambió."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
out = []
for c in cart:
    tk = str(c.get("ticker", "")).upper()
    if tk not in ("TRAN", "CEPU", "YPFD"):
        continue
    compra = float(c["precio"])
    salida = round(compra * 1.032 / 5) * 5
    revision = round(compra * 0.75 / 5) * 5
    c["vence"] = "2027-11-12"
    c["plazo_motivo"] = f"esperar para vender con ganancia (decisión del 12/11): salida en {salida}"
    c["objetivo_usuario"] = salida
    c["alertas"] = [
        {"id": f"salida-{tk}-1211", "tipo": "sube", "nivel": float(salida), "moneda": "ARS", "creada": "2026-11-12",
         "nota": f"💰 Llegó a tu precio de salida con ganancia: vendé {c.get('cantidad')} (compraste a {compra:g}; ganancia neta ~2% después de comisiones)."},
        {"id": f"revision-{tk}-1211", "tipo": "baja", "nivel": float(revision), "moneda": "ARS", "creada": "2026-11-12",
         "nota": "Alarma de revisión (-25% de tu compra): algo grave pasó, revisemos si conviene seguir esperando."}]
    out.append(f"{tk}: compra {compra:g} · salida {salida} · revisión {revision} · cantidad {c.get('cantidad')}")
a.put("usuario/cartera", cart)
dec = a.get("usuario/decisiones_cartera") or {}
dec = dec if isinstance(dec, dict) else {}
for tk in ("TRAN", "CEPU", "YPFD"):
    dec[tk] = {"fecha": "2026-11-12", "accion": "mantener", "sugerida": None, "detalle": "Clau espera vender con ganancia"}
a.put("usuario/decisiones_cartera", dec)
av = a.get("cartera/avisados") or {}
for tk in ("TRAN", "CEPU", "YPFD"):
    av.pop(tk, None)
a.put("cartera/avisados", av)
print("::notice::" + " | ".join(out))
