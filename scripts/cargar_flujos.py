"""PR17 (Bocon serie 10): 11 cuotas trimestrales del 2/11/2026 al 2/5/2029, cada 100 nominales originales.
Datos que pasó el usuario (Google / Docta Capital): próxima cuota 96,98 y total 962,65. Se reparte con amortización
fija e interés Badlar sobre el saldo (estimado: el interés real depende de la Badlar de cada trimestre)."""
from mesa.nucleo.almacen import almacen_por_defecto

fechas = ["2026-11-02", "2027-02-02", "2027-05-02", "2027-08-02", "2027-11-02", "2028-02-02", "2028-05-02",
          "2028-08-02", "2028-11-02", "2029-02-02", "2029-05-02"]
primera, total, n = 96.98, 962.65, 11
# cuota_k = A + r·A·(n−k+1): con primera y total se despejan A (amortización) y r (interés trimestral sobre el saldo)
s = n * (n + 1) / 2
r = (total / primera - n) / (s - (total / primera) * n)
A = primera / (1 + n * r)
flujos = [{"fecha": f, "interes": round(r * A * (n - k), 4), "amortizacion": round(A, 4)} for k, f in enumerate(fechas)]
a = almacen_por_defecto()
ons = a.get("usuario/ons") or {}
ons["PR17"] = {"emisor": "Bono de Consolidación serie 10 (Badlar) · estimado con datos de Docta Capital", "moneda": "ARS", "lamina_minima": 1,
               "flujos": flujos}
a.put("usuario/ons", ons)
print("::notice::" + f"r={r:.5f} A={A:.4f} primera={flujos[0]['interes'] + A:.2f} total={sum(f['interes'] + f['amortizacion'] for f in flujos):.2f} "
      + " | ".join(f"{f['fecha']} {f['interes'] + f['amortizacion']:.2f}" for f in flujos))
