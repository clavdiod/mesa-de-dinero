"""Anticipador ARG a 20 ruedas (+12%): reentrena (con capacitación volátil) y arma la lista de hoy."""
import json, traceback
from datetime import date
from mesa.agentes import anticipadores as A, volatil as V
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
try:
    panel = (a.get("ui/panel") or {}).get("titulos") or {}
    tks = sorted(tk for tk, x in panel.items() if x and x[4] == "acciones")
    acc, mer, rp, ccl = A.datos_arg(tks, 10)
    hm = {"horizonte": 20, "meta": 12.0}
    m = A.entrenar_arg(acc, mer, rp, ccl, **hm)
    m["version"] = "usd_10a"
    print(f"::notice::modelo 20 ruedas: activo={m.get('activo')} " + json.dumps(m.get("prueba")))
    da, ua = V.dias_arg(mer, rp)
    m["volatil"] = V.capacitar(lambda **kw: A.entrenar_arg(acc, mer, rp, ccl, **hm, **kw), da, ua, "Anticipador ARG")
    print("::notice::" + m["volatil"]["texto"])
    if m.get("activo"):
        a.put("anticipo_arg/modelo", m)
        vh, vpor = V.hoy_volatil("arg", mer, rp, m["volatil"].get("umbral_vol"))
        md = V.modelo_del_dia(m, vh)
        hoy = date.today().isoformat()
        la = A.lista_arg(md, {k: v[-200:] for k, v in acc.items()}, mer, rp, ccl, hoy)
        lista = {"fecha": hoy, "activo": True, "umbral": md.get("umbral"), "horizonte": 20, "meta": 12.0, "prueba": m.get("prueba"),
                 "volatil": V.estado_lista(m, vh, vpor), "lista": [x for x in la if x["prob"] >= (md.get("umbral") or 1)][:10]}
        a.put("anticipo_arg/lista", lista)
        print("::notice::lista hoy: " + ", ".join(f"{x['ticker']} {x['prob']}" for x in lista["lista"]) + f" | volátil {vh} {vpor}")
except Exception:
    print("::notice::ERR " + traceback.format_exc().replace(chr(10), " | ")[-700:])
