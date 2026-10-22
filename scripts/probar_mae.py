"""emisiones/flujofondos/{ticker} en MAE."""
import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
B = "https://api.marketdata.mae.com.ar/api/"
out = []
for tk in ("TTD26", "YM34O", "AL30", "GD30", "S13N6", "PN35O", "TLCMO"):
    r = requests.get(B + f"emisiones/flujofondos/{tk}", headers=H, timeout=20)
    out.append(f"{tk}: {r.status_code} {r.text[:900]}")
print("::notice::" + " ||| ".join(out)[:3950])
