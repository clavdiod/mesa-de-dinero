"""Licitaciones del MAE tal como las ve la mesa (sin escribir nada)."""
from datetime import date, timedelta

from mesa.datos.gratis import licitaciones_mae

hoy = date.today()
evs = licitaciones_mae(hoy - timedelta(days=1), hoy + timedelta(days=45))
print("::notice::" + f"{len(evs)} licitaciones || " + " || ".join(f"{e['fecha']} [{e['clase']}] {e['nombre']} · {e.get('emisor', '')}" for e in evs[:15])[:3900])

from mesa.datos import gratis
out = []
for q in ("obligaciones negociables", "licitación ON", "Loma Negra obligaciones negociables", "colocación de ON"):
    for h in (48, 168):
        ns = gratis.buscar_noticias(q, horas=h, max_items=8)
        out.append(f"{q}/{h}h: {len(ns)} " + " | ".join(n['titulo'][:70] for n in ns[:4]))
print("::notice::NOTICIAS || " + " || ".join(out)[:3900])
