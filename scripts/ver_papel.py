"""Todo lo que la mesa sabe hoy de un papel (TK fijo abajo)."""
import json, traceback
from mesa.nucleo.almacen import almacen_por_defecto
TK = "CEPU"
a = almacen_por_defecto()
try:
    e = a.get("ui/estado") or {}
    print(f"::notice::ronda {e.get('fecha')} {e.get('hora')}")
    fuentes = {"anticipador": e.get("anticipo_lista") or {}, **(e.get("anticipo_listas") or {}), **(e.get("anticipo_listas_obs") or {})}
    for k in ("ganadores/lista", "profesionales/lista"):
        fuentes[k] = a.get(k) or {}
    for ag, l in fuentes.items():
        for x in (l.get("lista") or []):
            if isinstance(x, dict) and x.get("ticker") == TK:
                print(f"::notice::LISTA {ag} ({l.get('fecha')}): " + json.dumps(x, ensure_ascii=False)[:700])
    acta = [c for c in ((e.get("comite") or {}).get("acta") or []) if c.get("ticker") == TK]
    print("::notice::COMITE " + json.dumps(acta, ensure_ascii=False)[:900])
    d = (a.get("ui/debates") or {}).get(TK) or {}
    sup = d.get("supervisor") or {}
    print(f"::notice::DEBATE {d.get('fecha')} {d.get('hora')} {sup.get('veredicto')} | {sup.get('titulo')} | " + " / ".join(sup.get("detalle") or [])[:600] + f" | plan {json.dumps(d.get('plan'))}")
    for lado in ("favor", "contra"):
        print(f"::notice::{lado.upper()} " + " || ".join(f"{s.get('agente')} ({s.get('fuerza')}): {s.get('texto')}" for s in (d.get(lado) or []))[:1500])
    ev = [x for x in (e.get("eventos") or []) if x.get("ticker") in (TK, TK + "D")]
    pron = [{k: x.get(k) for k in ("origen", "estado", "fecha", "ref", "objetivo_pct", "mejor", "ahora_pct")} for x in (a.get("pronosticos/libreta") or []) if x.get("ticker") == TK][-6:]
    co = (a.get("profesionales/consensos") or {}).get(TK)
    print("::notice::OTROS " + json.dumps({"eventos": ev, "pron": pron, "consenso": co, "anticipos": [x for x in (e.get("anticipos") or []) if x.get("ticker") == TK]}, ensure_ascii=False)[:1500])
except Exception:
    print("::notice::ERR " + traceback.format_exc().replace(chr(10), " | ")[-700:])
