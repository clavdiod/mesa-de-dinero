from mesa.nucleo.almacen import almacen_por_defecto
from mesa.agentes import biblioteca as B
from mesa.agentes.fundamentos import _ciks
a = almacen_por_defecto(); t = a.get(B.CLAVE) or {}
print(f"::notice::tabla {len(t)} · con calidad {sum(1 for v in t.values() if v.get('calidad'))} · fechas {sorted({v.get('sec_fecha') for v in t.values()})[-3:]}")
c = _ciks(); s = B.datos_sec(c["AAPL"])
print(f"::notice::AAPL ebit {s.get('ebit', [])[-2:]} ppe {s.get('ppe', [])[-1:]} calidad {B.evaluar_calidad(s, 230, ticker='AAPL')}")
