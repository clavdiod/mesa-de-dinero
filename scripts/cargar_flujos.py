"""Carga en usuario/ons los flujos que no publica MAE (sacados de IOL el 22/10/2026, cada 100 nominales)."""
import json

from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
ons = a.get("usuario/ons") or {}
fechas_ao27 = ["2026-10-31", "2026-11-30", "2026-12-31", "2027-01-31", "2027-02-28", "2027-03-31", "2027-04-30", "2027-05-31",
               "2027-06-30", "2027-07-31", "2027-08-31", "2027-09-30"]
nuevos = {
    "AO27": {"emisor": "Tesoro Nacional (Bonar 2027, renta mensual 6% anual) · fuente IOL", "moneda": "USD", "lamina_minima": 1,
             "flujos": [{"fecha": f, "interes": 0.5, "amortizacion": 0} for f in fechas_ao27] + [{"fecha": "2027-10-29", "interes": 0.5, "amortizacion": 100}]},
    "T661O": {"emisor": "ON T661O · fuente IOL (renta estimada: tasa variable)", "moneda": "ARS", "lamina_minima": 1,
              "flujos": [{"fecha": "2026-11-30", "interes": 1.25, "amortizacion": 100}]},
    "RVS1O": {"emisor": "ON RVS1O · fuente IOL (renta estimada: tasa variable)", "moneda": "ARS", "lamina_minima": 1,
              "flujos": [{"fecha": "2026-11-27", "interes": 1.25, "amortizacion": 0}, {"fecha": "2027-02-27", "interes": 1.25, "amortizacion": 100}]},
}
for k, v in nuevos.items():
    ons.setdefault(k, v)
a.put("usuario/ons", ons)
print("::notice::ONs cargadas: " + ", ".join(ons))
