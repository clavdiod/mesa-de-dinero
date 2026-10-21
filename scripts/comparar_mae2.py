"""Cierres diarios: MAE (histórico de precios de cierre) contra nuestro historial de BYMA (cache)."""
import json
import statistics as st
from datetime import date, timedelta

import requests

from mesa.datos.cache import CacheHistorico
from mesa.nucleo.almacen import almacen_por_defecto

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
B = "https://api.marketdata.mae.com.ar/api/"
hoy = date.today()
o = json.dumps({"fechaDesde": (hoy - timedelta(days=12)).isoformat(), "fechaHasta": hoy.isoformat()}, separators=(",", ":"))
filas = requests.get(B + f"mercado/historico/preciocierre?oTitulo={o}", headers=H, timeout=60).json()
print("::notice::EJ " + json.dumps(filas[0])[:600] + f" || {len(filas)} filas")
a = almacen_por_defecto()
c = CacheHistorico(a)
panel = (a.get("ui/panel") or {}).get("titulos") or {}
dif, ej = {}, []
for f in filas:
    tk, mon, pc = f["codTitulo"].strip(), f.get("moneda"), f.get("precioCierre")
    if not pc or f.get("plazo") not in ("000", "001"):
        continue
    nuestro_tk = tk + ("D" if mon == "D" else "C" if mon == "C" else "")
    if nuestro_tk not in panel:
        continue
    vs = {v["fecha"]: v["cierre"] for v in c.velas(nuestro_tk)}
    fe = f["fecha"][:10]
    if fe not in vs or not vs[fe]:
        continue
    for esc in (1, 100):
        d = (pc * esc / vs[fe] - 1) * 100
        if abs(d) < 20:
            g = panel[nuestro_tk][4]
            dif.setdefault(g, []).append((abs(d), f.get("volumen") or 0))
            ej.append((round(d, 2), nuestro_tk, fe, f.get("plazo"), pc * esc, vs[fe], f.get("volumen") or 0, f.get("cantidad") or 0))
            break
res = {}
for g, v in dif.items():
    x = sorted(d for d, _ in v)
    grandes = sorted(d for d, vol in v if vol >= 50_000_000)
    res[g] = (f"n={len(x)} mediana {st.median(x):.2f}% p90 {x[int(len(x) * .9)]:.2f}% · con volumen MAE>=50M: n={len(grandes)} "
              + (f"mediana {st.median(grandes):.2f}%" if grandes else ""))
print("::notice::RESUMEN " + str(res))
ej.sort(key=lambda e: -abs(e[0]))
print("::notice::MAYORES " + " | ".join(f"{t} {fe} pl{p} MAE {m:.2f} BYMA {b:.2f} {d:+.2f}% vol {v:,.0f}" for d, t, fe, p, m, b, v, _ in ej[:20])[:3900])
