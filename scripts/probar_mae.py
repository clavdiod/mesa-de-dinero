"""Contexto de cómo la web llama a las rutas útiles (formato de parámetros)."""
import re

import requests

H = {"User-Agent": "Mozilla/5.0", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
html = requests.get("https://marketdata.mae.com.ar/", headers=H, timeout=30).text
codigo = ""
for j in set(re.findall(r'(?:src|href)="([^"]+\.js)"', html)):
    codigo += requests.get("https://marketdata.mae.com.ar" + ("" if j.startswith("/") else "/") + j, headers=H, timeout=30).text
for c in list(set(re.findall(r'(?:assets|static/js)/[\w.\-]+\.js', codigo)))[:150]:
    try:
        codigo += requests.get("https://marketdata.mae.com.ar/" + c, headers=H, timeout=20).text
    except Exception:
        pass
out = []
for k in ("mercado/cotizaciones/rentafija", "mercado/titulo/historico", "mercado/tasaimplicita", "mercado/volumen\"", "mercado/resumen/",
          "mercado/cotizaciones/forex", "mercado/titulosactivos", "mercado/historico/preciocierre", "mercado/datos/", "mercado/repo?"):
    i = codigo.find(k.rstrip('"'))
    out.append(f"[{k}] " + (codigo[max(0, i - 500): i + 350].replace("\n", " ") if i >= 0 else "no"))
for i in range(0, len(out), 2):
    print("::notice::" + " ##### ".join(out[i:i + 2])[:3950])
