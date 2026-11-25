"""25/11: ¿por qué la mesa dijo "VENDÉ TODO" a TGSU2 a 6.985 (comprada a 7.000, alarma 5.284)? Solo lectura; solo TGSU2."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
TK = "TGSU2"
a = almacen_por_defecto()
for k in ("usuario/cartera", "usuario/lista"):
    for x in a.get(k) or []:
        if isinstance(x, dict) and str(x.get("ticker", "")).upper() == TK:
            print(f"::notice::{k} alertas=" + json.dumps(x.get("alertas"), ensure_ascii=False)
                  + " claves=" + ",".join(sorted(x.keys())))
est = a.get("ui/estado") or {}
def buscar(o, camino=""):
    if isinstance(o, dict):
        if str(o.get("ticker", "")).upper() == TK and any(c in o for c in ("piso", "consejo", "sugerida")):
            print(f"::notice::{camino} " + json.dumps({c: o.get(c) for c in ("precio", "compra", "piso", "a_piso_pct", "consejo", "motivo",
                  "objetivo", "fuente_objetivo", "rango_1m", "sugerida", "estructura") if c in o}, ensure_ascii=False, default=str)[:1500])
        for k, v in o.items():
            buscar(v, f"{camino}/{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o[:300]):
            buscar(v, f"{camino}[{i}]")
buscar(est)
for p in a.get("registro/propuestas") or []:
    if p.get("ticker") == TK and p.get("fecha", "") >= "2026-11-24":
        print(f"::notice::propuesta {p.get('fecha')} {p.get('hora')} linea={p.get('linea')} decision={p.get('decision')} seg={json.dumps(p.get('seguimiento'))[:200]} plan={json.dumps(p.get('plan'))}")
al = [x for x in (a.get("ui/alertas") or []) if TK in str(x.get("ticker", ""))][:5]
for x in al:
    print("::notice::alerta " + json.dumps(x, ensure_ascii=False)[:700])
