"""Reproduce licitaciones_mae tal cual la llama la mesa."""
import traceback
from datetime import date, timedelta

from mesa.datos import gratis

hoy = date.today()
try:
    evs = gratis.licitaciones_mae(hoy - timedelta(days=1), hoy + timedelta(days=45))
    print("::notice::" + " | ".join(f"{e['fecha']} {e['clase']} {e['nombre'][:60]}" for e in evs))
except Exception:
    print("::notice::ERROR " + traceback.format_exc()[-1500:])
