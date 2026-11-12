from mesa.datos.gratis import _S
for u in ["https://api.bcra.gob.ar/estadisticas/v3.0/monetarias", "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias",
          "https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones"]:
    try:
        r = _S.get(u, timeout=30, verify=False)
        print(f"::notice::{u} → {r.status_code} {r.text[:1500]}")
    except Exception as ex:
        print(f"::notice::{u} ERR {ex}")
