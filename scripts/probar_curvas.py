from datetime import date
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.reloj import ahora
from mesa.nucleo.config import config
from mesa.agentes import curvas
from mesa.datos import macro_ar
a = almacen_por_defecto(); hoy = ahora().date()
fich = a.get("macro/cer_fichas2") or {}
cer_b = macro_ar.bonos_cer(None, fich); a.put("macro/cer_fichas2", fich)
bc = macro_ar.bcra_ultimos()
cer = macro_ar.bcra_serie(30, date(2023, 1, 1)); inf = macro_ar.bcra_serie(27, date(2025, 1, 1))
fut = macro_ar.dolar_futuro(hoy)
lec = (a.get("renta_fija/propuestas") or {}).get("lecaps") or []
exp_ = ((a.get("ministro/series") or {}).get("series") or {}).get("expectativa") or {}
r = curvas.armar(hoy, bc, fut, cer_b, cer, lec, inf, config().get("banda") or {}, exp_[max(exp_)] if exp_ else None)
a.put("macro/curvas", r)
print(f"::notice::BCRA {bc} · CER puntos {len(cer)} (último {max(cer) if cer else None}) · inflación {dict(list(sorted(inf.items()))[-3:])} · futuros {len(fut)} · CER bonos {len(cer_b)} · LECAPs {len(lec)}")
for l in r["lineas"]:
    print("::notice::" + l)
print("::notice::futuros: " + " | ".join(f"{f['contrato']} {f['precio']} dev/mes {f['devaluacion_mensual_pct']}%" for f in r["futuros"]))
print("::notice::CER: " + " | ".join(f"{c['ticker']} {c['precio']} VT {c['valor_tecnico']} TIR real {c['tir_real_pct']}%" for c in r["cer"]))
print("::notice::breakeven: " + " | ".join(f"{p['lecap']}/{p['cer']} {p['inflacion_implicita_mensual']}%" for p in r["breakeven"]))
