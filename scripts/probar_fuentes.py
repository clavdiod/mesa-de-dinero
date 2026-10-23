"""Fuentes gratis para: revisiones de analistas, compras de insiders y sectores."""
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36", "Accept": "application/json, text/html"}
out = []
def prueba(nombre, url, **kw):
    try:
        r = requests.get(url, headers={**UA, **kw.get("h", {})}, timeout=25)
        out.append(f"{nombre}: {r.status_code} {len(r.text)}B {r.text[:260]!r}")
        return r
    except Exception as e:
        out.append(f"{nombre}: ERR {e}")
prueba("yahoo upgrades", "https://query2.finance.yahoo.com/v10/finance/quoteSummary/AAPL?modules=upgradeDowngradeHistory")
s = requests.Session(); s.headers.update(UA)
try:
    s.get("https://fc.yahoo.com", timeout=15)
    crumb = s.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=15).text
    r = s.get(f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/AAPL?modules=upgradeDowngradeHistory,assetProfile&crumb={crumb}", timeout=20)
    out.append(f"yahoo con crumb ({crumb[:8]}): {r.status_code} {r.text[:300]!r}")
except Exception as e:
    out.append(f"yahoo crumb ERR {e}")
prueba("nasdaq ratings", "https://api.nasdaq.com/api/analyst/AAPL/ratings")
prueba("nasdaq target", "https://api.nasdaq.com/api/analyst/AAPL/targetprice")
prueba("nasdaq perfil", "https://api.nasdaq.com/api/company/AAPL/company-profile")
prueba("nasdaq insiders", "https://api.nasdaq.com/api/company/AAPL/insider-trades?limit=20&type=ALL&sortColumn=lastDate&sortOrder=DESC")
r = prueba("openinsider", "http://openinsider.com/screener?s=NVDA&o=&pl=&ph=&ll=&lh=&fd=1461&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&vl=&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=100&page=1")
if r is not None:
    out.append("openinsider filas: " + str(len(re.findall(r"<tr", r.text))))
prueba("sec submissions", "https://data.sec.gov/submissions/CIK0000320193.json", h={"User-Agent": "mesa-de-dinero contacto@example.com"})
print("::notice::" + " ||| ".join(out)[:3950])
