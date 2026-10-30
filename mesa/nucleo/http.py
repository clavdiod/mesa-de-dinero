"""Sesión HTTP con reintentos ante cortes de red momentáneos (conexión cerrada, 502/503/504)."""
from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class _Sesion(requests.Session):
    """Además de los reintentos de urllib3: si la respuesta se corta a mitad de camino (ChunkedEncodingError,
    pasa con KV/IOL de vez en cuando), se vuelve a pedir hasta 2 veces. Antes eso tiraba la ronda entera (30/10 15:00)."""
    def request(self, *a, **kw):
        import time
        for i in range(3):
            try:
                return super().request(*a, **kw)
            except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError):
                if i == 2:
                    raise
                time.sleep(1.5 * (i + 1))


def sesion(reintentos: int = 3, metodos=("GET", "PUT", "HEAD")) -> requests.Session:
    s = _Sesion()
    r = Retry(total=reintentos, connect=reintentos, read=reintentos, backoff_factor=1.5,
              status_forcelist=(502, 503, 504), allowed_methods=frozenset(metodos), raise_on_status=False)
    s.mount("https://", HTTPAdapter(max_retries=r))
    s.mount("http://", HTTPAdapter(max_retries=r))
    return s
