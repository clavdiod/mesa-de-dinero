from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
e = a.get("ui/estado") or {}
print(f"::notice::ronda {e.get('fecha')} {e.get('hora')}")
for nom, l in [("anticipador", e.get("anticipo_lista") or {})] + list((e.get("anticipo_listas") or {}).items()):
    print(f"::notice::{nom} activo {l.get('activo')} " + " | ".join(f"#{x.get('prioridad')} {x['ticker']} plan {x.get('plan')} hasta {x.get('vence')}" for x in (l.get('lista') or [])[:6])[:1800])
c = e.get("comite") or {}
print("::notice::comite " + str([(x["ticker"], x["aprobada"]) for x in c.get("acta") or []]))
