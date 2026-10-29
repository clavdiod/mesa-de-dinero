"""Baja los cronogramas de MAE de todas las ONs en dólares (línea D) y arma las propuestas de renta fija."""
import json, collections, traceback
from datetime import date
from mesa.agentes import renta_fija as R
from mesa.datos import cobros, eventos
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
try:
    pan = dict((a.get("ui/panel") or {}).get("titulos") or {})
    from mesa.datos import gratis
    for t in gratis.data912("bonos"):  # hasta que la ronda los sume al panel
        pan.setdefault(t["simbolo"], [t["ultimo"], t["variacion"], t["compra"], t["venta"], "bonos"])
    print("::notice::bonos data912: " + ", ".join(sorted(t for t, x in pan.items() if x[4] == "bonos"))[:900])
    tks = sorted(tk for tk, x in pan.items() if x and len(x) > 4 and x[2] and x[3] and ((x[4] == "ons" and tk.endswith("D"))
                  or (x[4] in ("ons", "letras", "soberanos", "bonos") and not tk.endswith(("D", "C")) and (x[4] != "ons" or (tk[:-1] + "D") not in pan))))
    print(f"::notice::{len(tks)} ONs en dólares con puntas")
    hoy = date.today()
    fl = cobros.asegurar_flujos(a, tks, hoy, maximo=400)
    mon = collections.Counter(str((fl.get(t) or {}).get("moneda")) for t in tks)
    print("::notice::monedas MAE " + json.dumps(mon))
    cal = a.get("calificadoras/ultimo") or {}
    malas = {str(c.get("ticker") or "").upper() for c in cal.get("cambios", []) if int(c.get("dir", 0)) < 0}
    tengo = {str(x.get("ticker", "")).upper() for x in (a.get("usuario/cartera") or [])}
    res = R.proponer(pan, fl, eventos.flujos_bonos(), hoy, malas, tengo)
    a.put("renta_fija/propuestas", res)
    print(f"::notice::analizados {res['analizados']}, aptos {res['aptos']}")
    print("::notice::pesos vistos: " + json.dumps(res.get("pesos_vistos"), ensure_ascii=False)[:1500])
    sinmae = [t for t, x in pan.items() if x[4] == "bonos" and not t.endswith(("D", "C")) and str((fl.get(t) or {}).get("moneda")) == "ARS"]
    print("::notice::bonos con MAE ARS: " + ", ".join(sinmae) + " | precios " + json.dumps({t: pan[t][:4] for t in sinmae})[:700])
    for g in ("ons", "soberanos", "pesos"):
        for x in res[g]:
            print(f"::notice::{g} {x['ticker']} {x['descripcion'][:40]} | precio {x['precio']} TIR {x['tir']}% dur {x['duration']} vence {x['vence']} "
                  f"{x['frecuencia']} tasa {x['tasa']} {x.get('tasa_txt') or ''} pagos/año {x['pagos_por_anio']} renta actual {x['renta_actual_pct']}% | próximo {x['proximo']} | 1000 USD → {x['ejemplo']['nominales']} VN, 12m {x['ejemplo']['cobras_12m']}")
except Exception:
    print("::notice::ERR " + traceback.format_exc().replace(chr(10), " | ")[-800:])
