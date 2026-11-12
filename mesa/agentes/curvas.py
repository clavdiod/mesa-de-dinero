"""Dólar, tasas e inflación esperada (12/11). Pedido de Clau tras ver El Dashboard: sumar lo que le falta a la mesa para
decidir en pesos.

- Banda cambiaria: el techo se actualiza todos los días con la inflación de dos meses atrás (noviembre usa la de septiembre).
  Qué tan cerca está el dólar mayorista (A3500) del techo.
- Dólar futuro (A3): cuánta devaluación espera el mercado mes a mes.
- Bonos CER: tasa real; contra una LECAP de plazo parecido da la INFLACIÓN QUE ESPERA EL MERCADO (breakeven).
- Tasas de referencia: TAMAR, BADLAR, plazo fijo.
Con eso, la pregunta de los pesos: ¿la LECAP le gana a la devaluación esperada? ¿y a la inflación?
Solo información para decidir: no vota.
"""
from __future__ import annotations

import bisect
from datetime import date, timedelta


def _m(d: date) -> tuple[int, int]:
    return d.year, d.month


def techo_banda(hoy: date, ancla_fecha: str, ancla_techo: float, inflacion: dict[str, float]) -> float | None:
    """Desde el techo del último día de un mes (ancla), se actualiza día a día con la inflación de dos meses atrás.
    inflacion: {'AAAA-MM-..': % mensual}."""
    infl = {k[:7]: v for k, v in inflacion.items()}
    d, techo = date.fromisoformat(ancla_fecha), float(ancla_techo)
    while d < hoy:
        d2 = d + timedelta(days=1)
        y, m = _m(d2)
        ref = f"{y if m > 2 else y - 1}-{(m - 2 - 1) % 12 + 1:02d}"
        pi = infl.get(ref)
        if pi is None:  # sin el dato todavía: el último conocido
            pi = infl[max(infl)] if infl else 0
        dias_mes = ((date(y + (m == 12), m % 12 + 1, 1)) - date(y, m, 1)).days
        techo *= (1 + pi / 100) ** (1 / dias_mes)
        d = d2
    return round(techo, 2)


def _cer_en(cer: dict[str, float], d: date, habiles_antes: int = 10) -> float | None:
    """CER de 10 días hábiles antes (aprox.: se saltean fines de semana)."""
    k, x = 0, d
    while k < habiles_antes:
        x -= timedelta(days=1)
        if x.weekday() < 5:
            k += 1
    fs = sorted(cer)
    i = bisect.bisect_right(fs, x.isoformat()) - 1
    return cer[fs[i]] if i >= 0 else None


def armar(hoy: date, bcra: dict, futuros: list[dict], cer_bonos: list[dict], cer: dict[str, float],
          lecaps: list[dict], inflacion: dict[str, float], banda_cfg: dict, rem_12m: float | None = None) -> dict:
    a3500 = (bcra.get("a3500") or {}).get("valor")
    out = {"fecha": hoy.isoformat(), "lineas": []}
    # banda
    techo = techo_banda(hoy, banda_cfg["ancla_fecha"], banda_cfg["ancla_techo"], inflacion) if banda_cfg else None
    if techo and a3500:
        dist = (techo / a3500 - 1) * 100
        out["banda"] = {"a3500": a3500, "techo": techo, "distancia_pct": round(dist, 1)}
        ar = lambda x, d=2: f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        out["lineas"].append(f"Dólar mayorista {ar(a3500)} y techo de la banda {ar(techo)}: le queda {ar(dist, 1)}% para llegar al techo."
                             + (" Cerca del techo: más presión sobre bonos y acciones." if dist < 5 else " Lejos del techo: el BCRA no necesita intervenir."))
    # dólar futuro
    fut = []
    for f in futuros or []:
        dias = (date.fromisoformat(f["vence"]) - hoy).days
        if dias < 5 or not a3500:
            continue
        r = f["precio"] / a3500
        fut.append({**f, "dias": dias, "devaluacion_total_pct": round((r - 1) * 100, 2), "devaluacion_mensual_pct": round((r ** (30 / dias) - 1) * 100, 2),
                    "tna_pct": round((r - 1) * 365 / dias * 100, 1)})
    out["futuros"] = fut
    # bonos CER: tasa real
    reales = []
    cer_hoy = _cer_en(cer, hoy)
    for b in cer_bonos or []:
        em, vt = date.fromisoformat(b["emision"]), date.fromisoformat(b["vence"])
        c_em = _cer_en(cer, em)
        dias = (vt - hoy).days
        if not (c_em and cer_hoy) or dias < 20:
            continue
        valor = 100 * cer_hoy / c_em
        t = dias / 365
        r = (valor / b["precio"]) ** (1 / t) - 1
        reales.append({**b, "dias": dias, "valor_tecnico": round(valor, 2), "tir_real_pct": round(r * 100, 1),
                       "tem_real_pct": round(((1 + r) ** (1 / 12) - 1) * 100, 2)})
    out["cer"] = sorted(reales, key=lambda x: x["vence"])
    # inflación que espera el mercado: LECAP contra CER de plazo parecido
    pares = []
    for le in lecaps or []:
        cerca = min(reales, key=lambda x: abs(x["dias"] - le["dias"]), default=None)
        if cerca and abs(cerca["dias"] - le["dias"]) <= 75:
            be = ((1 + le["tem"] / 100) / (1 + cerca["tem_real_pct"] / 100) - 1) * 100
            pares.append({"lecap": le["ticker"], "cer": cerca["ticker"], "vence": le["vence"], "tem_lecap": le["tem"],
                          "tem_real_cer": cerca["tem_real_pct"], "inflacion_implicita_mensual": round(be, 2)})
    out["breakeven"] = pares
    rem_m = ((1 + rem_12m / 100) ** (1 / 12) - 1) * 100 if rem_12m else None
    if pares:
        p = pares[len(pares) // 2]
        out["lineas"].append(f"Inflación que espera el mercado: {p['inflacion_implicita_mensual']:.1f}% por mes (LECAP {p['lecap']} contra CER {p['cer']})."
                             .replace(".", ",", 1)
                             + (f" Los economistas (REM) esperan {rem_m:.1f}% por mes.".replace(".", ",", 1) if rem_m else "")
                             + " Si creés que la inflación va a ser MÁS alta que eso, conviene el CER; si más baja, la LECAP.")
    # pesos contra dólar: la LECAP le gana a la devaluación esperada?
    if lecaps and fut:
        le = min(lecaps, key=lambda x: abs(x["dias"] - 90))
        fu = min(fut, key=lambda x: abs(x["dias"] - le["dias"]))
        dif = le["tem"] - fu["devaluacion_mensual_pct"]
        out["carry"] = {"lecap": le["ticker"], "tem": le["tem"], "futuro": fu["contrato"], "devaluacion_mensual": fu["devaluacion_mensual_pct"], "diferencia": round(dif, 2)}
        out["lineas"].append(f"Pesos contra dólar: la LECAP {le['ticker']} paga {le['tem']:.2f}% por mes y el dólar futuro {fu['contrato']} descuenta {fu['devaluacion_mensual_pct']:.2f}% de devaluación por mes: "
                             .replace(".", ",")
                             + ("quedarse en pesos rinde más, si el dólar no se dispara por encima de lo esperado." if dif > 0.3 else
                                "es casi lo mismo: no hay premio por quedarse en pesos." if dif > -0.3 else "el mercado espera más devaluación que la tasa: conviene dolarizarse."))
    tasas = {k: (bcra.get(k) or {}).get("valor") for k in ("tamar", "badlar", "plazo_fijo")}
    out["tasas"] = tasas
    if any(tasas.values()):
        out["lineas"].append("Tasas de referencia (anual): " + ", ".join(f"{n} {v:.1f}%".replace(".", ",") for n, v in
                                                                          (("TAMAR", tasas["tamar"]), ("BADLAR", tasas["badlar"]), ("plazo fijo", tasas["plazo_fijo"])) if v) + ".")
    return out
