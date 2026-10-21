"""Prueba fuentes gratis para el historial de CEDEARs: precio de EE.UU. (Stooq) y CCL histórico (argentinadatos)."""
import requests

out = []
for sym in ("aapl", "ko"):
    try:
        r = requests.get(f"https://stooq.com/q/d/l/?s={sym}.us&i=d", timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        lineas = r.text.strip().splitlines()
        out.append(f"stooq {sym}: HTTP {r.status_code}, {len(lineas)} líneas, {lineas[0][:60] if lineas else ''} … {lineas[-1][:60] if lineas else ''}")
    except Exception as e:
        out.append(f"stooq {sym}: ERROR {e}")
try:
    r = requests.get("https://api.argentinadatos.com/v1/cotizaciones/dolares/contadoconliqui", timeout=30)
    d = r.json()
    out.append(f"ccl: HTTP {r.status_code}, {len(d)} días, último {d[-1]}")
except Exception as e:
    out.append(f"ccl: ERROR {e}")
print("::notice::" + " | ".join(out))
