"""Estado de la libreta de pronósticos."""
from mesa.nucleo import pronosticos as pr
from mesa.nucleo.almacen import almacen_por_defecto

lib = almacen_por_defecto().get("pronosticos/libreta") or []
print("::notice::" + f"{len(lib)} pronósticos || {pr.resumen(lib)} || " + " | ".join(
    f"{x['origen']} {x['ticker']} {x['estado']} ref {x.get('ref')} va {x.get('ahora_pct')}% mejor {x.get('mejor')}" for x in lib[:25])[:3500])
