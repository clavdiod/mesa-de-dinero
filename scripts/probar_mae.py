"""Cadena de redirecciones de un link de SharePoint de A3 (para replicarla en el Worker)."""
import requests

H = {"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}
d = requests.get("https://api.marketdata.mae.com.ar/api/mercado/boletin-mpmae", headers=H, timeout=30).json()[0]
u = d["url"] + ("&" if "?" in d["url"] else "?") + "download=1"
out = [u]
cookies = {}
for i in range(8):
    r = requests.get(u, allow_redirects=False, headers={"User-Agent": "Mozilla/5.0", "Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items())}, timeout=30)
    for c in r.raw.headers.getlist("Set-Cookie") if hasattr(r.raw.headers, "getlist") else []:
        k, v = c.split(";")[0].split("=", 1)
        cookies[k] = v
    out.append(f"{r.status_code} ct={r.headers.get('content-type','')[:25]} loc={(r.headers.get('location') or '')[:120]} cookies={list(cookies)} pdf={r.content[:4] == b'%PDF'}")
    if r.status_code in (301, 302, 303, 307, 308):
        loc = r.headers["location"]
        u = loc if loc.startswith("http") else "https://mercadoabierto.sharepoint.com" + loc
    else:
        break
# sin cookies
r = requests.get(out[0], allow_redirects=True, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
out.append(f"requests normal: {r.status_code} final={r.url[:100]} pdf={r.content[:4] == b'%PDF'} hist={[x.status_code for x in r.history]}")
print("::notice::" + " || ".join(out)[:3900])
