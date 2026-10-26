import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
print("::notice::" + json.dumps(a.get("usuario/cartera"), ensure_ascii=False)[:3000])
