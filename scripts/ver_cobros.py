"""Diagnóstico de cobros: cartera, flujos encontrados y lo que muestra la app."""
from datetime import date

from mesa.datos import cobros as c
from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
print("::notice::CARTERA " + str(cart)[:1500])
guard = a.get("cobros/flujos") or {}
print("::notice::FLUJOS GUARDADOS " + " | ".join(f"{k}: {len(v.get('flujos') or [])} pagos {'(sin datos)' if v.get('sin_datos') else ''} bajado {v.get('bajado')}" for k, v in guard.items())[:1500])
for x in cart:
    tk = x["ticker"].upper()
    if tk not in guard or guard[tk].get("sin_datos"):
        f = c.flujos_mae(tk)
        print(f"::notice::PRUEBA {tk}: candidatos {c.candidatos(tk)} -> {'OK ' + str(len(f['flujos'])) + ' pagos ' + str(f.get('descripcion')) if f else 'nada'}")
est = a.get("ui/estado") or {}
print("::notice::ESTADO hora " + str(est.get("hora")) + " cobros " + str(len(est.get("cobros") or [])) + " flujos_bonos " + str(list((est.get("flujos_bonos") or {}).keys())))
