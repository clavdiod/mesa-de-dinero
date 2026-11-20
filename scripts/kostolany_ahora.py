from datetime import date
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos.cache import CacheHistorico
from mesa.agentes import posiciones as P
a = almacen_por_defecto(); r = P.preparar_kostolany(a, CacheHistorico(a), date.today())
print("::notice::PANICO " + " | ".join(f"{x['ticker']} ({x['mercado']}) {x['r20']}% vol x{x['vol']}" for x in r["lista"][:40]))
