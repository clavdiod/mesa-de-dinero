"""25. El Ministro: mira el mercado con los ojos del Ministerio de Economía (hoy, Luis "Toto" Caputo).

No inventa declaraciones ni habla en nombre de nadie: sigue lo que el Ministerio y el BCRA hacen y publican, que es
lo que mueve a bonos, bancos, pesos y dólar en Argentina:
- Reservas del BCRA y compras de dólares (si se acumulan, baja el riesgo país).
- Tasa real: tasa en pesos (TAMAR) contra la inflación esperada (si es alta, conviene el "carry" en pesos).
- Inflación: tendencia de los últimos meses.
- Dólar mayorista: si se acelera, los CEDEARs cubren.
- Pagos de deuda en dólares (9 de enero y 9 de julio): con reservas que suben, el pago está asegurado.
- Licitaciones del Tesoro (rollover) y titulares del Ministro (últimas 48 h).
Fuente: API pública del BCRA (gratis) y noticias. Cada regla se prueba con la historia; la que no demuestra
que gana plata queda como dato, sin voto.
"""
from __future__ import annotations

import re
import statistics as st
from datetime import date, timedelta

from ..nucleo.modelos import Senal

BCRA = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/{id}"
VARIABLES = {"reservas": 1, "compras": 47, "tc": 5, "tamar": 44, "inflacion": 27, "expectativa": 29, "base": 15}
SOBERANOS = ["AL30", "GD30", "AL35", "GD35", "AE38", "GD38", "AL41", "GD41"]
BANCOS = ["GGAL", "BMA", "SUPV", "BBAR"]
COBERTURA = ["SPY", "QQQ", "GLD"]


def bajar_series(desde: date, hasta: date) -> dict[str, dict[str, float]]:
    from ..datos.gratis import _S
    out = {}
    for nombre, i in VARIABLES.items():
        try:
            j = _S.get(BCRA.format(id=i), params={"desde": desde.isoformat(), "hasta": hasta.isoformat(), "limit": 3000}, timeout=40).json()
            det = (j.get("results") or [{}])[0].get("detalle") or []
            out[nombre] = {d["fecha"]: float(d["valor"]) for d in det if d.get("valor") is not None}
        except Exception as ex:
            print(f"[ministro] {nombre}: {ex}")
            out[nombre] = {}
    return out


def _hasta(s: dict[str, float], f: str) -> list[tuple[str, float]]:
    return sorted((k, v) for k, v in s.items() if k <= f)


def foto(series: dict[str, dict[str, float]], fecha: str) -> dict:
    r = _hasta(series.get("reservas") or {}, fecha)
    c = _hasta(series.get("compras") or {}, fecha)
    tc = _hasta(series.get("tc") or {}, fecha)
    tamar = _hasta(series.get("tamar") or {}, fecha)
    inf = _hasta(series.get("inflacion") or {}, fecha)
    exp = _hasta(series.get("expectativa") or {}, fecha)
    out: dict = {"fecha": fecha}
    if len(r) > 21:
        out["reservas"] = r[-1][1]
        out["reservas_20d"] = round(r[-1][1] - r[-21][1])
    if c and tc:
        tc_ult = tc[-1][1]
        out["compras_20d"] = round(sum(v for _, v in c[-20:]) / tc_ult)  # millones de pesos -> millones de dólares
    if len(tc) > 21:
        out["tc"] = tc[-1][1]
        out["tc_20d_pct"] = round((tc[-1][1] / tc[-21][1] - 1) * 100, 2)
    if inf:
        out["inflacion"] = inf[-1][1]
        if len(inf) >= 4:
            out["inflacion_tendencia"] = round(inf[-1][1] - st.mean(v for _, v in inf[-4:-1]), 2)
    if tamar and exp:
        out["tasa_real"] = round(tamar[-1][1] - exp[-1][1], 1)  # TAMAR anual menos inflación esperada a 12 meses
        out["tamar"] = tamar[-1][1]
        out["expectativa"] = exp[-1][1]
    d = date.fromisoformat(fecha)
    pagos = [date(d.year, 1, 9), date(d.year, 7, 9), date(d.year + 1, 1, 9)]
    prox = min(p for p in pagos if p >= d)
    out["dias_pago_deuda"] = (prox - d).days
    out["pago_deuda"] = prox.isoformat()
    return out


# reglas: (clave, condición sobre la foto, efectos {ticker: dirección}, texto)
REGLAS = [
    ("acumula", lambda f: (f.get("reservas_20d") or 0) >= 500 or (f.get("compras_20d") or 0) >= 500,
     {**{t: 1 for t in SOBERANOS}, **{t: 1 for t in BANCOS}},
     "El BCRA acumula dólares: el Ministerio puede pagar la deuda con holgura y el riesgo país tiende a bajar."),
    ("pierde", lambda f: (f.get("reservas_20d") or 0) <= -1000,
     {t: -1 for t in SOBERANOS},
     "Las reservas caen fuerte: el mercado duda del pago y los bonos sufren."),
    ("tasa_real_alta", lambda f: (f.get("tasa_real") or 0) >= 6,
     {t: -1 for t in COBERTURA},
     "Tasa real en pesos alta: al Ministerio le sirve para sostener el peso; conviene el carry en pesos antes que cubrirse."),
    ("tasa_real_negativa", lambda f: f.get("tasa_real") is not None and f["tasa_real"] < 0,
     {t: 1 for t in COBERTURA},
     "Tasa real negativa: el peso rinde menos que la inflación; cubrirse en dólares (CEDEARs)."),
    ("inflacion_baja", lambda f: (f.get("inflacion_tendencia") or 0) <= -0.3,
     {t: 1 for t in BANCOS},
     "La inflación viene bajando: el programa del Ministerio funciona; los bancos ganan con más crédito."),
    ("dolar_acelera", lambda f: (f.get("tc_20d_pct") or 0) >= 4,
     {**{t: 1 for t in COBERTURA}, **{t: -1 for t in BANCOS}},
     "El dólar mayorista se acelera: presión cambiaria; los CEDEARs cubren y los bancos sufren."),
    ("pago_cerca_con_reservas", lambda f: (f.get("dias_pago_deuda") or 999) <= 45 and (f.get("reservas_20d") or 0) > 0,
     {t: 1 for t in SOBERANOS},
     "Se acerca el pago de deuda y las reservas suben: el pago está asegurado; históricamente los bonos suben antes del cobro."),
]


def senales(f: dict, existe, activas: dict | None = None) -> list[Senal]:
    """activas: {regla: True/False} según la prueba con la historia. Las no probadas votan con fuerza mínima."""
    out = []
    for clave, cond, efectos, texto in REGLAS:
        try:
            if not cond(f):
                continue
        except Exception:
            continue
        estado = (activas or {}).get(clave)
        if estado is False:
            continue  # la historia dijo que no gana plata: queda como dato en la lectura
        fuerza = 0.45 if estado else 0.25
        for tk, d in efectos.items():
            if existe(tk):
                out.append(Senal("ministro", tk, d, fuerza, f"Ministro: {texto}", {"regla": clave, "probada": bool(estado)}))
    return out


def lectura(f: dict, activas: dict | None = None) -> dict:
    act = []
    for clave, cond, efectos, texto in REGLAS:
        try:
            if cond(f):
                act.append({"regla": clave, "texto": texto, "estado": (activas or {}).get(clave)})
        except Exception:
            pass
    return {"foto": f, "reglas": act}


def rollover(titulares: list[dict]) -> float | None:
    for n in titulares:
        m = re.search(r"rollover (?:de|del)?\s*(\d{2,3}(?:[.,]\d+)?)\s?%", n.get("titulo", ""), re.I)
        if m:
            return float(m.group(1).replace(",", "."))
    return None


def entrenar(series: dict[str, dict[str, float]], cierres: dict[str, dict[str, float]], horizonte: int = 20, paso: int = 5) -> dict:
    """Prueba cada regla con la historia: si se cumplía, ¿qué hicieron sus papeles en las 20 ruedas siguientes?"""
    from ..nucleo.calibracion import _sumar
    fechas = sorted(set().union(*[set(s) for s in cierres.values()])) if cierres else []
    stats: dict[str, dict] = {}
    for i in range(30, len(fechas) - horizonte, paso):
        fe = fechas[i]
        f = foto(series, fe)
        for clave, cond, efectos, _ in REGLAS:
            try:
                if not cond(f):
                    continue
            except Exception:
                continue
            for tk, d in efectos.items():
                s = cierres.get(tk) or {}
                p0, p1 = s.get(fe), s.get(fechas[i + horizonte])
                if p0 and p1:
                    _sumar(stats.setdefault(clave, {}), (p1 / p0 - 1) * 100 * d, 0.4)
    activas = {}
    for k, v in stats.items():
        hit, ret = (v["aciertos"] / v["casos"], v["suma_ret"] / v["casos"]) if v.get("casos") else (0, 0)
        if v.get("casos", 0) >= 30:
            activas[k] = hit >= 0.52 and ret > 1.2
        elif v.get("casos", 0) >= 15 and ret < 0:
            activas[k] = False  # pocos casos pero claramente en contra: no vota
    return {"stats": stats, "activas": activas, "horizonte": horizonte}
