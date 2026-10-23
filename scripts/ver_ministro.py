"""¿El Ministro aparece en la app y en los debates?"""
from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
est = a.get("ui/estado") or {}
m = est.get("ministro") or {}
deb = a.get("ui/debates") or {}
con = {tk: [x["texto"][:60] for x in d.get("favor", []) + d.get("contra", []) if x["agente"] == "ministro"] for tk, d in deb.items()}
con = {k: v for k, v in con.items() if v}
sen = a.get(f"senales/{est.get('fecha')}") or {}
mis = sorted({v["ticker"] for k, v in sen.items() if v["agente"] == "ministro"})
print("::notice::" + f"ronda {est.get('hora')} · tarjeta: {'sí' if m else 'no'} · reglas {[r['regla'] for r in m.get('reglas') or []]} · "
      f"debates con el Ministro: {list(con)[:12]} · señales registradas: {mis}")
