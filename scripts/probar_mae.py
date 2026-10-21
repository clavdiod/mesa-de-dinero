"""Qué segmento/tipo de operación tiene cada fila del histórico (para descartar las que no son de mercado)."""
from collections import Counter
from datetime import date, timedelta

from mesa.datos.gratis import mae_cierres, mae_panel_rf

hoy = date.today()
h = mae_cierres(hoy - timedelta(days=1), hoy)
c = Counter((r.get("codsegmento"), r.get("tipoOpera"), r.get("tipoOperacionDesc"), r.get("tipoCierreDesc")) for r in h)
print("::notice::TIPOS " + " | ".join(f"{k}: {v}" for k, v in c.most_common(20))[:3900])
out = [f"{r['codTitulo']} {r['moneda']} pl{r['plazo']} {r['precioCierre']} vol {r['volumen']:.0f} seg {r.get('codsegmento')} op {r.get('tipoOpera')} {r.get('tipoOperacionDesc')} {r.get('tipoCierreDesc')} {r.get('tipoEmision')}"
       for r in h if r["codTitulo"].strip() in ("AE38", "D30O6", "S13N6") and r["fecha"][:10] == hoy.isoformat()]
print("::notice::FILAS " + " | ".join(out)[:3900])
p = mae_panel_rf()
cp = Counter((r.get("codigoSegmento"), r.get("segmento")) for r in p)
print("::notice::PANEL " + str(cp.most_common()) + " || " + " | ".join(f"{r['ticker']} {r['moneda']} pl{r['plazo']} {r['ultimo']} {r['segmento']}" for r in p if r["ticker"].strip() in ("AE38", "D30O6", "S13N6")))
