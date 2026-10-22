"""BAO27 (Municipalidad de Córdoba, deuda proveedores 2025 S1, TAMAR): flujo de Bull Market que pasó el usuario (1.084.872 nominales)."""
from mesa.nucleo.almacen import almacen_por_defecto

vn = 1084872
filas = [("2027-02-01", 85596.40, 0), ("2027-06-01", 85596.40, 0), ("2027-10-01", 85596.40, 1084872)]
a = almacen_por_defecto()
ons = a.get("usuario/ons") or {}
ons["BAO27"] = {"emisor": "Municipalidad de Córdoba deuda proveedores 2025 S.1 (TAMAR) · fuente Bull Market (renta estimada)", "moneda": "ARS",
                "lamina_minima": 1, "flujos": [{"fecha": f, "interes": round(r / vn * 100, 6), "amortizacion": round(am / vn * 100, 6)} for f, r, am in filas]}
a.put("usuario/ons", ons)
print("::notice::BAO27 " + str(ons["BAO27"]["flujos"]) + " || ONs: " + ", ".join(ons))
