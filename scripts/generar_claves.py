"""Genera las claves que van como secretos. Correr en una compu propia, NUNCA en Actions (los logs del repo son públicos).

- MESA_INGESTA_TOKEN: contraseña larga que comparten GitHub Actions y el Worker.
- VAPID_PUBLICA / VAPID_PRIVADA: para los avisos push al celular.
"""
import secrets

from mesa.nucleo.push import generar_claves

if __name__ == "__main__":
    k = generar_claves()
    print("MESA_INGESTA_TOKEN =", secrets.token_urlsafe(40))
    print("VAPID_PUBLICA      =", k["publica"])
    print("VAPID_PRIVADA      =", k["privada"])
    print("\nCopiá cada valor en GitHub → Settings → Secrets and variables → Actions → New repository secret.")
