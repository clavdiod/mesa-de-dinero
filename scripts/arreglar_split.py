"""04/11: deshace la corrección equivocada de limpiar_velas_raras (16 velas buenas) y ajusta por desdoblamiento
los precios viejos de YPFD y MIRG (el historial mezclaba precios de antes y después del split de agosto)."""
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
orig = {("MIRG", "2026-08-03"): (1720.0, 1680.0, 1650.0, 1630.0), ("MIRG", "2026-08-04"): (1700.0, 1640.0, 1700.0, 1570.0),
        ("YPFD", "2026-08-03"): (8270.0, 8105.0, 8150.0, 8015.0), ("YPFD", "2026-08-04"): (8095.0, 7855.0, 8095.0, 7770.0)}
COMUNES = [2, 3, 4, 5, 10, 20, 25, 50, 100]
for tk in ("YPFD", "MIRG"):
    v = a.get(f"cache/diario/{tk}") or []
    for x in v:
        o = orig.get((tk, x.get("fecha")))
        if o:
            x["maximo"], x["cierre"], x["apertura"], x["minimo"] = o
    # borde del split: el primer salto de 3x o más entre cierres seguidos
    cortes = [i for i in range(1, len(v)) if v[i - 1].get("cierre") and v[i].get("cierre") and v[i - 1]["cierre"] / v[i]["cierre"] >= 3]
    msg = f"{tk}: {len(v)} velas, cortes en " + ",".join(v[i]["fecha"] for i in cortes)
    for i in reversed(cortes):
        bruto = v[i - 1]["cierre"] / (v[i].get("apertura") or v[i]["cierre"])
        r = min(COMUNES, key=lambda c: abs(c / bruto - 1))
        r = r if abs(r / bruto - 1) <= 0.08 else bruto
        for x in v[:i]:
            for k in ("maximo", "cierre", "apertura", "minimo"):
                if x.get(k):
                    x[k] = round(x[k] / r, 2)
            if x.get("volumen"):
                x["volumen"] = x["volumen"] * r
        msg += f" · split {r} (salto bruto {bruto:.2f}) en {v[i]['fecha']}"
    a.put(f"cache/diario/{tk}", v)
    cs = [x["cierre"] for x in v[-250:] if x.get("cierre")]
    msg += f" · ahora máx/mín 1 año {max(cs)}/{min(cs)} · " + ",".join(f"{x['fecha'][5:]}:{x['cierre']}" for x in v[-70:-60])
    print("::notice::" + msg)
