"""¿El P/E y el crecimiento de ganancias predicen? 10 años, CEDEARs (acciones de EE.UU.).
Ganancias por acción trimestrales de la SEC (companyfacts, gratis). Cada fin de mes: P/E = precio / ganancias de los últimos 12 meses,
crecimiento = ganancias 12m contra las de un año antes, PEG = P/E / crecimiento. Rendimiento de los 3 meses siguientes.
Solo se usan ganancias YA publicadas en esa fecha (campo 'filed'). Además: si es cíclica (ganancias muy variables)."""
import json, traceback, bisect
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from mesa.datos import gratis
from mesa.datos.gratis import _S
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.cierre import _universo_cedears
a = almacen_por_defecto()
H = {"User-Agent": "MesaDeDinero research bot (uso personal, sin fines comerciales)", "Accept": "application/json"}
try:
    tick = _S.get("https://www.sec.gov/files/company_tickers.json", headers=H, timeout=30).json()
    cik = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in tick.values()}
    print(f"::notice::SEC: {len(cik)} empresas")
except Exception as ex:
    print(f"::notice::SEC ERR {ex}"); raise SystemExit

def eps(tk):
    c = cik.get(tk.replace(".", "-"))
    if not c:
        return None
    try:
        j = _S.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{c}.json", headers=H, timeout=40).json()
    except Exception:
        return None
    g = j.get("facts", {}).get("us-gaap", {})
    for k in ("EarningsPerShareDiluted", "EarningsPerShareBasic"):
        u = (g.get(k) or {}).get("units", {}).get("USD/shares")
        if u:
            q = {}
            for x in u:  # solo trimestres (≈90 días)
                if x.get("start") and x.get("end") and x.get("filed"):
                    from datetime import date
                    d = (date.fromisoformat(x["end"]) - date.fromisoformat(x["start"])).days
                    if 80 <= d <= 100:
                        q.setdefault(x["end"], (x["filed"], x["val"]))
                        q[x["end"]] = min(q[x["end"]], (x["filed"], x["val"]))
            return sorted((e, f, v) for e, (f, v) in q.items())
    return None

uni = _universo_cedears(a)
uni = [t for t in uni if t not in ("SPY", "QQQ", "DIA", "IWM", "GLD", "SLV", "EWZ", "XLE", "ARKK", "IBB", "BITO")]
with ThreadPoolExecutor(6) as ex:
    precios = dict(zip(uni, ex.map(lambda t: gratis.yahoo(t.replace(".", "-"), "10y"), uni)))
    epss = dict(zip(uni, ex.map(eps, uni)))
filas = []
for tk in uni:
    pr, ep = precios.get(tk) or [], epss.get(tk) or []
    if len(pr) < 500 or len(ep) < 12:
        continue
    fs = [f for f, _ in pr]; cs = [c for _, c in pr]
    anual = [v for _, _, v in ep]
    ciclica = np.std(anual) / (abs(np.mean(anual)) + 1e-9) > 0.8
    meses = sorted({f[:7] for f in fs})
    for m in meses[13:-3]:
        i = bisect.bisect_right(fs, m + "-31") - 1
        hoy = fs[i]
        pub = [(e, v) for e, f, v in ep if f <= hoy]
        if len(pub) < 8:
            continue
        ttm = sum(v for _, v in pub[-4:]); ant = sum(v for _, v in pub[-8:-4])
        if ttm <= 0 or ant <= 0:
            continue
        pe = cs[i] / ttm; gr = ttm / ant - 1
        j = min(len(cs) - 1, i + 63)
        filas.append((tk, hoy, pe, gr, pe / (gr * 100) if gr > 0 else None, cs[j] / cs[i] - 1, ciclica))
print(f"::notice::{len(filas)} meses-empresa de {len(set(f[0] for f in filas))} empresas")
def r(xs, nom):
    v = np.array([x[5] for x in xs]) * 100
    if len(v) >= 30:
        print(f"::notice::{nom}: {len(v)} · 3 meses {v.mean():+.2f}% (mediana {np.median(v):+.2f}%) · suben {np.mean(v > 0) * 100:.0f}% · caen 15%+ {np.mean(v < -15) * 100:.0f}%")
r(filas, "TODOS")
peg = [x for x in filas if x[4] is not None]
r([x for x in peg if x[4] < 1], "PEG < 1 (barata para lo que crece)")
r([x for x in peg if 1 <= x[4] < 2], "PEG 1-2")
r([x for x in peg if x[4] >= 2], "PEG ≥ 2 (cara para lo que crece)")
r([x for x in filas if x[3] <= 0], "ganancias en baja")
r([x for x in filas if x[2] < 15], "P/E < 15")
r([x for x in filas if x[2] > 40], "P/E > 40")
r([x for x in filas if x[6] and x[2] < 10], "CÍCLICA con P/E < 10 (trampa de Lynch)")
r([x for x in filas if x[6] and x[2] > 25], "CÍCLICA con P/E > 25")
r([x for x in filas if not x[6] and x[4] is not None and x[4] < 1], "NO cíclica con PEG < 1")
