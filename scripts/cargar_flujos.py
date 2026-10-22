"""BAF27 (Municipalidad de Córdoba, TAMAR + 5,5%): flujo de Bull Market que pasó el usuario (3.907.607 nominales), pasado a cada 100."""
from mesa.nucleo.almacen import almacen_por_defecto

vn = 3907607
filas = [("2026-11-13", 95345.61, 0), ("2026-12-13", 95345.61, 976901.75), ("2027-01-13", 71509.21, 976901.75), ("2027-02-13", 47672.81, 1953803.50)]
a = almacen_por_defecto()
ons = a.get("usuario/ons") or {}
ons["BAF27"] = {"emisor": "Municipalidad de Córdoba S.2 (TAMAR + 5,5%) · fuente Bull Market (renta estimada)", "moneda": "ARS", "lamina_minima": 1,
                "flujos": [{"fecha": f, "interes": round(r / vn * 100, 6), "amortizacion": round(am / vn * 100, 6)} for f, r, am in filas]}
a.put("usuario/ons", ons)
print("::notice::BAF27 " + str(ons["BAF27"]["flujos"]))
