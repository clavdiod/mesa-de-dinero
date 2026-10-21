"""Prueba fuentes gratis de precios diarios de EE.UU. para armar el historial de CEDEARs."""
import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "application/json"}
out = []
try:
    r = requests.get("https://api.nasdaq.com/api/quote/AAPL/historical?assetclass=stocks&fromdate=2025-09-01&todate=2026-10-20&limit=600", headers=UA, timeout=30)
    filas = ((r.json().get("data") or {}).get("tradesTable") or {}).get("rows") or []
    out.append(f"nasdaq: HTTP {r.status_code}, {len(filas)} días, {filas[0] if filas else ''} … {filas[-1] if filas else ''}")
except Exception as e:
    out.append(f"nasdaq: ERROR {e}")
try:
    r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/AAPL?range=2y&interval=1d", headers=UA, timeout=30)
    res = (r.json().get("chart") or {}).get("result") or []
    n = len(res[0]["timestamp"]) if res else 0
    out.append(f"yahoo: HTTP {r.status_code}, {n} días")
except Exception as e:
    out.append(f"yahoo: ERROR {e}")
print("::notice::" + " | ".join(out)[:3500])
