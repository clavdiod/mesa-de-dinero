"""25/11: qué dice la mesa de DGCU2 (aviso de vendedores fuertes) y de la alarma de METR. Solo lectura; solo esos dos tickers."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
est = a.get("ui/estado") or {}
for TK in ("DGCU2", "METR"):
    for x in a.get("usuario/cartera") or []:
        if isinstance(x, dict) and str(x.get("ticker", "")).upper() == TK:
            print(f"::notice::{TK} alertas=" + json.dumps(x.get("alertas"), ensure_ascii=False) + f" propuesta_id={x.get('propuesta_id')} obj={x.get('objetivo_idea')}")
    def buscar(o, camino=""):
        if isinstance(o, dict):
            if str(o.get("ticker", "")).upper() == TK and any(c in o for c in ("piso", "consejo", "sugerida", "motivo")):
                print(f"::notice::{TK} {camino} " + json.dumps({c: o.get(c) for c in ("precio", "piso", "fuente", "a_piso_pct", "consejo", "accion", "motivo",
                      "objetivo", "fuente_objetivo", "sugerida", "estructura", "texto") if c in o}, ensure_ascii=False, default=str)[:1500])
            for k, v in o.items():
                buscar(v, f"{camino}/{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o[:300]):
                buscar(v, f"{camino}[{i}]")
    buscar(est)
    for x in [x for x in (a.get("ui/alertas") or []) if TK in str(x.get("ticker", "")) or TK in str(x.get("texto", ""))][:4]:
        print(f"::notice::{TK} alerta " + json.dumps(x, ensure_ascii=False)[:800])
