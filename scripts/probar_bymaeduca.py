from datetime import date
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos import bymaeduca as be
from mesa.datos.eventos import _flujos_yaml
a = almacen_por_defecto()
print("BE| " + str(be.actualizar(a)))
fl = be.flujos_guardados(a)
y = _flujos_yaml()
hoy = "2026-11-16"
for tk in ("GD30", "AL30", "AO29", "AO28", "AN29", "AE38", "GD46"):
    b = [f for f in (fl.get(tk) or {}).get("flujos", []) if f["fecha"] > hoy]
    m = [f for f in (y.get(tk) or {}).get("flujos", []) if f["fecha"] > hoy]
    sb = (round(sum(f["interes"] + f["amortizacion"] for f in b), 2), len(b))
    sm = (round(sum(f["interes"] + f["amortizacion"] for f in m), 2), len(m))
    print(f"BE| {tk}: BYMA {sb} · a mano {sm} · {'IGUAL' if abs(sb[0] - sm[0]) < 0.5 and sb[1] == sm[1] else 'DISTINTO'} · TIR {(fl.get(tk) or {}).get('tir')} par {(fl.get(tk) or {}).get('paridad')}")
cart = [str(c.get("ticker")).upper() for c in a.get("usuario/cartera") or []] + ["AO29D"]
print("BE| tu cartera: " + ", ".join(f"{t}={'sí' if (fl.get(t) or {}).get('flujos') else 'NO'}" for t in cart))
div = (a.get("bymaeduca/dividendos") or {}).get("filas") or []
ult = [d for d in div if (d.get("fecha") or "") >= "2025-11-16"]
por = {}
for d in ult:
    por[d["ticker"]] = por.get(d["ticker"], 0) + (d.get("por_accion_usd") or 0)
print(f"BE| dividendos: {len(div)} desde {min(d['fecha'] for d in div)} · último año {len(ult)} pagos de {len(por)} empresas: " + ", ".join(f"{k} US${v:.3f}" for k, v in sorted(por.items(), key=lambda x: -x[1])[:15]))
