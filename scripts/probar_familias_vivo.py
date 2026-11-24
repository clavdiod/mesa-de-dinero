"""22/11 (Clau: "veamos cómo funciona"): ronda con los datos reales del último cierre, SIN escribir nada ni avisar.
Corre dos veces: sin familias (como antes) y con familias (como ahora), y compara puntajes, Comité y Vigía.
Todo lo que la ronda guarda queda en memoria; los avisos al celular están apagados. No imprime datos personales."""
import json
from mesa.nucleo import almacen as _alm, push, familias, vigia
import mesa.ronda as R

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
orig_pt, orig_fam = R.puntaje_ticker, familias.familia


def correr(nombre, sin_familias):
    a = SoloLectura(base)
    R.almacen_por_defecto = lambda: a
    pts, hablaron = {}, set()

    def pt(ss, reg, ctx=None):
        v = orig_pt(ss, reg, ctx)
        if ss:
            pts[ss[0].ticker] = v
            hablaron.update(x.agente for x in ss)
        return v
    R.puntaje_ticker = pt
    familias.familia = (lambda ag: ag) if sin_familias else orig_fam
    res = R.correr(forzar=True)
    est = a.mem.get("ui/estado") or {}
    acta = (est.get("comite") or {}).get("acta") or []
    print(f"::notice::[{nombre}] corrió={res.get('corrio', True)} · papeles con puntaje {len(pts)} · "
          f"con 0,6 o más (preselección) {sum(1 for v in pts.values() if v >= 0.6)} · al Comité {len(acta)} · "
          f"aprobadas {sum(1 for x in acta if x['aprobada'])}: {', '.join(x['ticker'] for x in acta if x['aprobada']) or 'ninguna'}")
    for x in acta[:10]:
        vs = " ".join(f"{'▲' if v['voto'] > 0 else '▼'}{v['nombre']}{' (repite ' + v['misma_familia'] + ')' if v.get('cuenta') is False else ''}" for v in x["votos"])
        print(f"::notice::[{nombre}] Comité {x['ticker']}: {'APRUEBA' if x['aprobada'] else 'no'} · favor {x['favor']} contra {x['contra']} · {x['motivo'] or 'ok'} · votos: {vs}")
    return pts, acta, a, hablaron


p0, a0, _, _h = correr("ANTES", True)
p1, a1, a, hab = correr("AHORA", False)
dif = sorted(((tk, p0.get(tk, 0), p1.get(tk, 0)) for tk in set(p0) | set(p1)), key=lambda x: -abs(x[1] - x[2]))
print("::notice::Puntajes que más cambiaron (antes → ahora): " + " | ".join(f"{tk} {x:+.2f}→{y:+.2f}" for tk, x, y in dif[:15] if abs(x - y) > 0.005))
cruzan = [tk for tk, x, y in dif if (x >= 0.6) != (y >= 0.6)]
print("::notice::Cruzan la línea de 0,6 (entran o salen de la preselección): " + (", ".join(f"{tk} ({'sale' if p0.get(tk,0) >= 0.6 else 'entra'})" for tk in cruzan) or "ninguno"))
# Vigía: en vivo solo corre entre 11:30 y 16:55. Acá se ve quién habló en esta ronda y se simula un agente que se calla.
from mesa.agentes.revision import nombre
print(f"::notice::Vigía: hablaron {len(hab)} agentes en esta ronda: " + ", ".join(sorted(nombre(x) for x in hab)))
ev, avisos = None, []
for i in range(20):
    ev, _ = vigia.actualizar(ev, hab, "2026-11-24", f"12:{i:02d}")
callado = "tecnico" if "tecnico" in hab else sorted(hab)[0]
for i in range(8):
    ev, av = vigia.actualizar(ev, hab - {callado}, "2026-11-24", f"14:{i * 5:02d}")
    avisos += [(f"14:{i * 5:02d}", x["texto"]) for x in av]
print("::notice::Vigía (simulado, si " + nombre(callado) + " se callara desde las 14:00): " + (" | ".join(f"{h} → {t}" for h, t in avisos) or "sin aviso"))
