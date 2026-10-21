"""Prueba Yahoo a 5 años para índices y acciones de EE.UU."""
import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "application/json"}
out = []
for s in ("SPY", "%5EVIX", "%5ETNX", "XLK", "AAPL"):
    try:
        r = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=5y&interval=1d", headers=UA, timeout=30)
        res = r.json()["chart"]["result"][0]
        out.append(f"{s}: {len(res['timestamp'])} días, último {res['indicators']['quote'][0]['close'][-1]}")
    except Exception as e:
        out.append(f"{s}: ERROR {e}")
print("::notice::" + " | ".join(out))
