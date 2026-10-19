from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Senal:
    """Lo que dice un agente sobre un ticker. direccion: +1 compra, -1 venta/evitar, 0 neutral."""
    agente: str
    ticker: str
    direccion: int
    fuerza: float            # 0 a 1
    texto: str
    datos: dict[str, Any] = field(default_factory=dict)
    veto: bool = False       # Riesgo / Hechos del emisor pueden vetar
    evaluable: bool = True   # si cuenta para el ranking de aciertos

    def dict(self) -> dict:
        return asdict(self)


@dataclass
class Plan:
    ticker: str
    lado: str                # "compra" (la mesa solo propone compras; "evitar" se informa como señal)
    entrada: float
    stop: float
    objetivo: float
    tamano_r: float = 1.0
    vence: str | None = None

    @property
    def riesgo_pct(self) -> float:
        return (self.entrada - self.stop) / self.entrada * 100

    @property
    def recompensa_pct(self) -> float:
        return (self.objetivo - self.entrada) / self.entrada * 100

    @property
    def r_bruto(self) -> float:
        riesgo = self.entrada - self.stop
        return (self.objetivo - self.entrada) / riesgo if riesgo > 0 else 0.0

    def r_neto(self, comision_pct: float) -> float:
        """Relación ganancia/pérdida descontando la comisión ida y vuelta de ambos lados."""
        gan = self.recompensa_pct - comision_pct
        per = self.riesgo_pct + comision_pct
        return gan / per if per > 0 else 0.0

    def dict(self) -> dict:
        d = asdict(self)
        d.update(riesgo_pct=round(self.riesgo_pct, 2), recompensa_pct=round(self.recompensa_pct, 2),
                 r_bruto=round(self.r_bruto, 2))
        return d
