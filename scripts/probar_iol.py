"""Prueba de conexión con IOL y descubrimiento de paneles (correr UNA vez desde Actions → 'probar-iol').

- Se loguea, lista instrumentos y paneles reales, y busca el nombre exacto de cada panel de config/mesa.yaml.
- Guarda el mapeo en el almacén (iol/paneles) para que las rondas usen los nombres correctos.
- Pide 1 panel de muestra e imprime los campos que devuelve (para verificar la normalización).
Consume ~10-15 consultas del cupo mensual, y quedan anotadas en el contador.
"""
from __future__ import annotations

import json
import unicodedata

from mesa.datos.consumo import Consumo
from mesa.datos.iol import IOL
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.config import config


def _n(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return "".join(ch for ch in s if ch.isalnum())


def _nombres(x) -> list[str]:
    if isinstance(x, list):
        out = []
        for i in x:
            if isinstance(i, dict):
                out.append(i.get("panel") or i.get("instrumento") or i.get("nombre") or next(iter(i.values())))
            else:
                out.append(str(i))
        return [o for o in out if o]
    return []


def main():
    a = almacen_por_defecto()
    c = Consumo(a)
    iol = IOL(c, almacen=a)
    insts = _nombres(iol.instrumentos())
    print("Instrumentos:", insts)
    _anotar("notice", "Instrumentos IOL: " + json.dumps(iol.instrumentos(), ensure_ascii=False)[:1500])
    mapeo = {}
    for p in config()["iol"]["paneles"]:
        inst = next((i for i in insts if _n(i) == _n(p["instrumento"])), None) or \
            next((i for i in insts if _n(p["instrumento"])[:6] in _n(i)), p["instrumento"])
        paneles = _nombres(iol.paneles_disponibles(inst))
        pan = next((x for x in paneles if _n(x) == _n(p["panel"])), None) or \
            next((x for x in paneles if _n(p["panel"]) in _n(x)), paneles[0] if paneles else p["panel"])
        mapeo[f"{p['instrumento']}|{p['panel']}"] = [inst, pan]
        _anotar("notice", f"{p['grupo']}: instrumento={inst} paneles={json.dumps(paneles, ensure_ascii=False)[:600]}")
        print(f"  {p['grupo']:10s} → instrumento={inst!r} panel={pan!r}  (disponibles: {paneles[:12]})")
    a.put("iol/paneles", mapeo)
    _anotar("notice", "Paneles: " + "; ".join(f"{k} -> {v[0]}/{v[1]}" for k, v in mapeo.items()))
    inst, pan = mapeo[f"{config()['iol']['paneles'][0]['instrumento']}|{config()['iol']['paneles'][0]['panel']}"]
    muestra = iol.panel(inst, pan)
    print(f"\nPanel de muestra {inst}/{pan}: {len(muestra)} títulos")
    print(json.dumps(muestra[:2], ensure_ascii=False, indent=1))
    cot = iol.cotizacion("GGAL")
    print("\nGGAL con puntas:", json.dumps({k: cot[k] for k in ("ultimo", "compra", "venta", "variacion", "monto")}, ensure_ascii=False))
    c.guardar()
    print("\nConsumo IOL:", c.resumen())
    _anotar("notice", f"OK. Muestra {len(muestra)} titulos. GGAL ultimo={cot.get('ultimo')} compra={cot.get('compra')} "
                      f"venta={cot.get('venta')}. Consumo IOL: {c.resumen()['total']}")


def _anotar(tipo: str, texto: str) -> None:
    """Deja el resultado como anotación de GitHub (visible en el resumen de la ejecución)."""
    print(f"::{tipo}::" + texto.replace("%", "%25").replace("\r", "").replace("\n", "%0A")[:3000])


if __name__ == "__main__":
    import traceback
    try:
        main()
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)[-1]
        _anotar("error", f"{type(e).__name__}: {e} (en {tb.filename.split('/')[-1]}:{tb.lineno})")
        raise
