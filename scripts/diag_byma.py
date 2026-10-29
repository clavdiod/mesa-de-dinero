import json
from mesa.datos.gratis import _S
H = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json", "Accept": "application/json",
     "Origin": "https://open.bymadata.com.ar", "Referer": "https://open.bymadata.com.ar/"}
B = "https://open.bymadata.com.ar/vanoms-be-core/rest/api/bymadata/free/"
for path, body in (("bnown/fichatecnica/especies/general", {"symbol": "S29E7", "Content-Type": "application/json"}),
                   ("bnown/fichatecnica/especies/general", {"symbol": "T30A7", "Content-Type": "application/json"}),
                   ("lebacs", {"excludeZeroPxAndQty": True, "T2": True, "T1": False, "T0": False, "Content-Type": "application/json"})):
    try:
        r = _S.post(B + path, json=body, headers=H, timeout=30, verify=False)
        print(f"::notice::{path} {body.get('symbol', '')}: {r.status_code} {r.text[:900]}")
    except Exception as ex:
        print(f"::notice::{path} ERR {ex}")
