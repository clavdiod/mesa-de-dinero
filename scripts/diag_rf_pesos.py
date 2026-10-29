"""¿Qué hay en pesos? ONs con línea O sin línea D (las que pagan pesos) + letras/bonos en pesos del panel; cronogramas de MAE."""
import json, collections, traceback
from datetime import date
from mesa.datos import cobros
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
try:
    pan = (a.get("ui/panel") or {}).get("titulos") or {}
    ons_o = sorted(tk for tk, x in pan.items() if x and x[4] == "ons" and tk.endswith("O") and (tk[:-1] + "D") not in pan and x[2] and x[3])
    otros = sorted(tk for tk, x in pan.items() if x and x[4] in ("letras", "soberanos") and not tk.endswith(("D", "C")) and x[2] and x[3])
    print(f"::notice::ONs solo en pesos con puntas: {len(ons_o)}: " + ", ".join(ons_o[:60]))
    print(f"::notice::letras/bonos pesos: {len(otros)}: " + ", ".join(otros))
    fl = cobros.asegurar_flujos(a, ons_o + otros, date.today(), maximo=200)
    mon = collections.Counter(str((fl.get(t) or {}).get("moneda")) for t in ons_o + otros)
    print("::notice::monedas " + json.dumps(mon))
    con = [t for t in ons_o + otros if (fl.get(t) or {}).get("flujos")]
    for t in con[:14]:
        f = fl[t]; fu = [x for x in f["flujos"] if x["fecha"] >= date.today().isoformat()]
        print(f"::notice::{t} {pan[t][:4]} | {f.get('moneda')} {f.get('descripcion')} | {len(fu)} pagos futuros: " + json.dumps(fu[:4]))
except Exception:
    print("::notice::ERR " + traceback.format_exc().replace(chr(10), " | ")[-800:])
