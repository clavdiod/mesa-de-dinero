"""20/11: Clau: "calculá un millón en total… entre 5 y 8 de pérdida". Capital de la mesa $1.000.000; cada idea arriesga
como mucho 1,5% ($15.000) si toca la alarma, así con 5 ideas abiertas a la vez la pérdida máxima total queda en ~7,5%."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
cap = a.get("usuario/capital") or {}
cap = cap if isinstance(cap, dict) else {}
cap.update(monto_ars=1_000_000, riesgo_pct=1.5, max_ideas_abiertas=5, tope_posicion_pct=25,
           nota="20/11: $1M en total; pérdida máxima total 5-8% (~$75.000): 1,5% por idea, hasta 5 ideas a la vez")
a.put("usuario/capital", cap)
print("::notice::" + json.dumps(cap, ensure_ascii=False))
