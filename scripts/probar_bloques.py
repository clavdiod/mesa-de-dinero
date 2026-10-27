"""Prueba por años (sin guardar): ¿las herramientas activas le ganan al promedio año por año?"""
import json
from concurrent.futures import ThreadPoolExecutor
from mesa.agentes import ganadores, profesionales as pro
from mesa.cierre import _universo_cedears
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
uni = _universo_cedears(a)
with ThreadPoolExecutor(8) as ex:
    s5 = {tk: f for tk, f in zip(uni, ex.map(lambda t: gratis.yahoo_ohlcv(t.replace(".", "-"), "5y"), uni)) if len(f) > 300}
g = ganadores.entrenar(s5)
for k, v in g["estrategias"].items():
    print(f"::notice::GAN {k} activa={v['activa']} plazo={v['plazo']} " + json.dumps({h: {x: y.get(x) for x in ('exceso', 'acierto', 'casos', 'anios_a_favor', 'por_anio', 'estable')} for h, y in v['horizontes'].items()}))
p5 = {tk: [[x["fecha"], x["c"]] for x in f] for tk, f in s5.items()}
etfs = {e: gratis.yahoo(e, "5y") for e in pro.NOMBRE_SECTOR}
r = pro.entrenar(p5, etfs, {k: v for k, v in (a.get("profesionales/sectores") or {}).items() if v},
                 (a.get("profesionales/consensos") or {}).get("datos") or {}, (a.get("profesionales/insiders_hist") or {}).get("lista") or [])
for k, v in r["herramientas"].items():
    print(f"::notice::PRO {k} activa={v['activa']} plazo={v['plazo']} " + json.dumps({h: {x: y.get(x) for x in ('exceso', 'exceso_mediana', 'acierto', 'casos', 'anios_a_favor', 'por_anio', 'estable')} for h, y in v['horizontes'].items()}))
