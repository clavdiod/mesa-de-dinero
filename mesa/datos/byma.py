"""Ficha técnica gratis de BYMA (open.bymadata): fecha de emisión, vencimiento y tasa de las LECAP y BONCAP.

Con eso se calcula lo que pagan al final, cada 100 nominales: VF = 100 × (1 + TEM) ^ (meses entre emisión y vencimiento),
contando los meses como 30/360 (verificado con IOL: S13N6 109,65; S29E7 111,68; T30A7 157,34).
"""
from __future__ import annotations

import re
from datetime import date

_B = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free/"
_H = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json", "Accept": "application/json",
      "Origin": "https://open.bymadata.com.ar", "Referer": "https://open.bymadata.com.ar/"}
LETRA = re.compile(r"^[ST]\d{2}[A-Z]\d$")


def ficha(tk: str) -> dict | None:
    from .gratis import _S
    try:
        r = _S.post(_B + "bnown/fichatecnica/especies/general", json={"symbol": tk, "Content-Type": "application/json"},
                    headers=_H, timeout=30, verify=False)
        d = (r.json().get("data") or [None])[0]
    except Exception as ex:
        print(f"[byma] {tk}: {ex}")
        return None
    return d


def meses_30_360(desde: date, hasta: date) -> float:
    d1, d2 = min(desde.day, 30), (min(hasta.day, 30) if desde.day >= 30 or hasta.day < 31 else hasta.day)
    return ((hasta.year - desde.year) * 360 + (hasta.month - desde.month) * 30 + (d2 - d1)) / 30


def tem_de(texto: str) -> float | None:
    m = re.search(r"(?:mensual|TEM)[^0-9]{0,40}(\d+[.,]\d+)\s*%", texto or "", re.I)
    return float(m.group(1).replace(",", ".")) if m else None


def letra(tk: str) -> dict | None:
    """{vence, valor_final, tipo, tem, emision} o None si BYMA no trae la tasa."""
    d = ficha(tk)
    if not d or not d.get("fechaEmision") or not d.get("fechaVencimiento"):
        return None
    em, vt = date.fromisoformat(d["fechaEmision"][:10]), date.fromisoformat(d["fechaVencimiento"][:10])
    tem = tem_de(d.get("interes") or "")
    tipo = "BONCAP" if "BONO" in (d.get("denominacion") or "").upper() else "LECAP"
    out = {"vence": vt.isoformat(), "emision": em.isoformat(), "tipo": tipo, "tem_emision": tem, "fuente": "BYMA"}
    if tem:
        out["valor_final"] = round(100 * (1 + tem / 100) ** meses_30_360(em, vt), 6)
    return out
