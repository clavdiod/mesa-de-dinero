"""Escala de precios: histórico vs panel de MAE, en pesos y dólares."""
from datetime import date, timedelta

from mesa.datos.gratis import mae_cierres, mae_panel_rf

hoy = date.today()
h = mae_cierres(hoy - timedelta(days=1), hoy)
p = mae_panel_rf()
quiero = ("AL30", "GD30", "AE38", "S13N6", "D30O6", "YM44O", "PNRCO", "TZXO6", "T661O")
out = []
for r in h:
    if r["codTitulo"].strip() in quiero:
        out.append(f"H {r['fecha'][:10]} {r['codTitulo']} {r['moneda']} pl{r['plazo']} cierre {r['precioCierre']} vol {r['volumen']} cant {r['cantidad']}")
for r in p:
    if r["ticker"].strip() in quiero:
        out.append(f"P {r['ticker']} {r['moneda']} pl{r['plazo']} ult {r['ultimo']} monto {r.get('monto')} vol {r.get('volumen')}")
print("::notice::" + " | ".join(out)[:3900])
