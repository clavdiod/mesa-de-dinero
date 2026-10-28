"""Todo lo que dice la mesa de un papel ahora: debate, cada analista, proyección, anticipos y noticias."""
import json, os
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
tk = os.environ.get("TK", "ETSY")
est = a.get("ui/estado") or {}
d = (a.get("ui/debates") or {}).get(tk) or {}
sup = d.get("supervisor") or {}
print(f"::notice::{est.get('hora')} SUP {sup.get('veredicto')} | {sup.get('titulo')} | " + " / ".join(sup.get("detalle") or []) + f" | precio {json.dumps(d.get('precio'))} | plan {json.dumps(d.get('plan'))} | debate {d.get('fecha')} {d.get('hora')}")
for lado in ("favor", "contra", "neutral"):
    print(f"::notice::{lado.upper()} " + " || ".join(f"{s.get('agente')} ({s.get('fuerza')}): {s.get('texto')}" for s in (d.get(lado) or []))[:3000])
db = d.get("debate") or {}
print("::notice::DEBATE alcista: " + str(db.get("alcista"))[:900] + " || bajista: " + str(db.get("bajista"))[:900])
print("::notice::PROY " + json.dumps((est.get("proyeccion_cartera") or {}).get(tk), ensure_ascii=False)[:1200])
mu = est.get("mundo") or {}
print("::notice::NOTICIAS " + json.dumps([e for e in (mu.get("empresas") or []) if e.get("ticker") == tk], ensure_ascii=False)[:1500]
      + " PAPEL " + json.dumps(((a.get("mundo/papeles") or {}).get("papeles") or {}).get(tk), ensure_ascii=False)[:1500])
print("::notice::ANT " + json.dumps([x for x in (est.get("anticipos") or []) if x["ticker"] == tk]) + " PRON " + json.dumps([{k: x.get(k) for k in ("origen", "estado", "fecha", "ref", "mejor", "ahora_pct", "objetivo_pct")} for x in (est.get("pronosticos") or []) if x["ticker"] == tk][:6]))
