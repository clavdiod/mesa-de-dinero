"""Caché de históricos. Regla: 1) mirar lo guardado, 2) pedir solo lo que falta, 3) guardar.

- Una rueda cerrada nunca se vuelve a pedir.
- Las velas diarias se arman gratis al cierre con el panel de la última ronda (sin consultas extra).
- La carga inicial por ticker se hace UNA vez con el historial de IOL.
"""
from __future__ import annotations

from datetime import date, timedelta

from ..nucleo.config import config
from ..nucleo.reloj import ahora


class CacheHistorico:
    def __init__(self, almacen, iol=None):
        self.almacen = almacen
        self.iol = iol
        self._mem: dict[str, list[dict]] = {}
        self._sucio: set[str] = set()
        self._lotes: dict[str, dict] = {}
        self.indice = almacen.get("cache/indice") or {}

    # Los historiales se guardan agrupados por la primera letra del ticker ("lotes"): el cierre escribe
    # como mucho ~26 claves por día en vez de una por papel (Cloudflare KV gratis: ~1.000 escrituras/día).
    @staticmethod
    def lote_de(ticker: str) -> str:
        return f"cache/lote/{ticker.upper()[:1] or '_'}"

    def _clave(self, ticker: str) -> str:  # formato viejo (un papel por clave): solo para migrar
        return f"cache/diario/{ticker.upper()}"

    def _lote(self, ticker: str) -> dict:
        k = self.lote_de(ticker)
        if k not in self._lotes:
            self._lotes[k] = self.almacen.get(k) or {}
        return self._lotes[k]

    def velas(self, ticker: str) -> list[dict]:
        t = ticker.upper()
        if t not in self._mem:
            lote = self._lote(t)
            if t in lote:
                self._mem[t] = lote[t]
            elif t in self.indice:  # todavía en el formato viejo: se lee una vez y pasa al lote
                v = self.almacen.get(self._clave(t)) or []
                self._mem[t] = v
                if v:
                    lote[t] = v
                    self._sucio.add(t)
            else:
                self._mem[t] = []
        return self._mem[t]

    def cierres(self, ticker: str) -> list[float]:
        return [v["cierre"] for v in self.velas(ticker) if v.get("cierre")]

    def asegurar_cedear(self, ticker: str, precio_hoy_ars: float) -> list[dict]:
        """CEDEARs: IOL no da su historial diario, así que se arma gratis con el precio en EE.UU. × CCL."""
        velas = self.velas(ticker)
        if velas or not precio_hoy_ars:
            return velas
        from .gratis import historial_cedear
        self.agregar(ticker, historial_cedear(ticker, precio_hoy_ars)[:-1], fuente="eeuu_x_ccl")  # hoy lo pone el panel
        return self.velas(ticker)

    def asegurar_mae(self, ticker: str, minimo: int = 20) -> bool:
        """Carga el historial desde nuestro histórico de cierres de MAE (gratis). Precio de MAE, no de BYMA:
        las diferencias suelen ser chicas (mediana < 1%) y alcanzan para tendencias y soportes."""
        if not hasattr(self, "_mae_idx"):
            self._mae_idx = set(self.almacen.get("mae/indice") or [])
        if ticker.upper() not in self._mae_idx:
            return False
        if not hasattr(self, "_mae_hist"):
            hoy = ahora().date()
            self._mae_hist = {}
            for a in (str(hoy.year - 1), str(hoy.year)):
                for tk, s in (self.almacen.get(f"mae/hist/{a}") or {}).items():
                    self._mae_hist.setdefault(tk, {}).update(s)
        s = self._mae_hist.get(ticker.upper()) or {}
        if len(s) < minimo:
            return False
        from ..agentes.mae import series_a_velas
        return self.agregar(ticker, series_a_velas(s)[:-1] if max(s) == ahora().date().isoformat() else series_a_velas(s), fuente="mae") > 0

    def asegurar(self, ticker: str, max_consultas_restantes: int = 1, titulo: dict | None = None) -> list[dict]:
        """Si el ticker no tiene historial, lo carga una sola vez (acciones/bonos: IOL, 1 consulta; CEDEARs: gratis)."""
        velas = self.velas(ticker)
        if not velas and titulo and titulo.get("grupo") == "cedears":
            return self.asegurar_cedear(ticker, titulo.get("ultimo"))
        if not velas and titulo and titulo.get("grupo") in ("soberanos", "ons", "letras", "bonos"):
            if self.asegurar_mae(ticker):  # bonos y ONs: primero nuestro histórico de MAE (gratis)
                return self.velas(ticker)
        if velas or self.iol is None or max_consultas_restantes <= 0:
            return velas
        if not self.iol.consumo.puede_consultar(1):
            return velas
        hasta = ahora().date() - timedelta(days=1)
        desde = hasta - timedelta(days=int(config()["iol"]["historial_dias_inicial"]))
        try:
            nuevas = self.iol.historial(ticker, desde, hasta)
        except Exception:
            return velas
        self.agregar(ticker, nuevas, fuente="iol")
        return self.velas(ticker)

    def agregar(self, ticker: str, nuevas: list[dict], fuente: str = "panel") -> int:
        """Agrega velas sin duplicar fechas. Devuelve cuántas agregó."""
        t = ticker.upper()
        velas = self.velas(t)
        existentes = {v["fecha"] for v in velas}
        agregadas = 0
        for v in nuevas:
            if not v.get("fecha") or v["fecha"] in existentes or not v.get("cierre"):
                continue
            velas.append({**v, "fuente": fuente})
            existentes.add(v["fecha"])
            agregadas += 1
        if agregadas:
            velas.sort(key=lambda v: v["fecha"])
            self._mem[t] = velas
            self._sucio.add(t)
            self.indice[t] = {"desde": velas[0]["fecha"], "hasta": velas[-1]["fecha"], "ruedas": len(velas)}
        return agregadas

    def vela_del_dia(self, titulo: dict, fecha: date | None = None) -> dict | None:
        """Arma la vela de hoy con el último panel (gratis)."""
        if not titulo.get("ultimo"):
            return None
        f = (fecha or ahora().date()).isoformat()
        return {"fecha": f, "apertura": titulo.get("apertura") or titulo["ultimo"],
                "maximo": titulo.get("maximo") or titulo["ultimo"], "minimo": titulo.get("minimo") or titulo["ultimo"],
                "cierre": titulo["ultimo"], "volumen": titulo.get("volumen") or 0}

    def guardar(self) -> None:
        lotes = set()
        for t in self._sucio:
            self._lote(t)[t] = self._mem[t]
            lotes.add(self.lote_de(t))
        for k in sorted(lotes):
            self.almacen.put(k, self._lotes[k])
        if self._sucio:
            self.almacen.put("cache/indice", self.indice)
        self._sucio.clear()
