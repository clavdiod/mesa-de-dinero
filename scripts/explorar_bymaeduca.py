"""16/11: tablero.bymaeduca.com.ar es un HTML de 2,8 MB con los datos adentro. ¿Qué trae?"""
import re, json
from collections import Counter
from mesa.datos.gratis import _S
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
html = _S.get("https://tablero.bymaeduca.com.ar", headers=H, timeout=60).text
scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
print(f"::notice::{len(scripts)} scripts inline; tamaños: {[len(s) for s in scripts][:15]}")
grande = max(scripts, key=len) if scripts else ""
print("::notice::inicio del script grande: " + grande[:700].replace("\n", " "))
fechas = re.findall(r"20[12]\d-[01]\d-[0-3]\d", html)
print(f"::notice::fechas: {len(fechas)} · desde {min(fechas) if fechas else None} hasta {max(fechas) if fechas else None}")
claves = Counter(re.findall(r'"([a-zA-Z_][a-zA-Z0-9_]{2,30})"\s*:', html))
print("::notice::claves JSON más comunes: " + ", ".join(f"{k}({n})" for k, n in claves.most_common(45)))
for pal in ("balance", "Balance", "dividend", "Dividend", "hecho", "calendario", "Calendario", "EECC", "estados contables", "vencim"):
    i = html.find(pal)
    if i >= 0:
        print(f"::notice::'{pal}': …{html[max(0, i - 200):i + 300]}…".replace("\n", " ")[:600])
tks = Counter(re.findall(r'"(?:symbol|ticker|simbolo|especie)"\s*:\s*"([A-Z0-9.]{2,10})"', html))
print(f"::notice::{len(tks)} especies: " + ", ".join(list(tks)[:80]))
