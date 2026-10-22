"""Detalle: aciertos por dirección (compra / evitar) de cada analista en la semana."""
from datetime import datetime, timedelta, timezone

from mesa.nucleo.almacen import almacen_por_defecto

a = almacen_por_defecto()
hoy = (datetime.now(timezone.utc) - timedelta(hours=3)).date()
panel = (a.get("ui/panel") or {}).get("titulos") or {}
st = {}
for i in range(8):
    f = (hoy - timedelta(days=i)).isoformat()
    if f == hoy.isoformat():
        continue
    for s in (a.get(f"senales/{f}") or {}).values():
        p1 = (panel.get(s["ticker"]) or [None])[0]
        if not p1 or not s.get("precio"):
            continue
        r = (p1 / s["precio"] - 1) * 100 * s["dir"]
        k = (s["agente"], "compra" if s["dir"] > 0 else "evitar")
        x = st.setdefault(k, [0, 0, 0.0])
        x[0] += 1; x[1] += int(r > 0); x[2] += r
print("::notice::" + " | ".join(f"{a_}/{d}: {x[0]} · {x[1] / x[0] * 100:.0f}% · {x[2] / x[0]:+.2f}%" for (a_, d), x in sorted(st.items(), key=lambda z: -z[1][0]))[:3900])
