import json
from mesa.datos import cobros
from mesa.datos.gratis import _S
for c in ["S13N6", "S30N6", "S29E7", "T15E7", "T30A7", "T30J7", "T31Y7", "TTM26", "TTD26"]:
    try:
        j = _S.get(cobros._MAE + f"emisiones/flujofondos/{c}", headers=cobros._H, timeout=20).json()
        print(f"::notice::{c}: {j.get('moneda')} {j.get('descripcion')} tir {j.get('tir')} precio {j.get('precio')} | " + json.dumps(j.get("detalle"))[:300])
    except Exception as ex:
        print(f"::notice::{c} ERR {ex}")
