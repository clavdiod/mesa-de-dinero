"""19/11: velas copiadas del día anterior (el panel del cierre vino viejo). El 17/11 pasó con 100+ papeles (VXX incluido).
Sospechosa = volumen 0 y la misma apertura/máximo/mínimo (o el mismo cierre) que la rueda anterior, desde el 20/10.
Se reemplaza con la vela real de data912 (gratis) o de IOL; si no se consigue, se borra (mejor un hueco que un dato falso)."""
from datetime import date
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.datos.cache import CacheHistorico
from mesa.datos.consumo import Consumo
from mesa.datos.iol import IOL
from mesa.datos.gratis import _S
a = almacen_por_defecto(); c = CacheHistorico(a); iol = IOL(Consumo(a), almacen=a)
panel = (a.get("ui/panel") or {}).get("titulos") or {}
_d912 = {}


def d912(tk, grupo):
    if tk not in _d912:
        seg = {"cedears": "cedears", "acciones": "stocks"}.get(grupo, "bonds")
        try:
            r = _S.get(f"https://data912.com/historical/{seg}/{tk}", timeout=30)
            _d912[tk] = {str(x.get("date"))[:10]: x for x in (r.json() if r.ok else [])}
        except Exception:
            _d912[tk] = {}
    return _d912[tk]


cambios, borradas, ok_d, ok_i = [], [], 0, 0
for tk in list(c.indice):
    v = c.velas(tk)
    malas = [i for i in range(1, len(v)) if v[i]["fecha"] >= "2026-10-20" and not v[i].get("volumen")
             and ((v[i].get("apertura"), v[i].get("maximo"), v[i].get("minimo")) == (v[i - 1].get("apertura"), v[i - 1].get("maximo"), v[i - 1].get("minimo"))
                  or v[i].get("cierre") == v[i - 1].get("cierre"))]
    if not malas:
        continue
    grupo = (panel.get(tk) or [None] * 5)[4]
    for i in reversed(malas):
        f = v[i]["fecha"]; nueva = None
        x = d912(tk, grupo).get(f)
        if x and x.get("c") and x.get("v"):
            nueva = {"fecha": f, "apertura": x.get("o") or x["c"], "maximo": x.get("h") or x["c"], "minimo": x.get("l") or x["c"], "cierre": x["c"], "volumen": x["v"], "fuente": "data912"}; ok_d += 1
        elif grupo != "cedears":
            try:
                h = [y for y in iol.historial(tk, date.fromisoformat(f), date.fromisoformat(f), ajustada=False) if y.get("fecha") == f and y.get("cierre")]
                if h and h[0].get("volumen"):
                    nueva = {**h[0], "fuente": "iol"}; ok_i += 1
            except Exception:
                pass
        if nueva:
            cambios.append(f"{tk} {f}: {v[i]['cierre']} → {nueva['cierre']}")
            v[i] = nueva
        else:
            borradas.append(f"{tk} {f}")
            v.pop(i)
    c._mem[tk] = v; c._sucio.add(tk)
    c.indice[tk] = {"desde": v[0]["fecha"], "hasta": v[-1]["fecha"], "ruedas": len(v)}
c.guardar()
print(f"::notice::corregidas {len(cambios)} (data912 {ok_d}, IOL {ok_i}) · borradas {len(borradas)}")
print("::notice::CAMBIOS " + " | ".join(cambios[:80]))
print("::notice::BORRADAS " + " | ".join(borradas[:80]))
print("::notice::VXX " + " | ".join(f"{x['fecha']} c{x['cierre']} v{x.get('volumen')} {x.get('fuente')}" for x in c.velas("VXX")[-5:]))
