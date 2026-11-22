"""22/11: SH y SHW salieron con los mismos votos y puntaje en el Comité. ¿Se mezclan o es casualidad?
Ronda con los datos del último cierre, SIN escribir ni avisar; muestra cada señal de los dos papeles."""
from mesa.nucleo import almacen as _alm, push
import mesa.ronda as R
from mesa.agentes import comite

base = _alm.almacen_por_defecto()


class SoloLectura:
    def __init__(self, b):
        self.b, self.mem = b, {}

    def get(self, k, d=None):
        return self.mem[k] if k in self.mem else self.b.get(k, d)

    def put(self, k, v):
        self.mem[k] = v

    def __getattr__(self, n):
        return getattr(self.b, n)


push.avisar = lambda *a, **k: {"enviadas": 0, "vencidas": []}
push.enviar = lambda *a, **k: {"enviadas": 0, "vencidas": []}
a = SoloLectura(base)
R.almacen_por_defecto = lambda: a
vistos = {}
orig_votar = comite.votar


def votar(e, pesos):
    if e.get("ticker") in ("SH", "SHW"):
        vistos[e["ticker"]] = (e, pesos)
    return orig_votar(e, pesos)


comite.votar = votar
R.correr(forzar=True)
for tk, (e, pesos) in vistos.items():
    print(f"::notice::{tk}: grupo {e.get('grupo')} · puntaje {e.get('puntaje')} · plan {e.get('plan', {}).get('entrada')}/{e.get('plan', {}).get('stop')} · {len(e.get('senales') or [])} señales")
    for s in e.get("senales") or []:
        print(f"::notice::{tk} ← {s.get('agente')} [{s.get('ticker')}] dir {s.get('direccion')} fuerza {s.get('fuerza')} peso {((pesos.get(s.get('agente')) or {}).get('peso'))} · {str(s.get('texto'))[:110]}")
