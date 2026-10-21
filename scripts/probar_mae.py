"""Licitaciones del MAE tal como las ve la mesa (sin escribir nada)."""
from datetime import date, timedelta

from mesa.datos.gratis import licitaciones_mae

hoy = date.today()
evs = licitaciones_mae(hoy - timedelta(days=1), hoy + timedelta(days=45))
print("::notice::" + f"{len(evs)} licitaciones || " + " || ".join(f"{e['fecha']} [{e['clase']}] {e['nombre']} · {e.get('emisor', '')}" for e in evs[:15])[:3900])

from mesa.datos import gratis
ns = []
for q in ("licitación obligaciones negociables", "colocación ON clase licita hoy", "emisión obligaciones negociables tasa licitación"):
    ns += [n["titulo"] for n in gratis.buscar_noticias(q, horas=48, max_items=8)]
print("::notice::NOTICIAS || " + " || ".join(dict.fromkeys(ns))[:3900])
