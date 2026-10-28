"""Las alertas de lo que tenés pasan a vivir en tu cartera; se borran de Mi lista los favoritos que creó la mesa."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
cart = a.get("usuario/cartera") or []
lista = a.get("usuario/lista") or []
en_cart = {str(c.get("ticker", "")).upper(): c for c in cart}
nueva = []
for it in lista:
    tk = str(it.get("ticker", "")).upper()
    c = en_cart.get(tk)
    if c and it.get("alertas"):
        ids = {x.get("id") for x in c.get("alertas") or []}
        c.setdefault("alertas", []).extend(x for x in it["alertas"] if x.get("id") not in ids)
        it["alertas"] = []
    creado_por_mesa = str(it.get("nota") or "").startswith("Compra")
    if c and creado_por_mesa:
        continue  # lo había creado la mesa para colgar las alertas: afuera de Mi lista
    nueva.append(it)
a.put("usuario/cartera", cart)
a.put("usuario/lista", nueva)
print("::notice::MI LISTA: " + ", ".join(f"{x['ticker']} ({x.get('nota') or ''})" for x in nueva))
print("::notice::CARTERA con alertas: " + json.dumps({c["ticker"]: [(x["tipo"], x["nivel"]) for x in c.get("alertas") or []] for c in cart if c.get("alertas")}))
