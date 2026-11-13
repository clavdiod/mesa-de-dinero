"""06/11: ¿Es buen momento para HIMS? Ficha en frío con la historia de Micron en dólares."""
import numpy as np
from mesa.datos import gratis
from mesa.agentes import ficha_frio, estructura, fundamentos
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
v = gratis.yahoo_ohlcv("HIMS", "10y")
viv = gratis.yahoo_vivo("HIMS", prepost=True)
vel = [{"fecha": x["fecha"], "cierre": x["c"], "maximo": x["h"], "minimo": x["l"], "apertura": x["o"], "volumen": x["v"]} for x in v]
c = np.array([x["c"] for x in v]); pr = viv.get("precio") or c[-1]
y1 = c[-252:]
atr = np.mean([x["h"] - x["l"] for x in v[-14:]])
dist = min(0.15, max(0.06, 2.5 * atr / pr))
plan = {"entrada": pr, "stop": pr * (1 - dist), "objetivo": pr * 1.15}
est = estructura.leer(vel[-300:], pr, "cedears") or {}
f = ficha_frio.ficha(vel[-400:], pr, plan, est, [], "cedears", fundamentos=fundamentos.de(a, "HIMS"))
# analogos: caídas parecidas desde el máximo de 20 ruedas y de 5 días, a 20 y 60 ruedas
dd = pr / max(c[-20:]) - 1; r5 = pr / c[-6] - 1
r20, r60 = [], []
for i in range(25, len(c) - 60):
    if abs(c[i] / c[i - 19:i + 1].max() - 1 - dd) <= 0.05 and abs(c[i] / c[i - 5] - 1 - r5) <= 0.06:
        r20.append(c[i + 20] / c[i] - 1); r60.append(c[i + 60] / c[i] - 1)
r20, r60 = np.array(r20), np.array(r60)
print(f"::notice::HIMS USD {pr:.2f} (ayer {c[-1]:.2f}) · cae {dd*100:.1f}% desde máx 20r, {r5*100:+.1f}% en 5r · 1 año máx {y1.max():.2f} mín {y1.min():.2f} · ubicación en el rango del año {(pr-y1.min())/(y1.max()-y1.min())*100:.0f}% · SMA50 {c[-50:].mean():.2f} SMA200 {c[-200:].mean():.2f} · stop usado {dist*100:.1f}%")
print("::notice::GRAFICO " + estructura.frase(est))
print("::notice::FICHA " + ficha_frio.texto(f).replace("\n", " ")[:3500])
if len(r20) >= 8:
    print(f"::notice::HISTORIA HIMS {len(r20)} casos: 20r mediana {np.median(r20)*100:+.1f}% suben {np.mean(r20>0)*100:.0f}% caen>10% {np.mean(r20<-.1)*100:.0f}% · 60r mediana {np.median(r60)*100:+.1f}% suben {np.mean(r60>0)*100:.0f}% peor10% {np.percentile(r60,10)*100:+.1f}%")
print(f"::notice::FUND {fundamentos.de(a, 'MU')}")
