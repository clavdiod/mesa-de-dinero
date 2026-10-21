"""Carga inicial del histórico propio de MAE (bonos, ONs, letras) y comparación de hoy con BYMA."""
from datetime import date, timedelta

from mesa.agentes import mae
from mesa.datos.gratis import mae_cierres
from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
panel = (a.get("ui/panel") or {}).get("titulos") or {}
hoy = date.today()
for anio in (str(hoy.year - 1), str(hoy.year)):
    a.put(f"mae/hist/{anio}", {})
a.put("mae/indice", [])
rows, d = [], hoy - timedelta(days=400)
while d <= hoy:
    h = min(d + timedelta(days=30), hoy)
    try:
        x = mae_cierres(d, h)
        rows += x
    except Exception as e:
        print(f"[mae] {d}: {e}")
    d = h + timedelta(days=1)
n = mae.guardar_historico(a, rows, set(panel))
idx = a.get("mae/indice") or []
fechas = sorted({r["fecha"][:10] for r in rows})
# comparación de cierres de hoy contra nuestro panel (última ronda)
tit = {tk: {"ultimo": x[0], "grupo": x[4], "volumen": 1, "simbolo": tk} for tk, x in panel.items() if x[4] in mae.GRUPOS_RF and x[0]}
pares = mae.comparar(tit, [{**r, "monto": r.get("volumen")} for r in rows if r["fecha"][:10] == hoy.isoformat()])
if pares:
    a.put("mae/comparacion", {"dias": [{"fecha": hoy.isoformat(), "resumen": mae.resumen(pares), "mayores": [p for p in pares if p["liquido"]][:8]}]})
print(f"::notice::{len(rows)} filas, {fechas[0] if fechas else '-'} a {fechas[-1] if fechas else '-'}, {n} cierres guardados, "
      f"{len(idx)} papeles con historia suficiente || hoy: {mae.resumen(pares)} || mayores: "
      + " | ".join(f"{p['ticker']} {p['dif']:+.2f}%" for p in pares if p['liquido'])[:2500])
