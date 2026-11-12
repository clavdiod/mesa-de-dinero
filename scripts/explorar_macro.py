"""12/11: explorar fuentes gratis para banda cambiaria, dólar futuro, CER y tasas."""
import json
from mesa.datos.gratis import _S, _UA_JSON
from mesa.datos import byma
out = []
try:
    r = _S.get("https://api.bcra.gob.ar/estadisticas/v3.0/monetarias", timeout=30, verify=False)
    vs = r.json().get("results") or []
    clave = ("3500", "TAMAR", "BADLAR", "CER", "plazo fijo", "Plazo", "banda", "Banda", "UVA", "inflaci")
    out.append("BCRA: " + " | ".join(f"{v.get('idVariable')}:{v.get('descripcion','')[:70]}={v.get('valor')}({v.get('fecha')})" for v in vs if any(k in (v.get('descripcion') or '') for k in clave)))
except Exception as ex:
    out.append(f"BCRA ERR {ex}")
try:
    d = byma.ficha("TZXD7")
    out.append("BYMA TZXD7: " + json.dumps({k: d.get(k) for k in list(d)[:40]}, ensure_ascii=False)[:1500] if d else "BYMA TZXD7: nada")
except Exception as ex:
    out.append(f"BYMA ERR {ex}")
try:
    b = _S.get("https://data912.com/live/arg_bonds", timeout=30).json()
    out.append("data912 bonos CER: " + ", ".join(f"{x['symbol']}={x.get('c')}" for x in b if str(x.get("symbol", "")).startswith(("TZX", "X", "TX", "DICP", "PARP", "TZV", "D3"))))
except Exception as ex:
    out.append(f"data912 ERR {ex}")
for u in ["https://data912.com/live/arg_futures", "https://data912.com/live/arg_fut",
          "https://apicem.matbarofex.com.ar/api/v2/closing-prices?product=DLR&segment=Monedas&type=FUT&excludeEmptyVol=false&from=2026-11-10&to=2026-11-12",
          "https://api.marketdata.mae.com.ar/api/mercado/futuros", "https://api.marketdata.mae.com.ar/api/derivados/futuros"]:
    try:
        r = _S.get(u, headers={**_UA_JSON, "Origin": "https://marketdata.mae.com.ar", "Referer": "https://marketdata.mae.com.ar/"}, timeout=20)
        out.append(f"{u[:70]} → {r.status_code} {r.text[:400]}")
    except Exception as ex:
        out.append(f"{u[:70]} ERR {type(ex).__name__}")
for o in out:
    print("::notice::" + o.replace("\n", " ")[:4000])
