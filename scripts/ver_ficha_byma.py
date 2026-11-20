"""20/11: condiciones de PR17 y BDC28 en la ficha técnica de BYMA (gratis)."""
import json
from mesa.datos.byma import ficha
for tk in ("PR17", "BDC28"):
    d = ficha(tk) or {}
    print(f"::notice::{tk} " + json.dumps({k: v for k, v in d.items() if v not in (None, "", [])}, ensure_ascii=False)[:2500])
