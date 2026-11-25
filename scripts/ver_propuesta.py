"""Ver el plan de la mesa para un papel (solo lectura). Uso: cambiar TK. Solo imprime ese papel."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
TK = "METR"
a = almacen_por_defecto()
for p in (a.get("registro/propuestas") or []):
    if str(p.get("ticker", "")).upper() == TK and p.get("fecha", "") >= "2026-11-20":
        print(f"::notice::{p.get('fecha')} {p.get('hora')} linea={p.get('linea')} meses={p.get('meses')} decision={p.get('decision')} "
              f"precio_al_proponer={p.get('precio_al_proponer')} cant={p.get('cantidad_sugerida')} monto={p.get('monto_sugerido')} "
              f"plan={json.dumps(p.get('plan'))} frio={(p.get('ficha_frio') or {}).get('veredicto')} ranking={json.dumps(p.get('ranking'))[:200]}")
        print("::notice::por qué: " + str(p.get("resumen_jefe") or "")[:600])
pan = (a.get("ui/panel") or {}).get("titulos", {}).get(TK)
print(f"::notice::panel {(a.get('ui/panel') or {}).get('hora')} {TK}={pan}")
