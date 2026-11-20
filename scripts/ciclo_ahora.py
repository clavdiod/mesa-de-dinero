from datetime import date
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.agentes import ciclo
a = almacen_por_defecto(); t = ciclo.medir(date.today()); a.put(ciclo.CLAVE, t)
print("::notice::" + str(t))
