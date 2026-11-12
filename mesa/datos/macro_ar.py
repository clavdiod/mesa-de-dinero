"""Datos macro argentinos gratis (12/11): BCRA (API pública v4), dólar futuro (Matba Rofex / A3) y bonos CER (data912 + BYMA)."""
from __future__ import annotations

from datetime import date, timedelta

from .gratis import _S, _UA_JSON

BCRA = "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias"
VAR = {"a3500": 5, "badlar": 7, "tamar": 44, "inflacion_mensual": 27, "plazo_fijo": 12, "cer": 30}


def _filas(x):
    """Busca recursivamente listas de {fecha, valor} (la API cambió de forma entre versiones)."""
    if isinstance(x, list):
        if x and isinstance(x[0], dict) and "fecha" in x[0] and "valor" in x[0]:
            return x
        for y in x:
            r = _filas(y)
            if r:
                return r
    elif isinstance(x, dict):
        for y in x.values():
            r = _filas(y)
            if r:
                return r
    return []


def bcra_ultimos() -> dict:
    """{nombre: {valor, fecha, descripcion}} de las variables que usa la mesa."""
    out, vs = {}, []
    for off in (0, 1000):
        try:
            vs += _S.get(f"{BCRA}?offset={off}&limit=1000", timeout=30, verify=False).json().get("results") or []
        except Exception as ex:
            print(f"[bcra] {ex}")
    por_id = {v.get("idVariable"): v for v in vs}
    for nombre, i in VAR.items():
        v = por_id.get(i) or {}
        out[nombre] = {"valor": v.get("ultValorInformado"), "fecha": v.get("ultFechaInformada"), "descripcion": v.get("descripcion")}
    return out


def bcra_serie(id_var: int, desde: date, hasta: date | None = None) -> dict[str, float]:
    hasta = hasta or date.today()
    try:
        j = _S.get(f"{BCRA}/{id_var}?desde={desde.isoformat()}&hasta={hasta.isoformat()}&limit=3000", timeout=40, verify=False).json()
        return {str(f["fecha"])[:10]: float(f["valor"]) for f in _filas(j) if f.get("valor") is not None}
    except Exception as ex:
        print(f"[bcra serie {id_var}] {ex}")
        return {}


def dolar_futuro(hoy: date) -> list[dict]:
    """Cierres de los contratos de dólar futuro (DLR) del último día con datos. Matba Rofex (A3), API pública."""
    for atras in range(0, 7):
        d = hoy - timedelta(days=atras)
        try:
            r = _S.get("https://apicem.matbarofex.com.ar/api/v2/closing-prices", headers=_UA_JSON, timeout=30,
                       params={"product": "DLR", "segment": "Monedas", "type": "FUT", "excludeEmptyVol": "false",
                               "from": (d - timedelta(days=1)).isoformat(), "to": d.isoformat()})
            filas = r.json().get("data") or []
        except Exception as ex:
            print(f"[futuro] {ex}")
            filas = []
        if filas:
            ult = max(f["dateTime"][:10] for f in filas)
            out = []
            for f in filas:
                s = str(f.get("symbol") or "")
                if f["dateTime"][:10] != ult or not s.startswith("DLR") or len(s) != 9 or not (f.get("settlement") or f.get("close")):
                    continue  # DLR112026: mes y año
                mes, anio = int(s[3:5]), int(s[5:9])
                fin = (date(anio + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1))
                out.append({"contrato": s, "vence": fin.isoformat(), "precio": float(f.get("settlement") or f["close"]),
                            "interes_abierto": f.get("openInterest"), "volumen": f.get("volume"), "fecha": ult})
            return sorted(out, key=lambda x: x["vence"])
    return []


def bonos_cer(panel_bonos: list[dict] | None = None, fichas: dict | None = None) -> list[dict]:
    """Bonos CER cero cupón (TZX..., X...) con precio de data912 y fechas de emisión de BYMA.
    fichas: caché {ticker: ficha o None} (las fechas no cambian: se consultan una sola vez)."""
    from . import gratis, byma
    filas = panel_bonos if panel_bonos is not None else gratis.data912("bonos")
    fichas = fichas if fichas is not None else {}
    out = []
    for f in filas:
        tk = str(f.get("simbolo") or "")
        if not (tk.startswith("TZX") or (tk.startswith("X") and len(tk) == 5)) or tk.endswith(("D", "C")) or not f.get("ultimo"):
            continue
        if tk not in fichas:
            d = byma.ficha(tk)
            fichas[tk] = {k: d.get(k) for k in ("formaAmortizacion", "fechaEmision", "fechaVencimiento")} if d else None
        fi = fichas[tk]
        fa = (fi or {}).get("formaAmortizacion") or ""
        if not fi or not fi.get("fechaEmision") or "CER" not in fa.upper() or "vencimiento" not in fa.lower() or "cuota" in fa.lower():
            continue
        out.append({"ticker": tk, "precio": float(f["ultimo"]), "emision": fi["fechaEmision"][:10], "vence": fi["fechaVencimiento"][:10]})
    return out
