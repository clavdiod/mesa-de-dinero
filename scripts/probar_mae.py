"""Cómo arma la web los parámetros de detalle y flujo de fondos."""
import re

import requests

H = {"User-Agent": "Mozilla/5.0", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
html = requests.get("https://marketdata.mae.com.ar/", headers=H, timeout=30).text
codigo = ""
for j in set(re.findall(r'(?:src|href)="([^"]+\.js)"', html)):
    codigo += requests.get("https://marketdata.mae.com.ar" + ("" if j.startswith("/") else "/") + j, headers=H, timeout=30).text
for c in list(set(re.findall(r'(?:assets|static/js)/[\w.\-]+\.js', codigo)))[:200]:
    try:
        codigo += "\n/*F " + c + "*/\n" + requests.get("https://marketdata.mae.com.ar/" + c, headers=H, timeout=20).text
    except Exception:
        pass
out = []
for k in ("GetTitleFlujoFondos(", "GetTitleInfo(", "GetTitleInfoList(", "flujoFondos", "idEmision", "codigoEmision"):
    for m in list(re.finditer(re.escape(k), codigo))[:2]:
        i = m.start()
        out.append(f"[{k}] " + codigo[max(0, i - 400): i + 300].replace("\n", " "))
for i in range(0, len(out), 3):
    print("::notice::" + " ##### ".join(out[i:i + 3])[:3950])
