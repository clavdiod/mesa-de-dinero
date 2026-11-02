"""¿Entramos caro? Para cada compra: dónde estaba el precio de entrada contra su historia (3 meses y 1 año, antes de comprar)."""
import statistics as st
from mesa.datos import gratis
COMPRAS = [("TRAN", "2026-10-28", 2158.0), ("ALUA", "2026-10-29", 850.0), ("YPFD", "2026-10-29", 8135.0),
           ("CEPU", "2026-10-30", 1791.0), ("IBB", "2026-10-22", 12690.0)]
for tk, f, p in COMPRAS:
    v = gratis.yahoo_ohlcv(tk + ".BA", "2y")
    antes = [x for x in v if x["fecha"] < f]
    c = [x["c"] for x in antes]; h = [x["h"] for x in antes]
    def pct(ventana):
        w = c[-ventana:]
        return sum(1 for x in w if x < p) / len(w) * 100
    m20 = st.mean(c[-20:])
    mx3, mx1 = max(h[-63:]), max(h[-250:])
    mn3, mn1 = min(c[-63:]), min(c[-250:])
    desp = [x for x in v if x["fecha"] >= f]
    mx_desde = max(x["h"] for x in desp); hoy = desp[-1]["c"]
    print(f"::notice::{tk} compra {p:g} el {f} | percentil 3 meses {pct(63):.0f} (rango {mn3:g}-{mx3:g}) | percentil 1 año {pct(250):.0f} (rango {mn1:g}-{mx1:g}) | "
          f"vs promedio 20 {(p / m20 - 1) * 100:+.1f}% | hasta máx 3m {(mx3 / p - 1) * 100:+.1f}% | hasta máx 1 año {(mx1 / p - 1) * 100:+.1f}% | "
          f"máximo desde la compra {mx_desde:g} ({(mx_desde / p - 1) * 100:+.1f}%) | hoy {hoy:g} ({(hoy / p - 1) * 100:+.1f}%)")
