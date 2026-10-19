"""Acceso a Claude para los agentes con IA. Si no hay clave, devuelve None y el agente usa su regla de respaldo."""
from __future__ import annotations

import json
import re

from .config import config, env


class IA:
    def __init__(self):
        self.clave = env("ANTHROPIC_API_KEY")
        self._cliente = None
        self.llamadas = 0

    @property
    def disponible(self) -> bool:
        return bool(self.clave)

    def _c(self):
        if self._cliente is None:
            import anthropic
            self._cliente = anthropic.Anthropic(api_key=self.clave)
        return self._cliente

    def texto(self, sistema: str, mensaje: str, rapido: bool = True, max_tokens: int | None = None) -> str | None:
        if not self.disponible:
            return None
        cfg = config()["ia"]
        try:
            r = self._c().messages.create(
                model=cfg["modelo_rapido"] if rapido else cfg["modelo_jefe"],
                max_tokens=max_tokens or cfg["max_tokens"],
                system=sistema,
                messages=[{"role": "user", "content": mensaje}],
            )
            self.llamadas += 1
            return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        except Exception as e:  # un fallo de IA no frena la ronda
            print(f"[ia] error: {e}")
            return None

    def json(self, sistema: str, mensaje: str, rapido: bool = True, max_tokens: int | None = None):
        t = self.texto(sistema + "\nRespondé SOLO con JSON válido, sin texto extra.", mensaje, rapido, max_tokens)
        if t is None:
            return None
        m = re.search(r"(\{.*\}|\[.*\])", t, re.S)
        try:
            return json.loads(m.group(1) if m else t)
        except Exception:
            print("[ia] respuesta no es JSON")
            return None
