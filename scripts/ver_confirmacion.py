import statistics as st
from mesa.datos import gratis
for tk in ("YPFD", "ALUA", "CEPU", "GGAL", "PAMP", "TGSU2", "TXAR", "BMA"):
    f = gratis.yahoo_ohlcv(tk + ".BA", "6mo")
    x = [v["c"] for v in f]
    m20, ant = st.mean(x[-20:]), st.mean(x[-25:-5])
    print(f"::notice::{tk}: último {x[-1]:.1f} ({f[-1]['fecha']}) promedio 20 {m20:.1f} (hace 5 ruedas {ant:.1f}) → {'CONFIRMADO' if x[-1] > m20 and m20 >= ant else 'todavía cayendo' if x[-1] < m20 else 'arriba del promedio pero el promedio sigue bajando'} | {(x[-1]/m20-1)*100:+.1f}% vs promedio")
