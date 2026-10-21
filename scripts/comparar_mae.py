"""Compara precios de renta fija: MAE contra nuestro panel (BYMA vía IOL / data912)."""
import json
import statistics as st

import requests

from mesa.nucleo.almacen import almacen_por_defecto

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
B = "https://api.marketdata.mae.com.ar/api/"
mae = requests.get(B + "mercado/datos/RF", headers=H, timeout=30).json()
panel = (almacen_por_defecto().get("ui/panel") or {})
tit = panel.get("titulos") or {}
print("::notice::EJEMPLO MAE " + json.dumps(mae[0])[:900] + " || panel " + str(panel.get("fecha")) + " " + str(panel.get("hora")) + f" ({len(tit)} títulos)")
seg = {}
for m in mae:
    seg[(m.get("codigoSegmento"), m.get("plazo"), m.get("moneda"))] = seg.get((m.get("codigoSegmento"), m.get("plazo"), m.get("moneda")), 0) + 1
print("::notice::SEGMENTOS " + str(seg))
filas = []
for m in mae:
    tk, mon, ult = m["ticker"].strip(), m.get("moneda"), m.get("ultimo")
    if not ult:
        continue
    cand = [tk + "D", tk + "C"] if mon == "D" else [tk + "C"] if mon == "C" else [tk]
    for c in cand:
        if c in tit and tit[c][0]:
            ours = tit[c][0]
            for esc in (1, 100):
                d = (ult * esc / ours - 1) * 100
                if abs(d) < 15:
                    filas.append((round(d, 2), c, tit[c][4], ult * esc, ours, m.get("plazo"), m.get("codigoSegmento"), m.get("monto") or 0))
                    break
            break
filas.sort(key=lambda f: -abs(f[0]))
grupos = {}
for f in filas:
    grupos.setdefault(f[2], []).append(abs(f[0]))
res = {g: f"n={len(v)} mediana {st.median(v):.2f}% p90 {sorted(v)[int(len(v) * .9)]:.2f}%" for g, v in grupos.items()}
print("::notice::RESUMEN " + str(res) + f" || pareados {len(filas)}")
print("::notice::MAYORES " + " | ".join(f"{c}({g}) MAE {a:.2f} vs nuestro {b:.2f} = {d:+.2f}% plazo {p} seg {s} monto {mo:,.0f}" for d, c, g, a, b, p, s, mo in filas[:22])[:3900])
