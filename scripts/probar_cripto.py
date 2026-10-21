"""Prueba datos para el agente Cripto: BTC (Yahoo) y dólar cripto histórico (argentinadatos)."""
import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "application/json"}
out = []
for s in ("BTC-USD", "ETH-USD", "IBIT", "MSTR", "COIN"):
    try:
        res = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=5y&interval=1d", headers=UA, timeout=30).json()["chart"]["result"][0]
        out.append(f"{s}: {len(res['timestamp'])} días")
    except Exception as e:
        out.append(f"{s}: ERROR {e}")
try:
    d = requests.get("https://api.argentinadatos.com/v1/cotizaciones/dolares/cripto", timeout=30).json()
    out.append(f"dólar cripto: {len(d)} días, desde {d[0]['fecha']}, último {d[-1]}")
except Exception as e:
    out.append(f"dólar cripto: ERROR {e}")
print("::notice::" + " | ".join(out))
