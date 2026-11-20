"""20/11: la simulación en papel da 12% ganadoras: demasiado bajo. ¿Por qué se cierran las operaciones?"""
import json
from collections import Counter
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
cer = a.get("sim/cerradas") or a.get("sim/historial") or []
print(f"::notice::claves sim: {[k for k in ('sim/cerradas', 'sim/historial', 'sim/posiciones', 'sim/resumen') if a.get(k) is not None]} · cerradas {len(cer)}")
if cer:
    print("::notice::motivos " + str(Counter(str(x.get('motivo') or x.get('estado') or x.get('salida_motivo')) for x in cer).most_common(8)))
    for x in cer[:6]:
        print("::notice::EJ " + json.dumps(x, ensure_ascii=False, default=str)[:500])
pos = a.get("sim/posiciones") or []
print("::notice::POS ej " + json.dumps(pos[:2] if isinstance(pos, list) else list(pos.items())[:2], ensure_ascii=False, default=str)[:900])
