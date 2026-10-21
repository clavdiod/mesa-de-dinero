"""19. Noche de Nueva York (ADRs): lo que pasó en Wall Street después del cierre de Buenos Aires.

Las acciones argentinas cotizan también en Nueva York (ADRs) hasta las 18 h, una hora después del cierre
local. Si el ADR (pasado a pesos con el CCL) se movió distinto que la acción local, al día siguiente la local
suele "ponerse al día". No hace falta saber el ratio de conversión: se comparan variaciones.

  brecha = (variación del ADR + variación del CCL) − variación de la acción local, del mismo día.

Solo opina en las primeras rondas del día y descuenta lo que la acción local ya se movió hoy (si ya
se puso al día en la apertura, no queda nada para ganar).
"""
from __future__ import annotations

from ..nucleo.modelos import Senal

# acción local -> ADR en Nueva York
ADRS = {"GGAL": "GGAL", "YPFD": "YPF", "PAMP": "PAM", "BMA": "BMA", "CEPU": "CEPU", "TGSU2": "TGS",
        "SUPV": "SUPV", "LOMA": "LOMA", "TECO2": "TEO", "CRES": "CRESY", "EDN": "EDN", "IRSA": "IRS", "BBAR": "BBAR"}


def _ret(serie: dict[str, float], fecha: str) -> float | None:
    """Variación % del día `fecha` contra el día hábil anterior de la misma serie."""
    fs = sorted(f for f in serie if f <= fecha)
    if len(fs) < 2 or fs[-1] != fecha:
        return None
    return (serie[fs[-1]] / serie[fs[-2]] - 1) * 100


def brecha(local: dict[str, float], adr: dict[str, float], ccl: dict[str, float], fecha: str) -> float | None:
    rl, ra, rc = _ret(local, fecha), _ret(adr, fecha), _ret(ccl, fecha)
    if rl is None or ra is None or rc is None:
        return None
    return round(ra + rc - rl, 3)


def entrenar(locales: dict[str, list[dict]], adrs: dict[str, list[list]], ccl: dict[str, float], umbral: float = 1.5) -> dict:
    """Prueba con la historia, de forma realista: la brecha se conoce a la noche, así que se mide lo que pasa
    DESDE LA APERTURA del día siguiente hasta su cierre (y hasta el cierre del subsiguiente)."""
    from ..nucleo.calibracion import _sumar, banda
    stats = {"total": {}, "bandas": {}, "por_horizonte": {"cierre_sig": {}, "dos_dias": {}, "al_cierre_ideal": {}}}
    for loc, ad in ADRS.items():
        velas = locales.get(loc) or []
        serie_adr = {f: c for f, c in adrs.get(ad, [])}
        if len(velas) < 30 or len(serie_adr) < 30:
            continue
        cierres = {v["fecha"]: v["cierre"] for v in velas}
        for i, v in enumerate(velas[1:-2], start=1):
            b = brecha(cierres, serie_adr, ccl, v["fecha"])
            if b is None or abs(b) < umbral:
                continue
            d = 1 if b > 0 else -1
            sig, sig2 = velas[i + 1], velas[i + 2]
            if not sig.get("apertura"):
                continue
            r_real = (sig["cierre"] / sig["apertura"] - 1) * 100 * d      # comprar en la apertura, vender al cierre
            r_2 = (sig2["cierre"] / sig["apertura"] - 1) * 100 * d
            r_ideal = (sig["cierre"] / v["cierre"] - 1) * 100 * d         # (no se puede: la brecha se conoce después)
            f = min(0.8, 0.3 + abs(b) / 10)
            _sumar(stats["total"], r_2, f)
            _sumar(stats["bandas"].setdefault(banda(f), {}), r_2, f)
            _sumar(stats["por_horizonte"]["cierre_sig"], r_real, f)
            _sumar(stats["por_horizonte"]["dos_dias"], r_2, f)
            _sumar(stats["por_horizonte"]["al_cierre_ideal"], r_ideal, f)
    return stats


def senales_en(ctx, datos: dict, ccl_series: dict[str, float], minuto: int, umbral: float = 1.5) -> tuple[list[Senal], list[dict]]:
    """Opina en la primera parte del día (hasta las 13 h) con la brecha de la noche anterior."""
    out, tabla = [], []
    if minuto > 13 * 60:
        return out, tabla
    adrs = datos.get("adrs") or {}
    for loc, ad in ADRS.items():
        t = ctx.titulo(loc)
        velas = ctx.cache.velas(loc) if ctx.cache else []
        serie_adr = {f: c for f, c in adrs.get(ad, [])}
        if not t or not t.get("ultimo") or len(velas) < 2 or not serie_adr:
            continue
        ayer = velas[-1]["fecha"] if velas[-1]["fecha"] < ctx.fecha.isoformat() else velas[-2]["fecha"]
        cierres = {v["fecha"]: v["cierre"] for v in velas if v["fecha"] <= ayer}
        b = brecha(cierres, serie_adr, ccl_series, ayer)
        if b is None:
            continue
        hoy_local = (t["ultimo"] / cierres[ayer] - 1) * 100
        resta = round(b - hoy_local, 2)
        tabla.append({"ticker": loc, "adr": ad, "brecha": b, "hoy": round(hoy_local, 2), "resta": resta})
        if abs(resta) >= umbral and (b > 0) == (resta > 0):
            d = 1 if resta > 0 else -1
            out.append(Senal("adr", loc, d, round(min(0.8, 0.3 + abs(resta) / 10), 2),
                             f"Anoche en Nueva York el ADR {ad} (con el CCL) quedó {b:+.1f}% contra el cierre local; hoy {loc} va {hoy_local:+.1f}%: "
                             f"le falta {resta:+.1f}% para ponerse al día.", {"brecha": b, "hoy": hoy_local, "resta": resta}))
    return out, tabla
