"""Anticipador ARG con 10, 15 y 20 años (todo en dólares CCL), los tres examinados con los MISMOS últimos 3 años.
Solo guarda si el más largo le gana al de 10 años que está en uso. Muestra desde cuándo hay datos."""
import json, traceback
from datetime import date, timedelta
from mesa.agentes import anticipadores as A
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
panel = (a.get("ui/panel") or {}).get("titulos") or {}
tks = sorted(tk for tk, x in panel.items() if x and x[4] == "acciones")
acc, mer, rp, ccl = A.datos_arg(tks, 20)
print(f"::notice::{len(acc)} acciones; velas desde {min(v[0]['fecha'] for v in acc.values())}; merval desde {min(mer) if mer else '-'}; "
      f"riesgo país desde {min(rp) if rp else '-'}; CCL desde {min(ccl) if ccl else '-'}")
print("::notice::acciones con 15+ años: " + str(sum(1 for v in acc.values() if v[0]['fecha'] <= (date.today() - timedelta(days=365 * 15)).isoformat())))
examen = (date.today() - timedelta(days=365 * 3)).isoformat()
res = {}
for anios in (10, 15, 20):
    d = (date.today() - timedelta(days=365 * anios)).isoformat()
    ser = {tk: [x for x in f if x["fecha"] >= d] for tk, f in acc.items()}
    ser = {k: v for k, v in ser.items() if len(v) > 300}
    try:
        m = A.entrenar_arg(ser, {f: v for f, v in mer.items() if f >= d}, rp, ccl, desde_prueba=examen)
        res[anios] = m
        print(f"::notice::{anios} años: activo={m.get('activo')} " + json.dumps(m.get("prueba")) + " | " + str(m.get("importancia"))[:150])
    except Exception:
        print(f"::notice::{anios} años ERROR " + traceback.format_exc().replace(chr(10), " | ")[-600:])
b = (res.get(10) or {}).get("prueba") or {}
mejor = None
for anios in (15, 20):
    p = (res.get(anios) or {}).get("prueba") or {}
    if res.get(anios, {}).get("activo") and p.get("top10_pct", 0) >= b.get("top10_pct", 0) and p.get("ret5_top10", 0) > b.get("ret5_top10", 0) + 0.2:
        if not mejor or p["ret5_top10"] > mejor[1]["prueba"]["ret5_top10"]:
            mejor = (anios, res[anios])
if mejor:
    mejor[1]["version"] = f"usd_{mejor[0]}a"
    a.put("anticipo_arg/modelo", mejor[1])
    print(f"::notice::GANÓ {mejor[0]} años: se guarda (version usd_{mejor[0]}a)")
else:
    print("::notice::Más historia no mejora el examen: queda el de 10 años")
