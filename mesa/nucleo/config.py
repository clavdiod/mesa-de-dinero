from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=None)
def _leer(nombre: str) -> dict:
    with open(RAIZ / "config" / nombre, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def config() -> dict:
    return _leer("mesa.yaml")


def emisores() -> dict:
    return _leer("emisores.yaml")


def ons() -> dict:
    return _leer("ons.yaml")


def sector(ticker: str) -> str:
    base = ticker_base(ticker)
    return (emisores().get(base) or {}).get("sector", "otros")


def nombre_emisor(ticker: str) -> str | None:
    return (emisores().get(ticker_base(ticker)) or {}).get("nombre")


def ticker_base(ticker: str) -> str:
    """AL30D -> AL30, GGALD -> GGAL. Respeta tickers que terminan en D de verdad si están en emisores."""
    t = ticker.upper()
    if t in emisores():
        return t
    for suf in ("D", "C"):
        if t.endswith(suf) and t[:-1] in emisores():
            return t[:-1]
    return t


def env(nombre: str, defecto: str | None = None) -> str | None:
    v = os.environ.get(nombre)
    return v if v not in (None, "") else defecto
