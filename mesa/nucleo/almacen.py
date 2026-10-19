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
        self.s = requests.Session()
        self.s.headers["Authorization"] = f"Bearer {token}"
        if access_id and access_secret:  # token de servicio de Cloudflare Access
            self.s.headers["CF-Access-Client-Id"] = access_id
            self.s.headers["CF-Access-Client-Secret"] = access_secret
        self._cache: dict[str, Any] = {}

    def get(self, clave, defecto=None):
        if clave in self._cache:
            return self._cache[clave]
        r = self.s.get(f"{self.url}/api/kv/{clave}", timeout=30)
        if r.status_code == 404:
            return defecto
        r.raise_for_status()
        v = r.json()
        self._cache[clave] = v
        return v

    def put(self, clave, valor):
        r = self.s.put(f"{self.url}/api/kv/{clave}", data=json.dumps(valor, ensure_ascii=False).encode(), timeout=30,
                       headers={"Content-Type": "application/json"})
        r.raise_for_status()
        self._cache[clave] = valor

    def listar(self, prefijo):
        r = self.s.get(f"{self.url}/api/kv-lista/{prefijo}", timeout=30)
        r.raise_for_status()
        return r.json()


def almacen_por_defecto() -> Almacen:
    url = env("MESA_WORKER_URL")
    token = env("MESA_INGESTA_TOKEN")
    if url and token:
        return AlmacenWorker(url, token, env("CF_ACCESS_CLIENT_ID"), env("CF_ACCESS_CLIENT_SECRET"))
    return AlmacenLocal(env("MESA_DATOS_LOCAL", ".datos"))
