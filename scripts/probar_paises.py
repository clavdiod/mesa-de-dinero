"""Cuántos titulares de 'sacudón' por país hay ahora (para calibrar los mínimos)."""
from mesa.agentes import mundo as m
ts = m.leer(12)
print(f"::notice::{len(ts)} titulares")
cuentas = []
for cod, (nombre, patron, papeles, contagia, minimo) in m.PAISES.items():
    rx = m._r(patron)
    mal = [t["titulo"] for t in ts if rx.search(t.get("titulo") or "") and m.SACUDON_MAL.search(t["titulo"]) and not m.SACUDON_BIEN.search(t["titulo"])]
    bien = [t["titulo"] for t in ts if rx.search(t.get("titulo") or "") and m.SACUDON_BIEN.search(t["titulo"]) and not m.SACUDON_MAL.search(t["titulo"])]
    mal = list({x[:70].lower(): x for x in mal}.values()); bien = list({x[:70].lower(): x for x in bien}.values())
    cuentas.append(f"{cod} mal={len(mal)} bien={len(bien)} min={minimo} ej: {(mal or bien or [''])[0][:70]}")
print("::notice::" + " || ".join(cuentas)[:3800])
print("::notice::DETECTADOS " + " | ".join(f"{t['tema']} {t['n']}" for t in m.detectar_paises(ts)))
