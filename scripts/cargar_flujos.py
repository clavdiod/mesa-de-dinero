"""SXC3O (ON de Mercado Libre, TAMAR + 3,5%): el ticker estaba cargado como SCX3O. Flujo de Bull Market (82.703 nominales)."""
from mesa.nucleo.almacen import almacen_por_defecto

vn = 82703
filas = [("2026-11-23", 5681.70, 0), ("2027-02-23", 5681.70, 82703)]
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
for x in cart:
    if x.get("ticker", "").upper() == "SCX3O":
        x["ticker"] = "SXC3O"
a.put("usuario/cartera", cart)
ons = a.get("usuario/ons") or {}
ons["SXC3O"] = {"emisor": "ON Mercado Libre (TAMAR + 3,5%) · fuente Bull Market (renta estimada)", "moneda": "ARS", "lamina_minima": 1,
                "flujos": [{"fecha": f, "interes": round(r / vn * 100, 6), "amortizacion": round(am / vn * 100, 6)} for f, r, am in filas]}
a.put("usuario/ons", ons)
print("::notice::" + str([x["ticker"] for x in cart]) + " || SXC3O " + str(ons["SXC3O"]["flujos"]))
