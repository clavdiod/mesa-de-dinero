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
    ok, vencidas, codigos = 0, [], []
    for s in suscripciones:
        ep = s.get("endpoint")
        if not ep:
            continue
        u = urlparse(ep)
        try:
            r = requests.post(ep, timeout=15, headers={
                "TTL": "3600", "Urgency": "high", "Content-Length": "0",
                "Authorization": f"vapid t={_jwt(f'{u.scheme}://{u.netloc}', priv, sub)}, k={pub}"})
            codigos.append(f"{u.netloc}:{r.status_code}")
            if r.status_code in (404, 410):
                vencidas.append(ep)
            elif r.ok:
                ok += 1
        except Exception as ex:
            codigos.append(f"{u.netloc}:error {type(ex).__name__}")
            continue
    return {"enviadas": ok, "vencidas": vencidas, "codigos": codigos}


# ---------- 19/11: que avise SIEMPRE ----------
# A las 12:10 del 19/11 Google (FCM) contestó 410: la suscripción del celular había vencido y se borró. La propuesta de
# VXX de las 12:40 no llegó. Ahora:
# 1) la suscripción vencida se anota (push/vencidas) y queda marcado el corte (push/corte), así la app, al abrirse,
#    sabe que tiene que pedir una suscripción NUEVA (no reusar la vieja) y la reemplaza sola;
# 2) si el aviso importante no llegó a ningún celular, va por el canal de respaldo (ntfy, gratis), si está configurado;
# 3) apenas se detecta el corte, también se avisa por el respaldo que hay que abrir la app.
def _respaldo(almacen, titulo: str, texto: str, prioridad: int = 4) -> bool:
    tema = env("NTFY_TEMA") or ((almacen.get("usuario/ntfy") or {}).get("tema") if almacen is not None else None)
    if not tema:
        return False
    try:
        r = requests.post("https://ntfy.sh", timeout=15, json={"topic": tema, "title": titulo[:120], "message": texto[:900],
                                                              "priority": prioridad, "tags": ["chart_with_upwards_trend"]})
        print(f"[push] respaldo ntfy: {r.status_code}")
        return r.ok
    except Exception as ex:
        print(f"[push] respaldo ntfy error: {ex}")
        return False


def avisar(almacen, titulo: str | None = None, texto: str | None = None, importante: bool = False) -> dict:
    """Manda el push a todos los celulares; maneja las vencidas y usa el respaldo si un aviso importante no llegó."""
    from ..nucleo.reloj import ahora
    subs = almacen.get("push/suscripciones") or []
    res = enviar(subs)
    print(f"[push] {len(subs)} suscripciones, enviadas {res['enviadas']}: {res.get('codigos')}")
    t = ahora()
    if res["vencidas"]:
        almacen.put("push/suscripciones", [s for s in subs if s.get("endpoint") not in res["vencidas"]])
        venc = (almacen.get("push/vencidas") or []) + [{"endpoint": e, "fecha": t.date().isoformat(), "hora": t.strftime("%H:%M")} for e in res["vencidas"]]
        almacen.put("push/vencidas", venc[-20:])
    if res["enviadas"] == 0:
        corte = almacen.get("push/corte") or {}
        nuevo = not corte.get("desde")
        if nuevo:
            corte = {"desde": f"{t.date().isoformat()} {t.strftime('%H:%M')}", "avisado": False}
        if not corte.get("avisado"):
            av = _respaldo(almacen, "🔕 Se cortaron los avisos de la mesa",
                           "El celular dejó de recibir las notificaciones. Abrí la app de la mesa para reactivarlas (es automático).", 5)
            if av or nuevo:
                corte["avisado"] = av
                almacen.put("push/corte", corte)
        if importante and titulo:
            res["respaldo"] = _respaldo(almacen, titulo, texto or "Entrá a la mesa para ver el detalle.")
    elif (almacen.get("push/corte") or {}).get("desde"):
        almacen.put("push/corte", {})  # volvió a andar
    return res
