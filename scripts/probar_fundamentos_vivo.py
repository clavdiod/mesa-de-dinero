"""Carga los fundamentos de los CEDEARs que sigue la mesa (SEC + Yahoo) y muestra algunos."""
from datetime import date
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
from mesa.agentes import fundamentos as fu
a = almacen_por_defecto()
uni = _universo_cedears(a)
tabla = fu.actualizar(a, uni, date.today(), maximo=100)
ok = [t for t in uni if fu.de(a, t)]
print(f"::notice::{len(ok)} de {len(uni)} CEDEARs con fundamentos")
for t in [x for x in ("AAPL", "NVDA", "MELI", "KO", "XOM", "IREN", "LRCX") if x in ok][:7]:
    print(f"::notice::{t}: {fu.frase(fu.de(a, t))}")
