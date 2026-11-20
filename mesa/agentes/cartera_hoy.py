"""Tu cartera hoy (20/11, criterio de Clau: "primero mi stock, a ver si se ve afectado por algo; luego oportunidades, y
qué tiempo aprox creen los analistas que sirve tenerla para tener una ganancia").

Una vez por día, en la primera ronda después de las 11:05 (antes de las oportunidades de las 11:20), revisa cada papel
de la cartera con todo lo que sabe la mesa y avisa:
- acciones y CEDEARs: precio contra tu compra, distancia a la alarma, noticias de la empresa (Corresponsal), lo que dicen
  los libros probados (Marks, Kostolany, Graham, Lynch) y cuánto TIEMPO suele tardar en dar ganancia según la historia;
- bonos y ONs: próximo cobro, vencimiento y TIR; si vence en 15 días, avisa que queda plata libre para oportunidades.
"""
from __future__ import annotations

import bisect
from datetime import date, timedelta

# 20/11, probado (scripts/probar_plazos.py): cuánto tardó en llegar a +5% (ganancia que ya paga la comisión)
PLAZOS = {
    "rebote": "en la historia, después de caídas así llegó a +5% en un mes 69 de cada 100 veces y en 3 meses 84 (la mitad, en ~7 ruedas)",
    "panico_acc": "después de un pánico así llegó a +5% en un mes 64 de cada 100 veces y en 3 meses 78",
    "panico_ced": "después de un pánico así llegó a +5% en un mes 61 de cada 100 veces y en 3 meses 81",
    "normal_acc": "un día cualquiera, una acción argentina llega a +5% en un mes 57 de cada 100 veces y en 3 meses 74",
    "normal_ced": "un día cualquiera, un CEDEAR llega a +5% en un mes 47 de cada 100 veces y en 3 meses 71",
}


def _n(x, d=0):
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _recuperar(velas: list[dict], falta: float) -> str:
    """Con la historia del propio papel: qué parte de las veces subió `falta` (o más) en 3, 6 y 12 meses."""
    c = [v["cierre"] for v in velas if v.get("cierre")]
    if len(c) < 300 or falta <= 0:
        return ""
    out = []
    for nom, d in (("3 meses", 63), ("6 meses", 126), ("1 año", 250)):
        xs = [max(c[i + 1:i + d + 1]) / c[i] - 1 >= falta for i in range(0, len(c) - d - 1, 3)]
        if len(xs) >= 30:
            out.append(f"{nom} {round(sum(xs) / len(xs) * 100)}%")
    return (f"Para volver a tu precio falta {_n(falta * 100, 1)}%; en su historia (en pesos), subió eso o más en: " + ", ".join(out) + ".") if out else ""


def armar(ctx, almacen, cartera: list[dict], hoy: date, noticias_de=None) -> dict | None:
    from .biblioteca import revision_libros
    from .posiciones import rebotes, CLAVE_KOST
    from ..datos.bymaeduca import flujos_guardados
    lineas, atencion = [], 0
    kost = {k["ticker"]: k for k in ((almacen.get(CLAVE_KOST) or {}).get("lista") or [])}
    try:
        from ..datos import gratis
        ccl = gratis.ccl_historico()
        precio_de = lambda tk: (ctx.titulo(tk) or {}).get("ultimo")
        reb = {r["ticker"] for r in rebotes(ctx, ctx.cache.velas, ccl, precio_de)}
    except Exception:
        reb = set()
    fl = flujos_guardados(almacen)
    for c in cartera:
        tk = str(c.get("ticker") or "").upper()
        t = ctx.titulo(tk) or {}
        pr, grupo = t.get("ultimo"), t.get("grupo")
        if not pr:
            continue
        if grupo in ("acciones", "cedears"):
            compra = float(c.get("precio") or 0)
            res = (pr / compra - 1) * 100 if compra else None
            alarmas = [float(a["nivel"]) for a in c.get("alertas") or [] if a.get("tipo") == "baja" and a.get("nivel")]
            al = max(alarmas) if alarmas else None
            d_al = (pr / al - 1) * 100 if al else None
            partes = [f"{tk} ${_n(pr, 2)}" + (f" ({'+' if res >= 0 else ''}{_n(res, 1)}% contra tu compra)" if res is not None else "")]
            ojo = False
            if d_al is not None:
                if d_al < 0:
                    partes.append(f"ya está {_n(abs(d_al), 1)}% DEBAJO de tu alarma de {_n(al)}: hay que decidir si seguir o vender (y mover la alarma)")
                else:
                    partes.append(f"alarma {_n(al)} a {_n(d_al, 1)}%")
                ojo |= d_al < 4
            sen = None
            if noticias_de:
                try:
                    sen = next(iter(noticias_de([tk])), None)
                except Exception:
                    sen = None
            if sen is not None and abs(sen.direccion) and sen.fuerza >= 0.2:
                partes.append(("🔴 " if sen.direccion < 0 else "🟢 ") + sen.texto[:160])
                ojo |= sen.direccion < 0
            libros = [x for x in revision_libros(almacen, tk, grupo) if not x.startswith("📗")]
            if libros:
                partes.append(" ".join(x.rstrip(".") + "." for x in libros)[:400].rstrip("."))
            base = tk[:-1] if tk[-1:] in ("D", "C") and grupo == "cedears" else tk
            clave = "rebote" if tk in reb else ("panico_acc" if grupo == "acciones" else "panico_ced") if base in kost else \
                ("normal_acc" if grupo == "acciones" else "normal_ced")
            partes.append("⏳ Tiempo: " + PLAZOS[clave] + ".")
            if res is not None and res < -3:
                r_ = _recuperar(ctx.cache.velas(tk), compra / pr - 1)
                if r_:
                    partes.append(r_)
            atencion += ojo
            lineas.append(("⚠️ " if ojo else "• ") + ". ".join(p_.rstrip(".") for p_ in partes) + ".")
        else:
            info = fl.get(tk) or {}
            compra = float(c.get("precio") or 0)
            res_b = (pr / compra - 1) * 100 if compra and 0.2 < pr / compra < 5 else None  # si las unidades no coinciden, no se muestra
            fut = [f for f in info.get("flujos") or [] if str(f.get("fecha")) > hoy.isoformat()]
            prox = fut[0] if fut else None
            vence = info.get("vence")
            txt = f"• {tk}" + (f": próximo cobro el {str(prox['fecha'])[8:10]}/{str(prox['fecha'])[5:7]}" if prox else "") \
                + (f", vence el {str(vence)[8:10]}/{str(vence)[5:7]}/{str(vence)[2:4]}" if vence else "") \
                + (f", rinde {_n(float(info['tir']), 1)}% anual" if info.get("tir") not in (None, "") else "")
            if not fut and not vence:
                txt += f": precio {_n(pr, 2)}" + (f" ({'+' if res_b >= 0 else ''}{_n(res_b, 1)}% contra tu compra)" if res_b is not None else "") \
                    + " (sin cronograma de pagos cargado)"
            if str(info.get("moneda") or "").upper() == "USD" and info.get("tir") not in (None, "") and float(info["tir"]) < 5:
                txt += " → rinde poco para un bono en dólares: el agente de asimetría muestra alternativas (AL35, AL41)"
            if vence and hoy.isoformat() < str(vence) <= (hoy + timedelta(days=15)).isoformat():
                txt += " → vence en menos de 15 días: queda plata libre para las oportunidades"
            lineas.append(txt + ".")
    if not lineas:
        return None
    lineas.sort(key=lambda x: (not x.startswith("⚠️"),))
    texto = (f"{atencion} cosa(s) para mirar. " if atencion else "Nada urgente. ") + " ".join(lineas)
    return {"fecha": hoy.isoformat(), "hora": ctx.hora, "ticker": "📋 Tu cartera hoy", "tipo": "cartera_hoy",
            "texto": texto[:3500], "lineas": lineas, "atencion": atencion}
