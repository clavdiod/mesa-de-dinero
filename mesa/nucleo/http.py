"""Sesión HTTP con reintentos ante cortes de red momentáneos (conexión cerrada, 502/503/504)."""
from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def sesion(reintentos: int = 3, metodos=("GET", "PUT", "HEAD")) -> requests.Session:
    s = requests.Session()
    r = Retry(total=reintentos, connect=reintentos, read=reintentos, backoff_factor=1.5,
              status_forcelist=(502, 503, 504), allowed_methods=frozenset(metodos), raise_on_status=False)
    s.mount("https://", HTTPAdapter(max_retries=r))
    s.mount("http://", HTTPAdapter(max_retries=r))
    return s
