"""13/11: NVDA a Mi lista (renuncia de Huang, resultados el 17/11). Avisos en dólares (precio de EE.UU.)."""
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
lista = a.get("usuario/lista") or []
lista = [x for x in lista if str((x.get("ticker") if isinstance(x, dict) else x) or "").upper() != "NVDA"]
lista.append({"ticker": "NVDA", "agregado": "2026-11-13", "nota": "Mínimo del año tras la renuncia de Jensen Huang (12/11). Esperar los resultados del 17/11 antes de entrar.",
              "alertas": [
                  {"id": "nvda-sube-1311", "tipo": "sube", "nivel": 175.0, "moneda": "USD", "creada": "2026-11-13",
                   "nota": "NVIDIA rebota fuerte (+9% desde el mínimo): revisemos si la entrada ya es razonable."},
                  {"id": "nvda-baja-1311", "tipo": "baja", "nivel": 150.0, "moneda": "USD", "creada": "2026-11-13",
                   "nota": "NVIDIA perfora US$150: la caída sigue, no es momento de entrar."}]})
a.put("usuario/lista", lista)
print("::notice::lista: " + ", ".join(str(x.get("ticker") if isinstance(x, dict) else x) for x in lista))
