"""BYMA Educa — Resumen Diario de Mercado (16/11). Página pública y gratis de la bolsa que trae los datos del día adentro.

De ahí se toma, una vez por día (en el cierre):
- El cronograma de pagos de todos los bonos y ONs (renta y amortización cada 100 nominales originales), con TIR,
  duration, paridad, valor técnico, ley, sector y liquidez. Reemplaza la carga a mano de config/bonos_flujos.yaml
  (que queda como respaldo) y ahorra consultas a MAE.
- El historial de dividendos de las acciones argentinas desde 2018.
No es un servicio de datos documentado: si la página cambia, se usa lo que ya había guardado y las otras fuentes.
"""
from __future__ import annotations

import json
import re

from .gratis import _S

URL = "https://tablero.bymaeduca.com.ar"


def descargar() -> dict | None:
    try:
        html = _S.get(URL, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}, timeout=90).text
    except Exception as ex:
        print(f"[bymaeduca] {ex}")
        return None
    for s in sorted(re.findall(r"<script[^>]*>(.*?)</script>", html, re.S), key=len, reverse=True)[:3]:
        try:
            d = json.loads(s.strip())
            if isinstance(d, dict) and ("tp" in d or "on" in d):
                return d
        except Exception:
            continue
    print("[bymaeduca] no se encontraron los datos en la página (¿cambió?)")
    return None


def _flujos(fila: dict) -> list[dict]:
    pagos: dict[str, dict] = {}
    for f, v in fila.get("ren") or []:
        pagos.setdefault(f, {"fecha": f, "interes": 0.0, "amortizacion": 0.0})["interes"] += float(v or 0)
    for f, v in fila.get("amo") or []:
        pagos.setdefault(f, {"fecha": f, "interes": 0.0, "amortizacion": 0.0})["amortizacion"] += float(v or 0)
    return [{**p, "interes": round(p["interes"], 6), "amortizacion": round(p["amortizacion"], 6)} for _, p in sorted(pagos.items())]


def extraer(d: dict) -> dict:
    """{'fecha', 'flujos': {ticker: {...}}, 'dividendos': [...], 'merval': {...}}"""
    flujos = {}
    for seg in ("tp", "on"):
        bloque = d.get(seg) or {}
        for r in bloque.get("rows") or []:
            tk = r.get("tk")
            if not tk:
                continue
            x = {"emisor": r.get("em"), "descripcion": r.get("de"), "tipo": r.get("ti"), "sector": r.get("sec"), "ley": r.get("ley"),
                 "moneda": r.get("me"), "vence": r.get("fv"), "frecuencia": r.get("fc"), "segmento": r.get("seg"),
                 "tir": r.get("ytm"), "duration": r.get("dm"), "paridad": r.get("par"), "valor_tecnico": r.get("vt"),
                 "volumen_diario": r.get("adtv"), "fuente": "BYMA", "flujos": _flujos(r), "grupo": "soberanos" if seg == "tp" else "ons"}
            flujos[tk] = x
            for e in (r.get("adtve") or []):  # sus especies en dólares (D) y cable (C)
                if e and e != tk:
                    flujos.setdefault(e, {"base": tk})  # solo la referencia: los pagos son los mismos
        for e in bloque.get("esp") or []:
            b = e.get("base")
            if e.get("tk") and b in flujos:
                flujos.setdefault(e["tk"], {"base": b})
    div = [{"fecha": x.get("f"), "ticker": x.get("tk"), "emisor": x.get("em"), "tipo": x.get("ti"), "moneda": x.get("mo"),
            "por_accion_ars": x.get("dpa"), "por_accion_usd": x.get("dpu"), "total_usd": x.get("usd"), "sector": x.get("sec")}
           for x in ((d.get("div") or {}).get("filas") or [])]
    mer = d.get("mer") or {}
    return {"fecha": (d.get("tp") or d.get("on") or {}).get("fecha"), "flujos": flujos, "dividendos": div,
            "merval": {"f": mer.get("f"), "usd": mer.get("usd"), "ars": mer.get("ars")} if mer.get("f") else None}


def actualizar(almacen) -> dict:
    """Descarga y guarda (bymaeduca/flujos, bymaeduca/dividendos, bymaeduca/merval). Devuelve un resumen."""
    d = descargar()
    if not d:
        return {"ok": False}
    x = extraer(d)
    if x["flujos"]:
        almacen.put("bymaeduca/flujos", {"fecha": x["fecha"], "titulos": x["flujos"]})
    if x["dividendos"]:
        almacen.put("bymaeduca/dividendos", {"fecha": x["fecha"], "filas": x["dividendos"]})
    if x["merval"]:
        almacen.put("bymaeduca/merval", {"fecha": x["fecha"], **x["merval"]})
    return {"ok": True, "fecha": x["fecha"], "titulos": len(x["flujos"]), "dividendos": len(x["dividendos"])}


def flujos_guardados(almacen) -> dict:
    """{ticker: {emisor, moneda, flujos, ...}} con las especies D y C resueltas a su título base."""
    t = ((almacen.get("bymaeduca/flujos") if almacen is not None else None) or {}).get("titulos") or {}
    return {k: ({**t[v["base"]], "base": v["base"]} if "flujos" not in v and v.get("base") in t else v) for k, v in t.items()}
