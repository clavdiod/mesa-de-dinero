"""Prueba si Yahoo devuelve el precio de pre-market (includePrePost) para algunos papeles."""
import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "application/json"}
out = []
for s in ("MSTR", "AAPL", "GGAL"):
    try:
        res = requests.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=1d&interval=5m&includePrePost=true", headers=UA, timeout=20).json()["chart"]["result"][0]
        m, ts = res["meta"], res.get("timestamp") or []
        cl = [c for c in res["indicators"]["quote"][0]["close"] if c]
        out.append(f"{s}: velas={len(ts)} última={cl[-1] if cl else None} regular={m.get('regularMarketPrice')} anterior={m.get('chartPreviousClose')} "
                   f"periodo={m.get('currentTradingPeriod', {}).get('pre', {})}")
    except Exception as e:
        out.append(f"{s}: ERROR {e}")
print("::notice::" + " | ".join(out)[:3500])
