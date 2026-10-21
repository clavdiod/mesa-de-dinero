"""Prueba variantes de historial de IOL para un CEDEAR (pocas consultas). No imprime secretos."""
from datetime import timedelta

from mesa.datos.consumo import Consumo
from mesa.datos.iol import IOL
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.reloj import ahora

a = almacen_por_defecto()
consumo = Consumo(a)
iol = IOL(consumo, almacen=a)
hasta = ahora().date() - timedelta(days=1)
out = []
for tk, merc, aj, dias in (("AAPL", "bCBA", False, 400), ("AAPL", "bCBA", True, 60), ("KO", "bCBA", False, 400), ("AAPL", "BCBA", True, 400)):
    try:
        v = iol.historial(tk, hasta - timedelta(days=dias), hasta, mercado=merc, ajustada=aj)
        out.append(f"{tk}/{merc}/{'aj' if aj else 'sin'}/{dias}d: {len(v)}")
    except Exception as e:
        out.append(f"{tk}/{merc}/{aj}: ERROR {type(e).__name__}: {str(e)[:120]}")
consumo.guardar()
print("::notice::" + " | ".join(out))
