"""04/11: revisión en frío de la cartera después de la caída. Por papel: precio, pérdida, pisos, gráfico, indicadores,
y qué pasó en 10 años cada vez que este papel cayó parecido desde su máximo de 20 ruedas (en dólares CCL, sin inflación)."""
import bisect
import numpy as np
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos import gratis
from mesa.agentes import estructura, grafico, ficha_frio
a = almacen_por_defecto()
cart = {c["ticker"]: c for c in a.get("usuario/cartera") or []}
ccl = gratis.ccl_historico()
fc = sorted(ccl)
def usd(f, p):
    i = bisect.bisect_right(fc, f) - 1
    return p / ccl[fc[i]] if i >= 0 else None
for tk in ("YPFD", "ALUA", "CEPU", "TRAN"):
    try:
        c = cart.get(tk) or {}
        vivo = gratis.yahoo_vivo(tk + ".BA")
        pr = vivo.get("precio")
        ent = float(c.get("precio_compra") or c.get("precio") or 0)
        h = gratis.yahoo(tk + ".BA", "10y")
        s = [(f, usd(f, p)) for f, p in h if usd(f, p)]
        cs = np.array([x for _, x in s])
        # caída de hoy desde el máximo de 20 ruedas (en ARS, igual en proporción)
        ars = [p for _, p in h]
        if pr and h[-1][1] != pr:
            ars = ars + [pr]
        dd = pr / max(ars[-20:]) - 1; r5 = pr / ars[-6] - 1
        res20, res60, rec = [], [], []
        for i in range(25, len(cs) - 60):
            d_i = cs[i] / cs[i - 19:i + 1].max() - 1
            if abs(d_i - dd) <= 0.04 and abs(cs[i] / cs[i - 5] - 1 - r5) <= 0.06:
                res20.append(cs[i + 20] / cs[i] - 1); res60.append(cs[i + 60] / cs[i] - 1)
                rec.append(cs[i + 1:i + 61].max() / cs[i] - 1)
        res20, res60, rec = map(np.array, (res20, res60, rec))
        falta = ent / pr - 1 if ent and pr else 0
        vel = a.get(f"cache/diario/{tk}") or []
        est = estructura.leer(vel, pr, "acciones") or {}
        g = grafico.armar(vel, pr) or {}
        lec = ficha_frio.lecturas([v["cierre"] for v in vel if v.get("cierre")] + [pr], "acciones")
        pisos = ", ".join(f"{x['nivel']:.0f}({x.get('toques','')})" for x in (g.get("soportes") or [])[:3])
        techos = ", ".join(f"{x['nivel']:.0f}" for x in (g.get("resistencias") or [])[:2])
        n = len(res20)
        txt = (f"{tk}: hoy {pr} · compra {ent} · {(pr/ent-1)*100:+.1f}% · para volver a la compra falta {falta*100:+.1f}% · "
               f"cae {dd*100:.1f}% desde máx 20r, {r5*100:+.1f}% en 5r · max/min 1a {g.get('max_1a')}/{g.get('min_1a')} · pisos {pisos} · techos {techos} · "
               f"gráfico: {estructura.frase(est)} · {lec.get('texto')} · buenas {lec.get('buenas')} malas {lec.get('malas')} · ")
        if n >= 8:
            txt += (f"HISTORIA {n} casos parecidos (USD): 20r mediana {np.median(res20)*100:+.1f}% suben {np.mean(res20>0)*100:.0f}% caen>10% {np.mean(res20<-0.10)*100:.0f}% · "
                    f"60r mediana {np.median(res60)*100:+.1f}% suben {np.mean(res60>0)*100:.0f}% · recupera la compra en 60r {np.mean(rec>=falta)*100:.0f}% · "
                    f"rebote máx típico 60r {np.median(rec)*100:+.1f}%")
        else:
            txt += f"HISTORIA pocos casos ({n})"
        print("::notice::" + txt.replace("\n", " "))
    except Exception as ex:
        import traceback; print(f"::notice::{tk} ERR {ex} {traceback.format_exc()[-300:]}")
