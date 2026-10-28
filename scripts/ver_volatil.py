from mesa.agentes import volatil as V, anticipadores as A
from mesa.datos import gratis
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
sp = {f: c for f, c in gratis.yahoo("SPY", "6mo")}; vx = {f: c for f, c in gratis.yahoo("^VIX", "6mo")}
mv = {f: c for f, c in gratis.yahoo("^MERV", "6mo")}
mac = (a.get("macro/series") or {}).get("series") or {}
for clave, tipo, ind, ex in (("anticipo/modelo", "mundo", sp, vx), ("anticipo_mundo/modelo", "mundo", sp, vx),
                             ("anticipo_arg/modelo", "arg", A.merval_dolares(mv, mac.get("ccl") or {}), mac.get("riesgo_pais") or {})):
    m = a.get(clave) or {}
    print(f"::notice::{clave}: hoy volátil = {V.hoy_volatil(tipo, ind, ex, (m.get('volatil') or {}).get('umbral_vol'))} | especialista={ (m.get('volatil') or {}).get('usar_especialista')}")
