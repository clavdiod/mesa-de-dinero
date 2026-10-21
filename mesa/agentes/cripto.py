"""18. Cripto: la visión de un trader de bolsa y bitcoin, aplicada a la mesa argentina.

Aporta dos cosas que ningún otro agente mira:
1. Bitcoin como termómetro del apetito por riesgo (opera 24/7, reacciona primero). Opina directo sobre los
   CEDEARs ligados a cripto (IBIT, MSTR, COIN, HUT...) según la tendencia de BTC.
2. El dólar cripto argentino (USDT en pesos), que cotiza también de noche y los fines de semana: si se
   despega del CCL puede anticipar hacia dónde va el dólar de bolsa (y con él los CEDEARs en pesos).

"Aprende del resto": antes de opinar sobre un papel mira qué dice el agente con mejor historial demostrado
(el de mayor voto calibrado); si opina distinto, baja su convicción a la mitad y lo dice.
Todo se prueba con la historia; si no aporta, su voto queda en el mínimo (o se lo discontinúa).
"""
from __future__ import annotations

from ..nucleo.modelos import Senal

CEDEARS_CRIPTO = ["IBIT", "MSTR", "COIN", "HUT", "BITF", "MARA", "RIOT", "ETHA", "BLOCK", "SQ"]


def _hasta(serie: list[list], fecha: str) -> list[float]:
    return [c for f, c in serie if f <= fecha]


def _ma(x, n):
    return sum(x[-n:]) / n if len(x) >= n else None


def lectura_btc(btc: list[list], fecha: str) -> dict | None:
    x = _hasta(btc, fecha)
    if len(x) < 210:
        return None
    ma200, ma50 = _ma(x, 200), _ma(x, 50)
    r20 = (x[-1] / x[-21] - 1) * 100
    if x[-1] > ma200 and x[-1] > ma50:
        estado = "alcista"
    elif x[-1] < ma200 and x[-1] < ma50:
        estado = "bajista"
    else:
        estado = "indefinido"
    return {"precio": x[-1], "ma200": ma200, "ma50": ma50, "r20": r20, "estado": estado,
            "riesgo": 0.5 if estado == "alcista" else -0.5 if estado == "bajista" else 0.0}


def brecha_cripto(cripto: dict[str, float], ccl: dict[str, float], fecha: str) -> float | None:
    """Dólar cripto contra CCL, en %, con los últimos datos hasta la fecha."""
    fc = [f for f in cripto if f <= fecha]
    fl = [f for f in ccl if f <= fecha]
    if not fc or not fl:
        return None
    c, l = cripto[max(fc)], ccl[max(fl)]
    return (c / l - 1) * 100 if l else None


def clase(btc: dict | None, brecha: float | None, mejor: str | None, ens: dict) -> dict:
    lineas, ensena = [], []
    if btc:
        lineas.append(f"Bitcoin en US$ {btc['precio']:,.0f}: tendencia {btc['estado']} ({btc['r20']:+.1f}% en un mes; promedio de 200 días "
                      f"US$ {btc['ma200']:,.0f}). ".replace(",", ".")
                      + ("El apetito por riesgo está prendido." if btc["estado"] == "alcista" else
                         "El apetito por riesgo está apagado." if btc["estado"] == "bajista" else "Sin dirección clara."))
    if brecha is not None:
        lineas.append(f"Dólar cripto {brecha:+.1f}% contra el CCL. "
                      + ("Cotiza por encima: hay demanda de dólares fuera del horario de bolsa, puede anticipar suba del CCL." if brecha >= 1 else
                         "Cotiza por debajo: sobran dólares cripto, puede anticipar calma o baja del CCL." if brecha <= -1 else
                         "Alineado con el CCL: no anticipa nada."))
    if mejor:
        lineas.append(f"Aprendo del resto: el agente con mejor historial hoy es {mejor}; si opina distinto en un papel, bajo mi convicción.")
    for clave, txt in (("btc", "lectura de Bitcoin sobre CEDEARs"), ("brecha", "dólar cripto como anticipo del CCL")):
        r = ens.get(clave) or {}
        if r.get("veredicto"):
            ensena.append(f"Prueba con la historia ({txt}): {r['veredicto']}")
    titulo = (f"Bitcoin {btc['estado']}" if btc else "Sin datos de Bitcoin") + (f" · dólar cripto {brecha:+.1f}% vs CCL" if brecha is not None else "")
    return {"titulo": titulo, "clase": lineas, "ensena": ensena}


def senales_en(btc: dict | None, brecha: float | None, ctx, tickers: list[str], ens: dict,
               otras: dict[str, list] | None = None, mejor_agente: str | None = None) -> list[Senal]:
    out = []
    usar_brecha = bool((ens.get("brecha") or {}).get("sirve"))
    for tk in dict.fromkeys(tickers):
        t = ctx.titulo(tk) if ctx else None
        grupo = (t or {}).get("grupo")
        d, f, txt = 0, 0.0, ""
        if btc and tk in CEDEARS_CRIPTO and btc["estado"] != "indefinido":
            d = 1 if btc["estado"] == "alcista" else -1
            f = 0.5
            txt = f"Bitcoin en tendencia {btc['estado']} ({btc['r20']:+.1f}% en un mes): {tk} sigue a BTC."
        elif usar_brecha and brecha is not None and grupo == "cedears" and abs(brecha) >= 1.5:
            d = 1 if brecha > 0 else -1
            f = 0.3
            txt = (f"El dólar cripto está {brecha:+.1f}% contra el CCL: anticipa {'suba' if d > 0 else 'baja'} del dólar de bolsa, "
                   f"que mueve a los CEDEARs en pesos.")
        if not d:
            continue
        if otras and mejor_agente:  # aprende del mejor: si opina distinto, baja convicción
            op = [s for s in otras.get(tk, []) if s.agente == mejor_agente and s.direccion]
            if op and op[0].direccion != d:
                f = round(f / 2, 2)
                txt += f" Pero {mejor_agente}, el de mejor historial, opina distinto: bajo mi convicción a la mitad."
            elif op:
                txt += f" Coincide con {mejor_agente}, el de mejor historial."
        out.append(Senal("cripto", tk, d, f, txt, {"btc": btc and btc["estado"], "brecha": brecha}))
    return out


def entrenar(btc_serie: list[list], precios_usd: dict[str, list[list]], cripto: dict[str, float], ccl: dict[str, float],
             paso: int = 3) -> dict:
    """¿Sirve? (1) BTC sobre CEDEARs cripto y sobre todos los CEDEARs, a 10 y 60 ruedas, en dólares.
    (2) ¿El dólar cripto despegado del CCL anticipa el CCL de los próximos 5 días?"""
    from ..nucleo.calibracion import _sumar, banda
    stats = {"total": {}, "bandas": {}, "por_horizonte": {"10": {}, "60": {}}}
    ens_btc = {"btc_alcista": {}, "btc_indefinido": {}, "btc_bajista": {}}
    fechas = [f for f, _ in btc_serie]
    pos = {tk: {f: i for i, (f, _) in enumerate(s)} for tk, s in precios_usd.items()}
    for f in fechas[210:-90:paso]:
        b = lectura_btc(btc_serie, f)
        if not b:
            continue
        for tk, s in precios_usd.items():
            i = pos[tk].get(f)
            if i is None or i + 60 >= len(s):
                continue
            r10 = (s[i + 10][1] / s[i][1] - 1) * 100
            _sumar(ens_btc[f"btc_{b['estado']}"], r10, 0.5)
            if tk in CEDEARS_CRIPTO and b["estado"] != "indefinido":
                d = 1 if b["estado"] == "alcista" else -1
                r60 = (s[i + 60][1] / s[i][1] - 1) * 100
                _sumar(stats["total"], r10 * d, 0.5)
                _sumar(stats["bandas"].setdefault(banda(0.5), {}), r10 * d, 0.5)
                _sumar(stats["por_horizonte"]["10"], r10 * d, 0.5)
                _sumar(stats["por_horizonte"]["60"], r60 * d, 0.5)
    # (2) dólar cripto -> CCL a 5 días
    ens_br = {"cripto_arriba": {}, "alineado": {}, "cripto_abajo": {}}
    fl = sorted(ccl)
    for k, f in enumerate(fl[:-5]):
        if f < min(cripto, default="9999"):
            continue
        br = brecha_cripto(cripto, ccl, f)
        if br is None:
            continue
        cambio = (ccl[fl[k + 5]] / ccl[f] - 1) * 100
        lado = "cripto_arriba" if br >= 1 else "cripto_abajo" if br <= -1 else "alineado"
        _sumar(ens_br[lado], cambio, 0.3)
    # veredictos
    def prom(d):
        return d["suma_ret"] / d["casos"] if d.get("casos") else None
    a, z = prom(ens_btc["btc_alcista"]), prom(ens_btc["btc_bajista"])
    v_btc = (None if a is None or z is None else
             f"comprar CEDEARs con BTC alcista rindió {a:+.1f}% a 10 ruedas contra {z:+.1f}% con BTC bajista "
             f"({ens_btc['btc_alcista']['casos']} y {ens_btc['btc_bajista']['casos']} casos).")
    up, dn = prom(ens_br["cripto_arriba"]), prom(ens_br["cripto_abajo"])
    sirve_br = up is not None and dn is not None and ens_br["cripto_arriba"]["casos"] >= 30 and ens_br["cripto_abajo"]["casos"] >= 30 and up - dn >= 0.5
    v_br = (None if up is None or dn is None else
            f"con el dólar cripto 1% o más arriba del CCL, el CCL se movió {up:+.2f}% en los 5 días siguientes; con el cripto abajo, {dn:+.2f}% "
            f"({ens_br['cripto_arriba']['casos']} y {ens_br['cripto_abajo']['casos']} días). " + ("Sí anticipa." if sirve_br else "No alcanza para anticipar."))
    return {"cripto": stats,
            "ensenanza": {"btc": {**ens_btc, "veredicto": v_btc,
                                  "sirve": a is not None and z is not None and a - z >= 0.5 and ens_btc["btc_bajista"].get("casos", 0) >= 200},
                          "brecha": {**ens_br, "veredicto": v_br, "sirve": sirve_br}}}


def multiplicador(btc: dict | None, ens: dict, grupo: str | None, direccion: int) -> float:
    """Si la historia mostró que BTC alcista mejora a los CEDEARs, a las compras de CEDEARs del resto se les cree
    un poco más con BTC alcista y un poco menos con BTC bajista (×0,9 a ×1,1)."""
    if not btc or grupo != "cedears" or not direccion or not (ens.get("btc") or {}).get("sirve"):
        return 1.0
    return round(1 + 0.2 * btc["riesgo"] * direccion, 3)
