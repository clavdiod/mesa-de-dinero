"""Contador de consultas a IOL. Regla fija: tener siempre presente el tope mensual (25.000).

Cada llamada queda anotada por mes, día y tipo. Antes de consultar se pregunta `puede_consultar`.
"""
from __future__ import annotations

from ..nucleo.config import config
from ..nucleo.reloj import ahora


class PresupuestoAgotado(RuntimeError):
    pass


class Consumo:
    def __init__(self, almacen):
        self.almacen = almacen
        self.mes = ahora().strftime("%Y-%m")
        self.clave = f"consumo/{self.mes}"
        self.datos = almacen.get(self.clave) or {"mes": self.mes, "total": 0, "por_dia": {}, "por_tipo": {}}
        self._pendiente = 0

    @property
    def tope(self) -> int:
        return int(config()["iol"]["presupuesto_mensual"])

    @property
    def total(self) -> int:
        return self.datos["total"]

    @property
    def pct(self) -> float:
        return self.total / self.tope * 100

    def factor_frecuencia(self) -> int:
        """1 = normal; 2 = la mitad de rondas cuando se pasa el % de alerta o el ritmo proyectado no alcanza."""
        c = config()["iol"]
        if self.pct >= c["alerta_pct"]:
            return 2
        dia = ahora().day
        if dia >= 5:  # proyección simple del mes con el ritmo actual (~22 ruedas por mes)
            proyectado = self.total / dia * 30
            if proyectado > self.tope:
                return 2
        return 1

    def solo_cierre(self) -> bool:
        return self.pct >= config()["iol"]["frenar_pct"]

    def puede_consultar(self, n: int = 1) -> bool:
        return self.total + n <= self.tope

    def anotar(self, tipo: str, n: int = 1) -> None:
        if not self.puede_consultar(n):
            raise PresupuestoAgotado(f"Se alcanzó el tope mensual de IOL ({self.tope}).")
        hoy = ahora().strftime("%Y-%m-%d")
        self.datos["total"] += n
        self.datos["por_dia"][hoy] = self.datos["por_dia"].get(hoy, 0) + n
        self.datos["por_tipo"][tipo] = self.datos["por_tipo"].get(tipo, 0) + n
        self._pendiente += n

    def guardar(self) -> None:
        if self._pendiente:
            self.almacen.put(self.clave, self.datos)
            self._pendiente = 0

    def resumen(self) -> dict:
        return {"mes": self.mes, "total": self.total, "tope": self.tope, "pct": round(self.pct, 1),
                "hoy": self.datos["por_dia"].get(ahora().strftime("%Y-%m-%d"), 0),
                "por_tipo": self.datos["por_tipo"]}
