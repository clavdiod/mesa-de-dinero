"""19/11: ¿el Anticipador (sigue a Nueva York) sirve para operar coberturas como VXX? Idea de Clau.
Con la libreta real de pronósticos: comprar el CEDEAR al precio de referencia cuando el Anticipador dice 'debería subir'
y vender al cierre del día (o al tocar el objetivo). Neto de 1,2% de comisiones."""
import numpy as np
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
lib = [x for x in (a.get("pronosticos/libreta") or []) if x.get("origen") == "anticipo" and x.get("estado") in ("se_dio", "no_se_dio", "fallo")]
COB = {"VXX", "UVXY", "VIXY", "SH", "PSQ", "SDS", "SQQQ", "SPXU"}
def fin(x):  # resultado de comprar (dir 1) o no operar
    obj = x.get("objetivo_pct") or 0
    return (obj if x["estado"] == "se_dio" else (x.get("ahora_pct") or 0)) / 100 - 0.012
def linea(nom, xs):
    if not xs:
        return f"{nom}: sin casos"
    r = np.array([fin(x) for x in xs]); o = np.array([x.get("objetivo_pct") or 0 for x in xs])
    return (f"{nom}: {len(xs)} casos · se dio {np.mean([x['estado'] == 'se_dio' for x in xs]) * 100:.0f}% · movimiento esperado típico {np.median(o):.1f}% · "
            f"operando neto {r.mean() * 100:+.2f}% (gana {np.mean(r > 0) * 100:.0f}%) · fechas {min(x['fecha'] for x in xs)} a {max(x['fecha'] for x in xs)}")
sube = [x for x in lib if x.get("dir") == 1]
print("::notice::" + linea("Anticipador 'sube', todos", sube))
print("::notice::" + linea("Anticipador 'sube', esperado 3% o más", [x for x in sube if (x.get("objetivo_pct") or 0) >= 3]))
print("::notice::" + linea("Anticipador 'sube', esperado 5% o más", [x for x in sube if (x.get("objetivo_pct") or 0) >= 5]))
print("::notice::" + linea("Coberturas (VXX, SH...) 'sube'", [x for x in sube if x.get("ticker") in COB]))
print("::notice::" + linea("Anticipador 'baja' (no se opera: solo acierto)", [x for x in lib if x.get("dir") == -1]))
for x in sorted([x for x in lib if x.get("ticker") in COB], key=lambda x: x["fecha"]):
    print(f"::notice::{x['fecha']} {x['ticker']} dir {x.get('dir')} esperado {x.get('objetivo_pct')}% → {x['estado']} (al cierre {x.get('ahora_pct')}%, mejor {x.get('mejor')}%)")
rad = a.get("radar/noticias") or {}
print(f"::notice::radar/noticias: claves {list(rad)[:10] if isinstance(rad, dict) else type(rad).__name__}")
