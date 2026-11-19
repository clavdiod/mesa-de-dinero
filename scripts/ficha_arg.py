"""Ficha en frío de una acción argentina con el historial de la mesa (TK abajo). 19/11: DGCU2 (compra grande)."""
import numpy as np
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos.cache import CacheHistorico
from mesa.agentes import ficha_frio, estructura
TK = "DGCU2"
a = almacen_por_defecto(); vel = CacheHistorico(a).velas(TK)
x = ((a.get("ui/panel") or {}).get("titulos") or {}).get(TK) or []
pr = float(x[0]) if x and x[0] else vel[-1]["cierre"]
c = np.array([v["cierre"] for v in vel])
atr = np.mean([v["maximo"] - v["minimo"] for v in vel[-14:]])
dist = min(0.12, max(0.04, 2 * atr / pr))
plan = {"ticker": TK, "entrada": pr, "stop": pr * (1 - dist), "objetivo": pr * (1 + 2 * dist)}
est = estructura.leer(vel[-300:], pr, "acciones") or {}
f = ficha_frio.ficha(vel[-400:], pr, plan, est, [], "acciones")
y1 = c[-250:]
print(f"::notice::{TK} ${pr:,.2f} (var hoy {x[1] if len(x) > 1 else '?'}%) · {len(vel)} ruedas · máx 1 año {y1.max():,.0f} mín {y1.min():,.0f} · cae {(pr / y1.max() - 1) * 100:.0f}% desde el máximo · "
      f"5r {(pr / c[-6] - 1) * 100:+.1f}% · 1m {(pr / c[-22] - 1) * 100:+.1f}% · 3m {(pr / c[-64] - 1) * 100:+.1f}% · SMA50 {c[-50:].mean():,.0f} SMA200 {c[-200:].mean():,.0f} · stop {dist * 100:.1f}%")
print("::notice::GRAFICO " + estructura.frase(est))
print("::notice::FICHA " + ficha_frio.texto(f).replace("\n", " ")[:3000])
print("::notice::ULTIMAS " + " | ".join(f"{v['fecha'][5:]} {v['cierre']:,.0f} v{v.get('volumen') or 0:,.0f}" for v in vel[-8:]))
