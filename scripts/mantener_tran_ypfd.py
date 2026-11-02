"""02/11: Clau decide mantener TRAN e YPFD.
YPFD: pasa a largo plazo (1 año): se cierra el seguimiento del plan del Comité (stop 7.470) y queda una alarma de revisión en 6.100.
TRAN: el plazo de la idea de 1 semana se estira a 20 ruedas (como el Anticipador ARG nuevo), con la alarma en 1.960."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
props = a.get("registro/propuestas") or []
for p in props:
    if p["ticker"] == "YPFD" and (p.get("seguimiento") or {}).get("estado") == "abierta":
        p["seguimiento"]["estado"] = "largo_plazo"
        p["seguimiento"]["nota"] = "Clau la pasó a largo plazo el 02/11 (tocó el stop de 7.470 del plan de 20 ruedas)."
a.put("registro/propuestas", props)
cart = a.get("usuario/cartera") or []
for c in cart:
    if c.get("ticker") == "YPFD":
        c["vence"] = "2027-11-02"; c["plazo_motivo"] = "largo plazo (decisión del 02/11): se revisa si cae a 6.100"
        c["alertas"] = [{"tipo": "baja", "nivel": 6100.0, "moneda": "ARS", "nota": "stop de revisión de largo plazo (-25%): algo grave pasó, revisar la tesis"}]
    if c.get("ticker") == "TRAN":
        c["vence"] = "2026-11-26"; c["plazo_motivo"] = "estirado a 20 ruedas el 02/11 (decisión de Clau)"
        c["alertas"] = [x for x in (c.get("alertas") or []) if "stop" not in str(x.get("nota", "")).lower()] + \
                       [{"tipo": "baja", "nivel": 1960.3, "moneda": "ARS", "nota": "stop del plan (Anticipador ARG)"}]
a.put("usuario/cartera", cart)
dec = a.get("usuario/decisiones_cartera") or {}
dec = dec if isinstance(dec, dict) else {}
for tk in ("YPFD", "TRAN"):
    dec[tk] = {"fecha": "2026-11-02", "accion": "mantener", "sugerida": None, "detalle": "Clau decide mantener"}
a.put("usuario/decisiones_cartera", dec)
av = a.get("cartera/avisados") or {}
av.pop("YPFD", None); a.put("cartera/avisados", av)
print("::notice::" + json.dumps([c for c in cart if c.get("ticker") in ("YPFD", "TRAN")], ensure_ascii=False)[:900])
