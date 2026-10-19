"""Cliente de la API v2 de IOL (InvertirOnline).

- Cada llamada a datos pasa por el contador (`Consumo`). Pedir el token no se cuenta acá, pero se
  reutiliza mientras no venza y se renueva con el refresh_token, así son pocas por día.
- Normaliza las respuestas a un formato propio (`normalizar_titulo`), tolerante a variaciones de nombres.
- `scripts/probar_iol.py` descubre los nombres exactos de paneles y guarda las respuestas crudas.
"""
from __future__ import annotations

import time
from datetime import date
from typing import Any

import requests

from ..nucleo.config import env
from .consumo import Consumo

BASE = "https://api.invertironline.com"


class IOL:
    def __init__(self, consumo: Consumo, usuario: str | None = None, clave: str | None = None, almacen=None):
        self.consumo = consumo
        self.usuario = usuario or env("IOL_USUARIO")
        self.clave = clave or env("IOL_CLAVE")
        self.almacen = almacen
        self.s = requests.Session()
        self._token: str | None = None
        self._refresh: str | None = None
        self._vence = 0.0
        self._cargar_token()

    # ---------- autenticación ----------
    def _cargar_token(self) -> None:
        if self.almacen is None:
            return
        t = self.almacen.get("iol/token") or {}
        if t.get("vence", 0) > time.time() + 60:
            self._token, self._refresh, self._vence = t["access"], t.get("refresh"), t["vence"]
        elif t.get("refresh") and t.get("refresh_vence", 0) > time.time() + 60:
            self._refresh = t["refresh"]

    def _guardar_token(self, data: dict) -> None:
        self._token = data["access_token"]
        self._refresh = data.get("refresh_token")
        self._vence = time.time() + int(data.get("expires_in", 900)) - 120
        if self.almacen is not None:
            self.almacen.put("iol/token", {"access": self._token, "refresh": self._refresh, "vence": self._vence,
                                           "refresh_vence": time.time() + 3600 * 12})

    def _autenticar(self) -> None:
        if self._refresh:
            r = self.s.post(f"{BASE}/token", data={"refresh_token": self._refresh, "grant_type": "refresh_token"},
                            timeout=30)
            if r.ok:
                self._guardar_token(r.json())
                return
        if not (self.usuario and self.clave):
            raise RuntimeError("Faltan IOL_USUARIO / IOL_CLAVE en los secretos.")
        r = self.s.post(f"{BASE}/token", data={"username": self.usuario, "password": self.clave,
                                                "grant_type": "password"}, timeout=30)
        r.raise_for_status()
        self._guardar_token(r.json())

    def _get(self, ruta: str, tipo: str, params: dict | None = None) -> Any:
        self.consumo.anotar(tipo)
        if not self._token or time.time() >= self._vence:
            self._autenticar()
        for intento in range(2):
            r = self.s.get(f"{BASE}{ruta}", params=params, timeout=30,
                           headers={"Authorization": f"Bearer {self._token}"})
            if r.status_code == 401 and intento == 0:
                self._token = None
                self._autenticar()
                continue
            r.raise_for_status()
            return r.json()

    # ---------- datos ----------
    def panel(self, instrumento: str, panel: str, pais: str = "argentina") -> list[dict]:
        data = self._get(f"/api/v2/Cotizaciones/{instrumento}/{panel}/{pais}", "panel")
        titulos = data.get("titulos", data) if isinstance(data, dict) else data
        if titulos and isinstance(titulos[0], dict) and "tasaPromedio" in titulos[0]:
            return normalizar_cauciones(titulos)
        return [normalizar_titulo(t) for t in (titulos or [])]

    def cotizacion(self, simbolo: str, mercado: str = "bCBA", plazo: str = "t1") -> dict:
        data = self._get(f"/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion", "cotizacion",
                         params={"model.simbolo": simbolo, "model.mercado": mercado, "model.plazo": plazo})
        t = normalizar_titulo(data)
        t["simbolo"] = t.get("simbolo") or simbolo
        return t

    def historial(self, simbolo: str, desde: date, hasta: date, mercado: str = "bCBA", ajustada: bool = True) -> list[dict]:
        aj = "ajustada" if ajustada else "sinAjustar"
        data = self._get(f"/api/v2/{mercado}/Titulos/{simbolo}/Cotizacion/seriehistorica/"
                         f"{desde.isoformat()}/{hasta.isoformat()}/{aj}", "historial")
        return [normalizar_vela(v) for v in (data or [])]

    def paneles_disponibles(self, instrumento: str, pais: str = "argentina") -> Any:
        return self._get(f"/api/v2/{pais}/Titulos/Cotizacion/Paneles/{instrumento}", "descubrimiento")

    def instrumentos(self, pais: str = "argentina") -> Any:
        return self._get(f"/api/v2/{pais}/Titulos/Cotizacion/Instrumentos", "descubrimiento")


# ---------- normalización ----------
def _num(x) -> float | None:
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        try:
            return float(str(x).replace(".", "").replace(",", "."))
        except ValueError:
            return None


def _primero(d: dict, *claves):
    for c in claves:
        if c in d and d[c] not in (None, ""):
            return d[c]
    return None


def normalizar_titulo(t: dict) -> dict:
    puntas = t.get("puntas")
    compras, ventas = [], []
    if isinstance(puntas, dict):
        puntas = [puntas]
    for p in puntas or []:
        if not isinstance(p, dict):
            continue
        if _num(p.get("precioCompra")):
            compras.append({"precio": _num(p["precioCompra"]), "cantidad": _num(p.get("cantidadCompra")) or 0})
        if _num(p.get("precioVenta")):
            ventas.append({"precio": _num(p["precioVenta"]), "cantidad": _num(p.get("cantidadVenta")) or 0})
    ultimo = _num(_primero(t, "ultimoPrecio", "ultimo", "precio"))
    cierre_ant = _num(_primero(t, "cierreAnterior", "ultimoCierre"))
    var = _num(_primero(t, "variacionPorcentual", "variacion"))
    if var is None and ultimo and cierre_ant:
        var = (ultimo / cierre_ant - 1) * 100
    return {
        "simbolo": _primero(t, "simbolo", "Simbolo"),
        "descripcion": _primero(t, "descripcion", "descripcionTitulo"),
        "ultimo": ultimo,
        "variacion": var,
        "apertura": _num(t.get("apertura")),
        "maximo": _num(t.get("maximo")),
        "minimo": _num(t.get("minimo")),
        "cierre_anterior": cierre_ant,
        "volumen": _num(_primero(t, "volumenNominal", "volumen")),
        "monto": _num(_primero(t, "montoOperado", "monto")) or (
            (_num(_primero(t, "volumenNominal", "volumen")) or 0) * (ultimo or 0) or None),  # el panel no trae monto: se estima
        "operaciones": _num(t.get("cantidadOperaciones")),
        "fecha": _primero(t, "fechaHora", "fecha"),
        "moneda": t.get("moneda"),
        "lamina_minima": _num(t.get("laminaMinima")),
        "compra": compras[0]["precio"] if compras else None,
        "venta": ventas[0]["precio"] if ventas else None,
        "puntas_compra": compras,
        "puntas_venta": ventas,
    }


def normalizar_vela(v: dict) -> dict:
    fecha = str(_primero(v, "fechaHora", "fecha") or "")[:10]
    return {"fecha": fecha, "apertura": _num(v.get("apertura")), "maximo": _num(v.get("maximo")),
            "minimo": _num(v.get("minimo")), "cierre": _num(_primero(v, "ultimoPrecio", "cierre")),
            "volumen": _num(_primero(v, "volumenNominal", "volumen")) or 0}


def normalizar_cauciones(filas: list[dict]) -> list[dict]:
    """Cauciones vienen como {plazo, tasaPromedio, montoContado, fechaVencimiento}. Se agrupa por plazo
    quedándose con la de mayor monto del vencimiento más reciente."""
    por_plazo: dict = {}
    for f in filas:
        pl, tasa, monto, venc = f.get("plazo"), _num(f.get("tasaPromedio")), _num(f.get("montoContado")) or 0, str(f.get("fechaVencimiento", ""))[:10]
        if pl is None or not tasa:
            continue
        actual = por_plazo.get(pl)
        if actual is None or (venc, monto) > (actual["fecha"], actual["monto"]):
            por_plazo[pl] = {"simbolo": f"CAUCION{int(pl)}D", "descripcion": f"Caución {int(pl)} días", "ultimo": tasa,
                             "variacion": None, "monto": monto, "fecha": venc, "volumen": None,
                             "compra": None, "venta": None, "puntas_compra": [], "puntas_venta": []}
    return [por_plazo[k] for k in sorted(por_plazo)]
