"""19/11: la vela del 17/11 de VXX quedó con volumen 0 y el cierre del día anterior. ¿Cuántos papeles más? (solo mira)"""
from collections import Counter
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos.cache import CacheHistorico
a = almacen_por_defecto(); c = CacheHistorico(a)
malos, por_dia, total = [], Counter(), 0
for tk in c.indice:
    v = c.velas(tk)
    for i in range(1, len(v)):
        x, p = v[i], v[i - 1]
        if x["fecha"] >= "2026-10-20" and not x.get("volumen") and x.get("cierre") == p.get("cierre"):
            por_dia[x["fecha"]] += 1
            if x["fecha"] == "2026-11-17":
                malos.append(tk)
    total += 1
print(f"::notice::{total} papeles con historial · velas sospechosas (volumen 0 y mismo cierre que el día anterior) por día desde 20/10: {dict(sorted(por_dia.items()))}")
print(f"::notice::17/11: {len(malos)} papeles: {', '.join(sorted(malos)[:120])}")
v = c.velas("VXX")[-6:]
print("::notice::VXX " + " | ".join(f"{x['fecha']} a{x.get('apertura')} M{x.get('maximo')} m{x.get('minimo')} c{x['cierre']} v{x.get('volumen')} {x.get('fuente')}" for x in v))
