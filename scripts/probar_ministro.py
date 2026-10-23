"""Datos de política económica gratis: BCRA (reservas, compras, tasas, base) y Tesoro."""
import requests

out = []
for u in ("https://api.bcra.gob.ar/estadisticas/v3.0/monetarias", "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias"):
    try:
        r = requests.get(u, timeout=30, headers={"Accept-Language": "es-AR"})
        j = r.json()
        res = j.get("results") or []
        out.append(f"{u[-20:]} {r.status_code} {len(res)} vars: " + " | ".join(f"{x.get('idVariable')}={(x.get('descripcion') or '')[:55]} ({x.get('fecha') or x.get('ultFechaInformada')}: {x.get('valor') or x.get('ultValorInformado')})" for x in res[:45]))
    except Exception as e:
        out.append(f"{u} ERROR {e}")
for i in range(0, len(out)):
    print("::notice::" + out[i][:3900])
