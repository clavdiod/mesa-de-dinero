"""Formato de avisos de pago y resultados; alcance del histórico."""
import json
from datetime import date, timedelta

import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
B = "https://api.marketdata.mae.com.ar/api/"
p = requests.get(B + "mercado/pagoamortizrenta", headers=H, timeout=30).json()
print("::notice::PAGOS " + str(len(p)) + " " + p[-1]["fecha"][:10] + " a " + p[0]["fecha"][:10] + " || " + " | ".join(f"{x['fecha'][:10]} {x.get('empresa')}: {x['titulo']}" for x in p[:25])[:3800])
r = requests.get(B + "mercado/boletin-mpmae", headers=H, timeout=30).json()
print("::notice::BOLETIN " + str(len(r)) + " || " + " | ".join(f"{x['fecha'][:10]} {x['titulo']}" for x in r[:25])[:3800])
q = lambda o: json.dumps(o, separators=(",", ":"))
for dias in (60, 400, 1500):
    d = date.today() - timedelta(days=dias)
    x = requests.get(B + f"mercado/historico/preciocierre?oTitulo={q({'fechaDesde': d.isoformat(), 'fechaHasta': (d + timedelta(days=3)).isoformat()})}", headers=H, timeout=60)
    j = x.json() if x.status_code == 200 else []
    print(f"::notice::HIST hace {dias} días: {x.status_code} {len(j)} filas {len(x.content)} bytes " + (json.dumps(j[0])[:200] if j else ""))
x = requests.get(B + f"mercado/historico/preciocierre?oTitulo={q({'fechaDesde': (date.today() - timedelta(days=31)).isoformat(), 'fechaHasta': date.today().isoformat()})}", headers=H, timeout=90)
print(f"::notice::HIST 31 días: {x.status_code} {len(x.content)} bytes {len(x.json()) if x.status_code == 200 else 0} filas")
x = requests.get(B + f"mercado/historico/preciocierre?oTitulo={q({'fechaDesde': (date.today() - timedelta(days=5)).isoformat(), 'fechaHasta': date.today().isoformat(), 'codTitulo': 'AL30'})}", headers=H, timeout=60)
print(f"::notice::HIST filtro AL30: {x.status_code} {len(x.json()) if x.status_code == 200 else 0} filas")
