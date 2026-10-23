"""Formato detallado de Nasdaq (perfil, consenso) y OpenInsider."""
import json
import re

import requests

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36", "Accept": "application/json, text/html"}
p = requests.get("https://api.nasdaq.com/api/company/NVDA/company-profile", headers=UA, timeout=25).json()["data"]
print("::notice::PERFIL " + json.dumps({k: (v.get("value") if isinstance(v, dict) else v) for k, v in p.items() if k in ("Sector", "Industry", "CompanyName", "Region")}, ensure_ascii=False))
t = requests.get("https://api.nasdaq.com/api/analyst/NVDA/targetprice", headers=UA, timeout=25).json()["data"]
print("::notice::TARGET " + json.dumps(t, ensure_ascii=False)[:3500])
r = requests.get("https://api.nasdaq.com/api/analyst/NVDA/ratings", headers=UA, timeout=25).json()["data"]
print("::notice::RATINGS " + json.dumps(r, ensure_ascii=False)[:1500])
h = requests.get("http://openinsider.com/screener?s=CRWD&fd=1461&xp=1&cnt=100&page=1&sortcol=0", headers=UA, timeout=25).text
tabla = re.search(r'<table[^>]*class="tinytable"[^>]*>(.*?)</table>', h, re.S)
filas = re.findall(r"<tr[^>]*>(.*?)</tr>", tabla.group(1), re.S) if tabla else []
celdas = [[re.sub(r"<[^>]+>", "", c).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", f, re.S)] for f in filas[:6]]
print("::notice::OPENINSIDER " + f"{len(filas)} filas || " + json.dumps(celdas, ensure_ascii=False)[:2500])
