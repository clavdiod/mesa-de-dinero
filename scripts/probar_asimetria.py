from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.reloj import ahora
from mesa.agentes import asimetria as asi
from mesa.datos.eventos import flujos_bonos
a = almacen_por_defecto()
pan = (a.get("ui/panel") or {}).get("titulos") or {}
r = asi.tabla(pan, flujos_bonos(), ahora().date(), {str(c.get("ticker") or "").upper() for c in a.get("usuario/cartera") or []})
print("::notice::" + r["resumen"])
print("::notice::" + " | ".join(f"{f['ticker']}({f['dolar']}) {f['precio']} par {f['paridad']}%: {f['escenarios']['pesimista']}/{f['escenarios']['reestructuracion']}/{f['escenarios']['optimista']} → {f['ratio']}" for f in sorted(r["filas"], key=lambda f: -(f["ratio"] or 0))))
