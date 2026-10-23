"""Bitácora de fallas del reloj del Worker."""
import json

from mesa.nucleo.almacen import almacen_por_defecto

print("::notice::" + json.dumps((almacen_por_defecto().get("reloj/log") or [])[:8], ensure_ascii=False)[:3000])
