"""Opinión del Ministro sobre la cartera."""
from mesa.nucleo.almacen import almacen_por_defecto

m = (almacen_por_defecto().get("ui/estado") or {}).get("ministro") or {}
print("::notice::" + " ||| ".join(f"{c['ticker']} [{c['tipo']}] {c['texto']}" for c in m.get("cartera") or [])[:3900])
