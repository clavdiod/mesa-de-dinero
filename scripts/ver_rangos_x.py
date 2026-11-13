"""13/11: ¿los rangos de compra de un posteo de X son razonables? Precio actual, rango del año y distancia al rango."""
from mesa.datos import gratis
R = {"NVDA": (158, 168), "AVGO": (305, 325), "NBIS": (120, 132), "RKLB": (52, 58), "INTC": (52, 56)}
out = []
for tk, (lo, hi) in R.items():
    v = gratis.yahoo(tk, "1y")
    cs = [c for _, c in v]
    p = (gratis.yahoo_vivo(tk) or {}).get("precio") or (cs[-1] if cs else None)
    if not p:
        out.append(f"{tk}: sin datos"); continue
    mn, mx = min(cs), max(cs)
    dentro = lo <= p <= hi
    out.append(f"{tk}: hoy {p:.2f} · rango posteo {lo}-{hi} ({'ADENTRO' if dentro else f'{(hi / p - 1) * 100:+.0f}% hasta el techo del rango'}) · año {mn:.0f}-{mx:.0f} · tocó el rango en el año: {sum(1 for c in cs if lo <= c <= hi)} días")
print("::notice::" + " ## ".join(out))
