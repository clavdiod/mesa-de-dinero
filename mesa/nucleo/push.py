"""Avisos push al celular sin librerías extra.

Se usa Web Push "sin contenido": la notificación solo despierta a la web instalada, que pide las
propuestas nuevas al Worker y las muestra. Así no hace falta cifrar el mensaje; alcanza con firmar
un token VAPID (ES256) con la clave privada guardada en los secretos (VAPID_PRIVADA, en base64url).
"""
from __future__ import annotations

import base64
import json
import time
from urllib.parse import urlparse

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

from .config import env


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64u_dec(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def generar_claves() -> dict:
    k = ec.generate_private_key(ec.SECP256R1())
    priv = k.private_numbers().private_value.to_bytes(32, "big")
    pub = k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return {"privada": _b64u(priv), "publica": _b64u(pub)}


def _jwt(aud: str, privada_b64u: str, sub: str) -> str:
    k = ec.derive_private_key(int.from_bytes(_b64u_dec(privada_b64u), "big"), ec.SECP256R1())
    head = _b64u(json.dumps({"typ": "JWT", "alg": "ES256"}).encode())
    body = _b64u(json.dumps({"aud": aud, "exp": int(time.time()) + 12 * 3600, "sub": sub}).encode())
    der = k.sign(f"{head}.{body}".encode(), ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der)
    return f"{head}.{body}.{_b64u(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"


def enviar(suscripciones: list[dict]) -> dict:
    priv, pub = env("VAPID_PRIVADA"), env("VAPID_PUBLICA")
    if not (priv and pub) or not suscripciones:
        return {"enviadas": 0, "vencidas": []}
    sub = env("VAPID_CONTACTO", "mailto:mesa@example.com")
    ok, vencidas = 0, []
    for s in suscripciones:
        ep = s.get("endpoint")
        if not ep:
            continue
        u = urlparse(ep)
        try:
            r = requests.post(ep, timeout=15, headers={
                "TTL": "3600", "Urgency": "high", "Content-Length": "0",
                "Authorization": f"vapid t={_jwt(f'{u.scheme}://{u.netloc}', priv, sub)}, k={pub}"})
            if r.status_code in (404, 410):
                vencidas.append(ep)
            elif r.ok:
                ok += 1
        except Exception:
            continue
    return {"enviadas": ok, "vencidas": vencidas}
