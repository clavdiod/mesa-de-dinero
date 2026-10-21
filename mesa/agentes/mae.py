"""22. MAE contra BYMA: el mismo bono o la misma ON cotiza en dos mercados y a veces a precios distintos.

- Compara en cada ronda el precio de MAE (A3 Mercados) con el de BYMA (nuestro panel), mismo papel,
  misma moneda y, si existe, el mismo plazo (24 h). Avisa cuando la diferencia es grande y los dos lados
  tienen volumen: puede ser una oportunidad (comprar donde está más barato) o un precio viejo.
- Guarda un histórico propio de cierres de MAE (gratis) para bonos y ONs: así no se gastan consultas de IOL
  para armar su historial.
- Lee los avisos de pago de renta y amortización y los avisos de licitaciones (anuncios y resultados).
"""
from __future__ import annotations

import re
import statistics as st
import unicodedata
from datetime import date

from ..datos.gratis import escala_mae, ticker_mae_a_byma

GRUPOS_RF = ("soberanos", "ons", "letras", "bonos")
# segmentos de compraventa (bilateral y garantizado). Se descartan pases (RT) y cauciones (K): no son precio de mercado.
SEGMENTOS = {"BT", "GT", "GP"}
UMBRAL = {"soberanos": 1.0, "letras": 0.7, "ons": 1.5, "bonos": 1.0}


def _monto_minimo(moneda: str | None) -> float:
    return 10_000 if (moneda or "$").strip().upper() in ("D", "C") else 10_000_000


def elegir_filas(rows: list[dict]) -> dict[tuple[str, str], dict]:
    """Una fila por papel y moneda: plazo 24 h si hay, y dentro de eso la de más monto."""
    mejor: dict[tuple[str, str], dict] = {}
    for m in rows:
        if not m.get("ultimo") and not m.get("precioCierre"):
            continue
        if (m.get("codigoSegmento") or m.get("codsegmento") or "BT").strip() not in SEGMENTOS:
            continue
        k = ((m.get("ticker") or m.get("codTitulo") or "").strip().upper(), (m.get("moneda") or "$").strip())
        p = mejor.get(k)
        rango = lambda x: (x.get("plazo") == "001", x.get("monto") or x.get("volumen") or 0)
        if not p or rango(m) > rango(p):
            mejor[k] = m
    return mejor


def comparar(titulos: dict[str, dict], rows: list[dict]) -> list[dict]:
    """titulos: nuestro panel {ticker: {ultimo, grupo, monto, volumen}}. Devuelve los pares comparables."""
    out = []
    for (cod, mon), m in elegir_filas(rows).items():
        tk = ticker_mae_a_byma(cod, mon, titulos)
        t = titulos.get(tk)
        if not t or not t.get("ultimo") or t.get("grupo") not in GRUPOS_RF:
            continue
        precio = (m.get("ultimo") or m.get("precioCierre")) * escala_mae(mon)
        dif = (precio / t["ultimo"] - 1) * 100
        if abs(dif) > 15:  # distinta escala o error de dato: no se compara
            continue
        liquido = (m.get("monto") or 0) >= _monto_minimo(mon) and bool(t.get("volumen") or t.get("monto"))
        out.append({"ticker": tk, "grupo": t["grupo"], "mae": round(precio, 4), "byma": t["ultimo"], "dif": round(dif, 2),
                    "plazo_mae": "24 h" if m.get("plazo") == "001" else "contado", "monto_mae": m.get("monto") or 0,
                    "liquido": liquido})
    return sorted(out, key=lambda p: -abs(p["dif"]))


def resumen(pares: list[dict]) -> dict:
    out = {}
    for g in GRUPOS_RF:
        xs = [abs(p["dif"]) for p in pares if p["grupo"] == g and p["liquido"]]
        if xs:
            xs.sort()
            out[g] = {"n": len(xs), "mediana": round(st.median(xs), 2), "p90": round(xs[int(len(xs) * 0.9)], 2),
                      "mayor_1pct": sum(1 for x in xs if x >= 1)}
    return out


def alertas(pares: list[dict]) -> list[dict]:
    """Para el radar: diferencias grandes con volumen en los dos mercados."""
    out = []
    for p in pares:
        if not p["liquido"] or abs(p["dif"]) < UMBRAL.get(p["grupo"], 1.0):
            continue
        barato = "MAE" if p["dif"] < 0 else "BYMA"
        out.append({"tipo": "mae", "tipos": ["mae"], "ticker": p["ticker"], "grupo": p["grupo"], "valor": p["dif"],
                    "severidad": "alta" if abs(p["dif"]) >= 2 * UMBRAL.get(p["grupo"], 1.0) else "media",
                    "texto": f"{p['ticker']}: en MAE cotiza {p['dif']:+.1f}% contra BYMA ({p['mae']:,.2f} contra {p['byma']:,.2f}); "
                             f"más barato en {barato}. Puede ser una oportunidad o un precio viejo: confirmar puntas."
                             .replace(",", "X").replace(".", ",").replace("X", ".")})
    return out


# ---------- histórico propio de cierres de MAE ----------
def cierres_a_series(rows: list[dict], existentes=None) -> dict[str, dict[str, list]]:
    """{ticker BYMA: {fecha: [cierre, volumen]}} con una fila por papel, moneda y día (24 h si hay)."""
    por_dia: dict[tuple[str, str, str], dict] = {}
    for r in rows:
        if not r.get("precioCierre") or (r.get("codsegmento") or "BT").strip() not in SEGMENTOS:
            continue
        k = (r["codTitulo"].strip().upper(), (r.get("moneda") or "$").strip(), r["fecha"][:10])
        p = por_dia.get(k)
        rango = lambda x: (x.get("plazo") == "001", (x.get("tipoCierreDesc") or "").startswith("Repres"), x.get("volumen") or 0)
        if not p or rango(r) > rango(p):
            por_dia[k] = r
    out: dict[str, dict[str, list]] = {}
    for (cod, mon, fe), r in por_dia.items():
        tk = ticker_mae_a_byma(cod, mon, existentes)
        e = escala_mae(mon)
        out.setdefault(tk, {})[fe] = [round(r["precioCierre"] * e, 4), round(r.get("volumen") or 0),
                                      round((r.get("precioMaximo") or r["precioCierre"]) * e, 4),
                                      round((r.get("precioMinimo") or r["precioCierre"]) * e, 4)]
    return out


def series_a_velas(serie: dict[str, list]) -> list[dict]:
    return [{"fecha": f, "apertura": v[0], "maximo": v[2] if len(v) > 2 else v[0], "minimo": v[3] if len(v) > 3 else v[0],
             "cierre": v[0], "volumen": v[1]} for f, v in sorted(serie.items())]


# ---------- avisos de pago y de licitaciones ----------
def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\b(s\.?a\.?u?|s\.?r\.?l\.?|sociedad anonima|argentina|de|la|del)\b|[^a-z0-9 ]", " ", s)


def coincide_emisor(empresa: str, nombres: list[str]) -> bool:
    e = _norm(empresa).split()
    for n in nombres:
        palabras = [w for w in _norm(n).split() if len(w) > 2]
        if palabras and all(w in e for w in palabras[:2]):
            return True
    return False


_FECHA = re.compile(r"(\d{2})-(\d{2})-(\d{2,4})(?!.*\d{2}-\d{2}-\d{2})")


def _fecha_titulo(t: str) -> str | None:
    m = _FECHA.search(t)
    if not m:
        return None
    d, mth, y = m.groups()
    y = ("20" + y) if len(y) == 2 else y
    try:
        return date(int(y), int(mth), int(d)).isoformat()
    except ValueError:
        return None


def pagos(docs: list[dict], hoy: date, nombres_mios: list[str]) -> list[dict]:
    """Avisos de pago de renta/amortización con fecha de pago futura -> eventos de calendario."""
    out, vistos = [], set()
    for d in docs:
        t = re.sub(r"\.pdf$", "", d.get("titulo") or "", flags=re.I)
        m = re.search(r"pago\s+(\d{2}-\d{2}-\d{2,4})", t, re.I)
        f = _fecha_titulo(m.group(1)) if m else None
        if not f or f < hoy.isoformat():
            continue
        clave = (t.lower().replace("rectificativo ", ""), f)
        if clave in vistos:
            continue
        vistos.add(clave)
        nombre = re.sub(r"-?\s*(rectificativo\s+)?pago\s+\d{2}-\d{2}-\d{2,4}", "", t, flags=re.I).replace("-", " ").strip()
        out.append({"fecha": f, "tipo": "cobro", "fuente": "mae", "ticker": None, "link": d.get("url"),
                    "empresa": d.get("empresa"), "mio": coincide_emisor(d.get("empresa") or "", nombres_mios),
                    "nombre": f"Pago de renta/amortización: {nombre} ({(d.get('empresa') or '').title()})"})
    return sorted(out, key=lambda e: e["fecha"])


def avisos_licitacion(docs: list[dict], hoy: date, dias: int = 7) -> dict:
    """Del boletín del mercado primario: anuncios (suscripción, colocación) y resultados de los últimos días."""
    desde = date.fromordinal(hoy.toordinal() - dias).isoformat()
    anuncios, resultados = [], []
    for d in docs:
        if (d.get("fecha") or "")[:10] < desde:
            continue
        t = re.sub(r"\.pdf$", "", d.get("titulo") or "", flags=re.I)
        tl = t.lower()
        limpio = re.sub(r"^MP\s*A3\s*-\s*(RES|ANU|ADE)\s*-\s*", "", t, flags=re.I).strip()
        item = {"fecha": d["fecha"][:10], "titulo": limpio, "empresa": d.get("empresa"), "link": d.get("url")}
        if "resultado" in tl:
            resultados.append(item)
        elif any(w in tl for w in ("aviso de suscrip", "aviso de coloca", "anuncio de licitac", "aviso complementario")):
            anuncios.append(item)
    dedup = lambda xs: list({x["titulo"].lower(): x for x in reversed(xs)}.values())[::-1]
    return {"anuncios": dedup(anuncios)[:10], "resultados": dedup(resultados)[:10]}


def guardar_historico(almacen, rows: list[dict], existentes=None) -> int:
    """Suma los cierres al histórico propio (una clave por año: mae/hist/AAAA). Devuelve cuántos datos nuevos."""
    nuevos = 0
    series = cierres_a_series(rows, existentes)
    por_anio: dict[str, dict] = {}
    for tk, s in series.items():
        for f, v in s.items():
            por_anio.setdefault(f[:4], {}).setdefault(tk, {})[f] = v
    for anio, ss in por_anio.items():
        h = almacen.get(f"mae/hist/{anio}") or {}
        for tk, s in ss.items():
            antes = h.setdefault(tk, {})
            nuevos += sum(1 for f in s if f not in antes)
            antes.update(s)
        almacen.put(f"mae/hist/{anio}", h)
        # índice chico: qué papeles tienen historia suficiente (para no leer el histórico entero en cada ronda)
        idx = set(almacen.get("mae/indice") or [])
        nuevo_idx = idx | {tk for tk, s in h.items() if len(s) >= 20}
        if nuevo_idx != idx:
            almacen.put("mae/indice", sorted(nuevo_idx))
    return nuevos


def historico(almacen, ticker: str, anios: list[str]) -> list[dict]:
    serie: dict[str, list] = {}
    for a in anios:
        serie.update(((almacen.get(f"mae/hist/{a}") or {}).get(ticker.upper())) or {})
    return series_a_velas(serie)
