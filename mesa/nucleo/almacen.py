"""Almacenamiento privado de la mesa.

En producción los datos viven en Cloudflare KV, detrás del Worker (nunca en el repo público).
Para pruebas locales se usa una carpeta. Ambos exponen la misma interfaz get/put de JSON.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import requests

from .config import env


class Almacen:
    def get(self, clave: str, defecto: Any = None) -> Any:  # pragma: no cover - interfaz
        raise NotImplementedError

    def put(self, clave: str, valor: Any) -> None:  # pragma: no cover - interfaz
        raise NotImplementedError

    def listar(self, prefijo: str) -> list[str]:  # pragma: no cover - interfaz
        raise NotImplementedError


class AlmacenLocal(Almacen):
    def __init__(self, carpeta: str | Path):
        self.carpeta = Path(carpeta)
        self.carpeta.mkdir(parents=True, exist_ok=True)

    def _ruta(self, clave: str) -> Path:
        return self.carpeta / (clave.replace("/", "__") + ".json")

    def get(self, clave, defecto=None):
        p = self._ruta(clave)
        if not p.exists():
            return defecto
        return json.loads(p.read_text(encoding="utf-8"))

    def put(self, clave, valor):
        self._ruta(clave).write_text(json.dumps(valor, ensure_ascii=False, indent=1), encoding="utf-8")

    def listar(self, prefijo):
        pre = prefijo.replace("/", "__")
        return sorted(p.stem.replace("__", "/") for p in self.carpeta.glob(pre + "*.json"))


class AlmacenWorker(Almacen):
    """Habla con el Worker de Cloudflare usando un secreto compartido (MESA_INGESTA_TOKEN)."""

    def __init__(self, url: str, token: str, access_id: str | None = None, access_secret: str | None = None):
        url = url.strip().rstrip("/")
        if not url.startswith(("http://", "https://")):
            url = "https://" + url  # tolera que el secreto se haya cargado sin https://
        self.url = url
        from .http import sesion
        self.s = sesion()
        self.s.headers["Authorization"] = f"Bearer {token}"
        if access_id and access_secret:  # token de servicio de Cloudflare Access
            self.s.headers["CF-Access-Client-Id"] = access_id
            self.s.headers["CF-Access-Client-Secret"] = access_secret
        self._cache: dict[str, Any] = {}
        self._foto: dict[str, str] = {}   # cómo estaba guardado cada valor (para no reescribir lo que no cambió)
        self.escrituras = 0
        self.omitidas = 0

    def get(self, clave, defecto=None):
        if clave in self._cache:
            return self._cache[clave]
        r = self.s.get(f"{self.url}/api/kv/{clave}", timeout=30)
        if r.status_code == 404:
            self._foto[clave] = "null"
            return defecto
        r.raise_for_status()
        v = r.json()
        self._cache[clave] = v
        self._foto[clave] = json.dumps(v, ensure_ascii=False, sort_keys=True)
        return v

    def put(self, clave, valor):
        """Cloudflare KV gratis permite ~1.000 escrituras por día: si el valor no cambió, no se escribe."""
        nuevo = json.dumps(valor, ensure_ascii=False, sort_keys=True)
        if self._foto.get(clave) == nuevo:
            self.omitidas += 1
            return
        r = self.s.put(f"{self.url}/api/kv/{clave}", data=json.dumps(valor, ensure_ascii=False).encode(), timeout=30,
                       headers={"Content-Type": "application/json"})
        r.raise_for_status()
        self.escrituras += 1
        self.escritas = getattr(self, "escritas", []) + [clave]
        self._cache[clave] = valor
        self._foto[clave] = nuevo

    def listar(self, prefijo):
        r = self.s.get(f"{self.url}/api/kv-lista/{prefijo}", timeout=30)
        r.raise_for_status()
        return r.json()


class AlmacenDelDia:
    """Envuelve al almacén: las claves "del día" (fotos de ADRs, registro de anticipos, historial del radar)
    no se escriben aparte sino dentro de ui/estado, que la ronda escribe igual. Ahorra 3 escrituras por ronda."""
    PREFIJOS = ("adr/fotos/", "anticipo/2", "radar/2")

    def __init__(self, base, dia: dict):
        self.base, self.dia = base, dia

    def _propia(self, clave: str) -> bool:
        return clave.startswith(self.PREFIJOS)

    def get(self, clave, defecto=None):
        if self._propia(clave):
            return self.dia.get(clave, defecto)
        return self.base.get(clave, defecto)

    def put(self, clave, valor):
        if self._propia(clave):
            self.dia[clave] = valor
        else:
            self.base.put(clave, valor)

    def __getattr__(self, nombre):
        return getattr(self.base, nombre)


def almacen_por_defecto() -> Almacen:
    url = env("MESA_WORKER_URL")
    token = env("MESA_INGESTA_TOKEN")
    if url and token:
        return AlmacenWorker(url, token, env("CF_ACCESS_CLIENT_ID"), env("CF_ACCESS_CLIENT_SECRET"))
    return AlmacenLocal(env("MESA_DATOS_LOCAL", ".datos"))
