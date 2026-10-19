from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class Contexto:
    """Todo lo que la ronda sabe del mercado en este momento. Los agentes solo leen de acá."""
    fecha: date
    hora: str
    paneles: dict[str, list[dict]]                 # grupo -> títulos normalizados
    dolares: dict = field(default_factory=dict)
    riesgo_pais: dict = field(default_factory=dict)
    riesgo_pais_ayer: float | None = None
    reservas: dict = field(default_factory=dict)
    noticias: list[dict] = field(default_factory=list)
    cache: Any = None                               # CacheHistorico
    lista: list[dict] = field(default_factory=list)       # Mi lista
    cartera: list[dict] = field(default_factory=list)
    params: dict = field(default_factory=dict)            # parámetros entrenados por agente
    clima: float = 0.0                                   # -1 malo .. +1 bueno (lo fija Macro)
    eventos: list[dict] = field(default_factory=list)    # calendario
    hechos: dict = field(default_factory=dict)           # ticker -> hechos relevantes recientes
    calificaciones: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)

    def __post_init__(self):
        self.por_simbolo: dict[str, dict] = {}
        for grupo, titulos in self.paneles.items():
            for t in titulos:
                if t.get("simbolo"):
                    self.por_simbolo[t["simbolo"].upper()] = {**t, "grupo": grupo}

    def titulo(self, simbolo: str) -> dict | None:
        return self.por_simbolo.get(simbolo.upper())

    def grupo(self, nombre: str) -> list[dict]:
        return self.paneles.get(nombre, [])

    def tickers_lista(self) -> list[str]:
        return [x["ticker"].upper() for x in self.lista if x.get("ticker")]
