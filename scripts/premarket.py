"""Cómo vienen ahora (pre-market de EE.UU.) los papeles de la cartera."""
from mesa.datos.gratis import _S
for sym in ["ETSY", "BAK", "SPY"]:
    try:
        j = _S.get(f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}", params={"interval": "5m", "range": "1d", "includePrePost": "true"},
                   headers={"User-Agent": "Mozilla/5.0"}, timeout=20).json()["chart"]["result"][0]
        m = j["meta"]; cl = [c for c in j["indicators"]["quote"][0]["close"] if c]
        prev = m.get("chartPreviousClose") or m.get("previousClose")
        ult = cl[-1] if cl else m.get("regularMarketPrice")
        print(f"::notice::{sym} cierre {prev} ahora {ult:.3f} ({(ult / prev - 1) * 100:+.2f}%) regular {m.get('regularMarketPrice')}")
    except Exception as ex:
        print(f"::notice::{sym} error {ex}")
