"""Arma el seguimiento de la cartera con lo de la última ronda y lo pone en la app (sin esperar a mañana)."""
import json
from mesa.agentes import seguimiento_cartera as sc
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.registro import Registro
from mesa.nucleo.reloj import ahora
a = almacen_por_defecto()
est = a.get("ui/estado") or {}
hoy = ahora().date()
seg, av = sc.armar(a.get("usuario/cartera") or [], est.get("proyeccion_cartera") or {}, est.get("opinion_cartera") or {},
                   Registro(a).propuestas, a.get("pronosticos/libreta") or [], {}, {}, hoy, est.get("hora") or "")
est["seguimiento_cartera"] = seg
a.put("ui/estado", est)
for tk, g in seg.items():
    print(f"::notice::{tk} día {g['dias']}/{g['total']} vence {g['vence']} ({g['plazo_motivo']}) sug {g['sugerida']} | {g['por_que']} | " + " / ".join(o["texto"] for o in g["opciones"]))
