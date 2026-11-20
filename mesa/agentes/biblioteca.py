"""El Bibliotecario (20/11, pedido de Clau): un analista que aprende de los libros que Clau le pasa y lo enseña al resto
de la mesa en forma práctica y con palabras sencillas.

Cómo funciona:
- Cada libro es un archivo en config/biblioteca/ (resumen con palabras propias, nunca copia del texto): sus ideas, cómo se
  aplican en la mesa y, si se pueden medir con datos, las reglas.
- Lo que se puede medir se mide con datos reales (SEC + Yahoo, gratis) y se prueba con historia antes de votar, como
  cualquier otro analista. Mientras no esté probado, opina pero no vota.
- Enseña: agrega a la ficha en frío de cada CEDEAR "📚 Graham: ..." (cuántos criterios cumple, si hay margen de
  seguridad), y la lección de la semana en el informe del viernes, elegida según lo que pasó en el mercado.

Primer libro: El inversor inteligente (Benjamin Graham). Para sumar un libro: un .yaml nuevo con el mismo formato.
"""
from __future__ import annotations

import math
from datetime import date, timedelta
from pathlib import Path

import yaml

from ..nucleo.config import RAIZ

CLAVE = "biblioteca/graham"


def libros() -> list[dict]:
    out = []
    for p in sorted((RAIZ / "config" / "biblioteca").glob("*.yaml")):
        try:
            out.append(yaml.safe_load(p.read_text(encoding="utf-8")) | {"archivo": p.name})
        except Exception as ex:
            print(f"[biblioteca] {p.name}: {ex}")
    return out


def _graham_cfg() -> dict:
    for lb in libros():
        if (lb.get("reglas") or {}).get("defensivo"):
            return {r["clave"]: r for r in lb["reglas"]["defensivo"]}
    return {}


# ---------------- datos de la SEC (solo lo publicado hasta cada fecha: sirve para probar con historia) ----------------
def _anuales(unidades: list[dict]) -> list[tuple[str, str, float]]:
    """(fin, publicado, valor) de los años fiscales (períodos de ~1 año), la primera publicación de cada uno."""
    q: dict[str, tuple[str, float]] = {}
    for x in unidades or []:
        if not (x.get("start") and x.get("end") and x.get("filed")):
            continue
        d = (date.fromisoformat(x["end"]) - date.fromisoformat(x["start"])).days
        if 350 <= d <= 380:
            q[x["end"]] = min(q.get(x["end"], (x["filed"], x["val"])), (x["filed"], x["val"]))
    return sorted((e, f, v) for e, (f, v) in q.items())


def _instantes(unidades: list[dict]) -> list[tuple[str, str, float]]:
    """(fecha, publicado, valor) de los saldos de balance (sin 'start'), la primera publicación."""
    q: dict[str, tuple[str, float]] = {}
    for x in unidades or []:
        if x.get("start") or not (x.get("end") and x.get("filed")):
            continue
        q[x["end"]] = min(q.get(x["end"], (x["filed"], x["val"])), (x["filed"], x["val"]))
    return sorted((e, f, v) for e, (f, v) in q.items())


def datos_sec(cik: str) -> dict | None:
    from ..datos.gratis import _S
    from .fundamentos import H
    j = _S.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=H, timeout=40).json()
    g = j.get("facts", {}).get("us-gaap", {})
    u = lambda k, un="USD": ((g.get(k) or {}).get("units") or {}).get(un) or []
    prim = lambda *ks, un="USD": next((u(k, un) for k in ks if u(k, un)), [])
    s = {
        "eps": _anuales(prim("EarningsPerShareDiluted", "EarningsPerShareBasic", un="USD/shares")),
        "ventas": _anuales(prim("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet")),
        "div": _anuales(prim("CommonStockDividendsPerShareDeclared", "CommonStockDividendsPerShareCashPaid", un="USD/shares")),
        "div_pagados": _anuales(prim("PaymentsOfDividendsCommonStock", "PaymentsOfDividends")),
        "act_corr": _instantes(u("AssetsCurrent")), "pas_corr": _instantes(u("LiabilitiesCurrent")),
        "deuda_lp": _instantes(prim("LongTermDebtNoncurrent", "LongTermDebt")),
        "patrimonio": _instantes(prim("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest")),
        "acciones": _instantes(((j.get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding") or {}).get("units") or {}).get("shares") or []),
    }
    return s if len(s["eps"]) >= 3 else None


def evaluar(s: dict, precio: float, hasta: str | None = None) -> dict | None:
    """Los 7 criterios del inversor defensivo y el número de Graham, con lo publicado hasta `hasta` (default: todo)."""
    cfg = _graham_cfg()
    h = hasta or "9999"
    pub = lambda k: [(e, v) for e, f, v in s.get(k) or [] if f <= h]
    ult = lambda k: (pub(k) or [(None, None)])[-1][1]
    eps = pub("eps")
    if len(eps) < 3 or not precio:
        return None
    eps10 = [v for _, v in eps[-10:]]
    eps3 = sum(v for _, v in eps[-3:]) / 3
    ac, pc, dlp, pat, acc = ult("act_corr"), ult("pas_corr"), ult("deuda_lp"), ult("patrimonio"), ult("acciones")
    ventas = ult("ventas")
    bvps = pat / acc if pat and acc else None
    divs = pub("div") or pub("div_pagados")
    anios_div = len([1 for _, v in divs[-10:] if v and v > 0])
    crit = {}
    crit["tamano"] = (ventas or 0) >= float(cfg.get("tamano", {}).get("minimo_ventas_usd", 2e9))
    crit["solidez"] = bool(ac and pc and ac / pc >= cfg.get("solidez", {}).get("ratio_corriente", 2.0))
    crit["deuda"] = bool(ac and pc and (dlp or 0) <= (ac - pc)) if ac and pc else False
    crit["estabilidad"] = all(v > 0 for v in eps10)
    crit["dividendos"] = bool(divs) and anios_div >= min(len(divs[-10:]), 10) and anios_div >= 3
    viejo = sum(eps10[:3]) / 3 if len(eps10) >= 6 else None
    crit["crecimiento"] = bool(viejo and viejo > 0 and eps3 / viejo - 1 >= cfg.get("crecimiento", {}).get("crec_min", 0.33))
    pe3 = precio / eps3 if eps3 > 0 else None
    pb = precio / bvps if bvps and bvps > 0 else None
    crit["precio"] = bool(pe3 and pe3 <= 15 and (pb is None or pe3 * pb <= 22.5))
    ng = math.sqrt(22.5 * eps[-1][1] * bvps) if bvps and bvps > 0 and eps[-1][1] > 0 else None
    return {"cumple": sum(crit.values()), "criterios": crit, "pe3": round(pe3, 1) if pe3 else None, "pb": round(pb, 2) if pb else None,
            "numero_graham": round(ng, 2) if ng else None, "margen_pct": round((ng / precio - 1) * 100) if ng else None,
            "anios_eps": len(eps10), "al": eps[-1][0]}


def frase(ev: dict | None) -> str:
    """En criollo, para la ficha en frío."""
    if not ev:
        return ""
    cfg = _graham_cfg()
    si = [k for k, v in ev["criterios"].items() if v]
    no = [k for k, v in ev["criterios"].items() if not v]
    corto = {"tamano": "grande", "solidez": "finanzas sólidas", "deuda": "poca deuda", "estabilidad": "gana todos los años",
             "dividendos": "paga dividendos", "crecimiento": "crece", "precio": "precio moderado"}
    t = f"📚 Graham (El inversor inteligente): cumple {ev['cumple']} de 7 criterios del inversor defensivo"
    if si:
        t += f" (sí: {', '.join(corto[k] for k in si)}"
        t += f"; no: {', '.join(corto[k] for k in no)})" if no else ")"
    if ev.get("margen_pct") is not None:
        m = ev["margen_pct"]
        t += (f". Margen de seguridad: según su fórmula valdría {m}% más que el precio" if m > 0 else
              f". Sin margen de seguridad: el precio está {abs(m)}% arriba de lo que valdría según su fórmula")
    elif cfg:
        t += ". Su fórmula de valor no se puede calcular (pierde plata o patrimonio negativo)"
    # 20/11, probado con 635 balances de 58 empresas (2011-2025), a 12 meses contra el S&P 500
    return t + (". Probado: las que cumplen 5 o más le ganaron al S&P 56 de cada 100 años (+2,3%); las que pierden plata quedaron 7% abajo."
                " Es una mirada de un año, no de semanas: dato, no voto.")


def actualizar(a, universo: list[str], hoy: date, maximo: int = 25) -> dict:
    """Semanal por empresa (la SEC pide no abusar). Usa el precio en dólares que ya guardó fundamentos."""
    from concurrent.futures import ThreadPoolExecutor
    from .fundamentos import NO_EMPRESA, _ciks
    tabla = a.get(CLAVE) or {}
    fund = a.get("fundamentos/cedears") or {}
    emp = [t for t in universo if t not in NO_EMPRESA]
    viejo = (hoy - timedelta(days=7)).isoformat()
    pend = [t for t in emp if (tabla.get(t) or {}).get("sec_fecha", "") < viejo][:maximo]
    if pend:
        try:
            cik = _ciks()
        except Exception as ex:
            print(f"[biblioteca] SEC: {ex}")
            cik = {}

        def uno(t):
            c = cik.get(t.replace(".", "-"))
            try:
                return t, (datos_sec(c) if c else None)
            except Exception as ex:
                print(f"[biblioteca] {t}: {ex}")
                return t, False
        with ThreadPoolExecutor(4) as ex:
            for t, s in ex.map(uno, pend):
                if s is False:
                    continue
                pr = (fund.get(t) or {}).get("precio_usd")
                ev = evaluar(s, pr) if s and pr else None
                tabla[t] = {"sec_fecha": hoy.isoformat(), **({"ev": ev, "frase": frase(ev)} if ev else {"sin_datos": True})}
    a.put(CLAVE, tabla)
    print(f"[biblioteca] Graham: {len(pend)} empresas revisadas")
    return tabla


def de(a, ticker: str) -> str:
    t = ticker.upper()
    tabla = a.get(CLAVE) or {}
    x = tabla.get(t) or (tabla.get(t[:-1]) if t[-1:] in ("D", "C") else None) or {}
    return x.get("frase") or ""


def leccion(situaciones: list[str], semana: int) -> dict | None:
    """La lección de la semana: la idea que mejor encaja con lo que pasó; si no hay, rota."""
    ideas = [(lb, i) for lb in libros() for i in lb.get("ideas") or []]
    if not ideas:
        return None
    for s in situaciones:
        for lb, i in ideas:
            if s in (i.get("situaciones") or []):
                return {"libro": lb["titulo"], "autor": lb["autor"], **i}
    lb, i = ideas[semana % len(ideas)]
    return {"libro": lb["titulo"], "autor": lb["autor"], **i}
