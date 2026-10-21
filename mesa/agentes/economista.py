"""16. Economista: lee el contexto macro argentino, define el régimen del mercado y les enseña al resto.

Mira cuatro cosas (series gratis de argentinadatos + la ronda):
- Riesgo país a 20 ruedas: si baja, el mercado le cree más a la Argentina (suben bonos en dólares,
  bancos y acciones locales); si sube, es al revés.
- Dólar CCL a 20 ruedas y brecha con el oficial: si se acelera, conviene cubrirse (CEDEARs); si está
  calmo, el peso rinde (carry).
- Tasa real en pesos: caución mensual menos la última inflación. Positiva = el plazo fijo/LECAP le gana
  a la inflación y compite con las acciones.
- Inflación del último mes (tendencia).

Con eso arma una inclinación (−1 a +1) por categoría: acciones locales, bancos, energía, servicios
públicos, bonos en dólares, CEDEARs y pesos. "Enseña" de dos formas:
1. Opina él mismo en los papeles que la mesa está mirando (con voto calibrado como cualquier agente).
2. Ajusta cuánto se les cree a los demás: una señal a favor del régimen pesa más (hasta ×1,25) y una
   en contra pesa menos (hasta ×0,75). Ese ajuste se prueba con la historia antes de confiar en él.
"""
from __future__ import annotations

import bisect
from datetime import date, timedelta

from ..nucleo.config import sector
from ..nucleo.modelos import Senal

CATEGORIAS = {"acciones": "acciones locales", "bancos": "bancos", "energia": "energía", "utilities": "servicios públicos",
              "bonos_usd": "bonos en dólares", "cedears": "CEDEARs", "pesos": "pesos (LECAP/caución)"}


def categoria(ticker: str, grupo: str | None) -> str | None:
    if grupo == "cedears":
        return "cedears"
    if grupo == "soberanos":
        return "bonos_usd"
    if grupo in ("letras", "cauciones"):
        return "pesos"
    if grupo == "acciones":
        sec = sector(ticker)
        return sec if sec in ("bancos", "energia", "utilities") else "acciones"
    return None


def _valor_en(serie: dict[str, float], fecha: str) -> float | None:
    if not serie:
        return None
    fechas = sorted(serie)
    i = bisect.bisect_right(fechas, fecha) - 1
    return serie[fechas[i]] if i >= 0 else None


def foto(series: dict, fecha: date, rp_hoy: float | None = None, ccl_hoy: float | None = None,
         caucion_tna: float | None = None) -> dict:
    """Foto macro a una fecha (sirve en vivo y para rebobinar la historia sin mirar el futuro)."""
    f, f20 = fecha.isoformat(), (fecha - timedelta(days=28)).isoformat()  # ~20 ruedas
    rp, ccl, of = series.get("riesgo_pais") or {}, series.get("ccl") or {}, series.get("oficial") or {}
    infl = series.get("inflacion") or {}
    corte = (fecha - timedelta(days=15)).isoformat()  # el INDEC publica a mitad del mes siguiente: sin mirar el futuro
    infl_prev = [infl[k] for k in sorted(infl) if k < corte]
    return {"fecha": f, "rp": rp_hoy or _valor_en(rp, f), "rp_20": _valor_en(rp, f20),
            "ccl": ccl_hoy or _valor_en(ccl, f), "ccl_20": _valor_en(ccl, f20),
            "oficial": _valor_en(of, f), "oficial_20": _valor_en(of, f20),
            "inflacion": infl_prev[-1] if infl_prev else None, "inflacion_prev": infl_prev[-2] if len(infl_prev) > 1 else None,
            "caucion_tna": caucion_tna}


def regimen(fx: dict) -> dict:
    """Lectura del contexto + inclinación por categoría + la 'clase' en castellano."""
    t = {k: 0.0 for k in CATEGORIAS}
    lineas, ensena = [], []
    # 1) riesgo país
    rp, rp20 = fx.get("rp"), fx.get("rp_20")
    if rp and rp20:
        d = rp - rp20
        if d <= -30:
            fuerza = min(1.0, -d / 100)
            for k, w in (("bonos_usd", 1.0), ("bancos", 1.0), ("acciones", 0.8), ("energia", 0.7), ("utilities", 0.7)):
                t[k] += w * fuerza
            lineas.append(f"Riesgo país en baja: {rp:.0f} puntos, {d:+.0f} en un mes. El mercado le presta más barato a la Argentina: "
                          "suelen subir los bonos en dólares y, detrás, los bancos y las acciones locales.")
            ensena.append("Con riesgo país en baja, creerles más a las compras de bancos, acciones locales y bonos.")
        elif d >= 30:
            fuerza = min(1.0, d / 100)
            for k, w in (("bonos_usd", -1.0), ("bancos", -1.0), ("acciones", -0.8), ("energia", -0.6), ("utilities", -0.7), ("cedears", 0.5)):
                t[k] += w * fuerza
            lineas.append(f"Riesgo país en alza: {rp:.0f} puntos, {d:+.0f} en un mes. Sube el costo de financiarse y el mercado se defiende: "
                          "presión vendedora en bonos, bancos y acciones locales; los CEDEARs funcionan como refugio.")
            ensena.append("Con riesgo país en alza, desconfiar de las compras de bancos y acciones locales; preferir CEDEARs.")
        else:
            lineas.append(f"Riesgo país estable en {rp:.0f} puntos ({d:+.0f} en un mes): no empuja para ningún lado.")
    # 2) dólar y brecha
    ccl, ccl20, of, of20 = fx.get("ccl"), fx.get("ccl_20"), fx.get("oficial"), fx.get("oficial_20")
    presion = calma = False
    if ccl and ccl20:
        v = (ccl / ccl20 - 1) * 100
        brecha = (ccl / of - 1) * 100 if of else None
        brecha20 = (ccl20 / of20 - 1) * 100 if of20 else None
        txt_b = f" La brecha con el oficial es {brecha:.1f}%" + (f" ({brecha - brecha20:+.1f} puntos en el mes)." if brecha20 is not None else ".") if brecha is not None else ""
        if v >= 3 or (brecha is not None and brecha20 is not None and brecha - brecha20 >= 3):
            presion = True
            t["cedears"] += min(1.0, v / 6 + 0.3)
            t["pesos"] -= min(1.0, v / 6 + 0.3)
            lineas.append(f"Dólar CCL acelerando: {v:+.1f}% en un mes.{txt_b} Cuando el dólar se mueve, los CEDEARs cubren y los pesos pierden.")
            ensena.append("Con el dólar acelerando, valorar más las compras de CEDEARs y desconfiar de quedarse en pesos.")
        elif v <= 1:
            calma = True
            t["pesos"] += 0.4
            t["cedears"] -= 0.3
            lineas.append(f"Dólar calmo: CCL {v:+.1f}% en un mes.{txt_b} Con el dólar quieto, la tasa en pesos rinde en dólares (carry).")
        else:
            lineas.append(f"Dólar CCL {v:+.1f}% en un mes, sin sobresaltos.{txt_b}")
    # 3) tasa real en pesos
    infl, tna = fx.get("inflacion"), fx.get("caucion_tna")
    if infl is not None and tna:
        real = tna / 12 - infl
        if real >= 0.5:
            t["pesos"] += 0.5 if not presion else 0.2
            for k in ("acciones", "bancos", "energia", "utilities"):
                t[k] -= 0.2
            lineas.append(f"Tasa real positiva: la caución rinde {tna / 12:.1f}% por mes contra {infl:.1f}% de inflación ({real:+.1f} puntos). "
                          "La plata en pesos le gana a la inflación y compite con las acciones: pide más a una compra de acciones.")
            ensena.append("Con tasa real positiva, una compra de acciones tiene que prometer bastante más que la tasa en pesos.")
        elif real <= -0.5:
            t["pesos"] -= 0.5
            lineas.append(f"Tasa real negativa: la caución rinde {tna / 12:.1f}% por mes y la inflación fue {infl:.1f}%. Quedarse en pesos pierde poder de compra.")
    if infl is not None and fx.get("inflacion_prev") is not None:
        di = infl - fx["inflacion_prev"]
        if abs(di) >= 0.3:
            lineas.append(f"La inflación {'subió' if di > 0 else 'bajó'} de {fx['inflacion_prev']:.1f}% a {infl:.1f}% mensual: "
                          + ("si sigue, presiona tasas y dólar." if di > 0 else "ayuda a que bajen tasas y riesgo país."))
    t = {k: round(max(-1.0, min(1.0, v)), 2) for k, v in t.items()}
    favor = [CATEGORIAS[k] for k, v in sorted(t.items(), key=lambda x: -x[1]) if v >= 0.4]
    contra = [CATEGORIAS[k] for k, v in sorted(t.items(), key=lambda x: x[1]) if v <= -0.4]
    titulo = ("Favorece: " + ", ".join(favor) if favor else "Sin sesgo claro") + (". Evitar: " + ", ".join(contra) if contra else "")
    return {"fecha": fx.get("fecha"), "inclinacion": t, "titulo": titulo, "clase": lineas, "ensena": ensena, "foto": fx}


def senales(ctx, reg: dict, tickers: list[str]) -> list[Senal]:
    """El economista opina en los papeles que la mesa está mirando, según su categoría."""
    out = []
    for tk in dict.fromkeys(tickers):
        t = ctx.titulo(tk)
        cat = categoria(tk, (t or {}).get("grupo"))
        v = reg["inclinacion"].get(cat, 0.0) if cat else 0.0
        if abs(v) < 0.5:
            continue
        out.append(Senal("economista", tk, 1 if v > 0 else -1, round(min(0.6, 0.15 + 0.45 * abs(v)), 2),
                         f"Contexto macro {'a favor' if v > 0 else 'en contra'} de {CATEGORIAS[cat]}: {reg['titulo']}.",
                         {"categoria": cat, "inclinacion": v}))
    return out


def multiplicador(reg: dict | None, ctx, ticker: str, direccion: int) -> float:
    """Cuánto creerle a la señal de otro agente según el régimen (×0,75 a ×1,25)."""
    if not reg or not direccion:
        return 1.0
    cat = categoria(ticker, (ctx.titulo(ticker) or {}).get("grupo"))
    v = reg["inclinacion"].get(cat, 0.0) if cat else 0.0
    return round(1 + 0.25 * v * direccion, 3)
