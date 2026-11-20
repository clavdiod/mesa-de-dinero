"""20/11: Clau: "necesito que agarremos oportunidades… no tengo disponible… tengo que recuperar YPFD… ¿volver a comprar YPF
al precio actual? ¿o Vista?… analicemos, tenemos expertos". Todo en una corrida:
A) la cartera completa: cuánto vale cada cosa y cuánto rinde (lo que está quieto puede financiar oportunidades);
B) YPFD, VIST, PAMP y las energéticas: precio, ficha en frío y qué pasó en 10 años en momentos parecidos (en dólares);
C) la tesis de Nacho (IEB): "el equity argentino está desarbitrado con el riesgo país". ¿Cuando el riesgo país baja y el
   Merval en dólares no acompaña, después el Merval corrige para arriba? 10 años.
D) el ranking de hoy con las ventajas probadas (compra grande, MACD positivo en acciones argentinas, etc.)."""
import bisect, json, traceback
import numpy as np
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos import gratis
from mesa.datos.cache import CacheHistorico
from mesa.datos.bymaeduca import flujos_guardados
from mesa.agentes import ficha_frio, estructura
a = almacen_por_defecto(); cache = CacheHistorico(a)
panel = (a.get("ui/panel") or {}).get("titulos") or {}
cart = a.get("usuario/cartera") or []
fl = flujos_guardados(a)

# A) cartera
tot = 0; filas = []
for p in cart:
    tk = p["ticker"]; x = panel.get(tk) or []
    pr = float(x[0]) if x and x[0] else None; q = float(p.get("cantidad") or 0); c = float(p.get("precio") or 0)
    grupo = x[4] if len(x) > 4 else "?"
    div = 100 if grupo in ("bonos", "ons", "letras", "soberanos") or (tk in fl) else 1
    val = pr * q / div if pr else None
    res = (pr / c - 1) * 100 if pr and c else None
    info = fl.get(tk) or {}
    tot += val or 0
    filas.append(f"{tk} [{grupo}] q {q:g} compra {c:g} hoy {pr} valor ${val:,.0f} res {('%+.1f%%' % res) if res is not None else 's/d'} TIR {info.get('tir')} vence {info.get('vence')} ley {info.get('ley')} moneda {info.get('moneda')}" if val else f"{tk} [{grupo}] q {q:g} compra {c:g} sin precio")
print("::notice::CARTERA total aprox $" + f"{tot:,.0f} | " + " | ".join(filas))

# B) energéticas: ficha + historia en dólares
ccl = gratis.ccl_historico(); fc = sorted(ccl)
usd = lambda f, p: p / ccl[fc[bisect.bisect_right(fc, f) - 1]] if fc and f >= fc[0] else None
for tk in ("YPFD", "VIST", "PAMP", "TGSU2", "CEPU"):
    try:
        x = panel.get(tk) or []; pr = float(x[0]) if x and x[0] else None
        vel = cache.velas(tk)
        if not pr or len(vel) < 100:
            print(f"::notice::{tk}: sin datos"); continue
        cs = [v["cierre"] for v in vel]
        atr = np.mean([v["maximo"] - v["minimo"] for v in vel[-14:]]); dist = min(0.12, max(0.05, 2 * atr / pr))
        plan = {"ticker": tk, "entrada": pr, "stop": pr * (1 - dist), "objetivo": pr * (1 + 3 * dist)}
        est = estructura.leer(vel[-300:], pr, "acciones") or {}
        f = ficha_frio.ficha(vel[-400:], pr, plan, est, [], "acciones")
        h = gratis.yahoo(tk + ".BA", "10y")
        s = np.array([u for u in (usd(fe, p_) for fe, p_ in h) if u])
        dd = pr / max(cs[-60:]) - 1; r20 = pr / cs[-21] - 1
        r60, mx60 = [], []
        for i in range(60, len(s) - 60):
            if abs(s[i] / s[i - 59:i + 1].max() - 1 - dd) <= 0.05 and abs(s[i] / s[i - 20] - 1 - r20) <= 0.07:
                r60.append(s[i + 60] / s[i] - 1); mx60.append(s[i + 1:i + 61].max() / s[i] - 1)
        r60, mx60 = np.array(r60), np.array(mx60)
        c0 = next((p for p in cart if p["ticker"] == tk), None)
        hist = (f"HISTORIA USD {len(r60)} casos (cae {dd * 100:.0f}% del máx 3m, {r20 * 100:+.0f}% en 1m): a 3 meses mediana {np.median(r60) * 100:+.1f}%, suben {np.mean(r60 > 0) * 100:.0f}%, "
                f"llegó a +15% en algún momento {np.mean(mx60 >= 0.15) * 100:.0f}%, peor 10% {np.percentile(r60, 10) * 100:+.1f}%") if len(r60) >= 10 else f"historia: pocos casos ({len(r60)})"
        print(f"::notice::{tk} ${pr:,.0f} ({x[1] if len(x) > 1 else '?'}% hoy)" + (f" · TU POSICIÓN {c0.get('cantidad')} a {c0.get('precio')} ({(pr / float(c0['precio']) - 1) * 100:+.1f}%)" if c0 else "")
              + f" · máx 1 año {max(cs[-250:]):,.0f} mín {min(cs[-250:]):,.0f} · stop {dist * 100:.0f}% · {hist} | GRAFICO {estructura.frase(est)} | FICHA {ficha_frio.texto(f)[:1500]}")
    except Exception:
        print(f"::notice::{tk} ERR " + traceback.format_exc().replace(chr(10), ' | ')[-400:])

# C) Merval en dólares contra riesgo país (tesis "desarbitrado")
try:
    mac = gratis.series_macro(10); rp = mac.get("riesgo_pais") or {}
    mer = {fe: v for fe, v in gratis.yahoo("^MERV", "10y")}
    mu = {fe: u for fe, u in ((fe, usd(fe, v)) for fe, v in mer.items()) if u}
    fs = sorted(set(mu) & set(rp)); m = np.array([mu[x] for x in fs]); r = np.array([rp[x] for x in fs])
    casos, todos = [], []
    for i in range(60, len(fs) - 60, 5):
        dr = r[i] / r[i - 60] - 1; dm = m[i] / m[i - 60] - 1; fw = m[i + 60] / m[i] - 1
        todos.append(fw)
        if dr <= -0.15 and dm <= 0.05:
            casos.append((fs[i], dr, dm, fw))
    i = len(fs) - 1
    hoy = f"hoy: riesgo país {r[i]:.0f} ({(r[i] / r[i - 60] - 1) * 100:+.0f}% en 3 meses), Merval USD {(m[i] / m[i - 60] - 1) * 100:+.0f}% en 3 meses"
    if casos:
        fw = np.array([c[3] for c in casos])
        print(f"::notice::DESARBITRAJE {hoy} | 10 años: riesgo país bajó 15%+ en 3 meses y el Merval USD no subió más de 5%: {len(casos)} momentos "
              f"(años {sorted({c[0][:4] for c in casos})}) → Merval USD 3 meses después mediana {np.median(fw) * 100:+.1f}%, sube {np.mean(fw > 0) * 100:.0f}% "
              f"· contra cualquier momento {np.median(todos) * 100:+.1f}% (sube {np.mean(np.array(todos) > 0) * 100:.0f}%)")
    else:
        print(f"::notice::DESARBITRAJE {hoy} | sin casos parecidos en 10 años")
except Exception:
    print("::notice::DESARBITRAJE ERR " + traceback.format_exc().replace(chr(10), ' | ')[-400:])

# D) lo que la mesa ve hoy con ventaja probada
est = a.get("ui/estado") or {}
c = est.get("comite") or {}
print("::notice::COMITE hoy " + json.dumps([{k: x.get(k) for k in ("ticker", "aprobada", "favor", "frio", "frio_motivo")} for x in (c.get("acta") or [])[:10]], ensure_ascii=False)[:1500])
al = [x for x in a.get("ui/alertas") or [] if x.get("fecha", "") >= "2026-11-18" and ("compra grande" in str(x.get("texto", "")).lower() or "agotamiento" in str(x.get("texto", "")).lower())]
print("::notice::COMPRAS GRANDES " + " | ".join(f"{x['fecha'][5:]} {x.get('hora')} {x.get('ticker')}: {str(x.get('texto'))[:120]}" for x in al[:12]))
