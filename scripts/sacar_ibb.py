"""24/11 (Clau: "no tengo más IBB"): saca IBB de la cartera que sigue la mesa. Mi lista no se toca.
El repo y los logs son públicos: solo imprime si IBB estaba o no, nada más de la cartera."""
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
es = lambda x: str((x.get("ticker") if isinstance(x, dict) else x) or "").upper() in ("IBB", "IBBD", "IBBC")
cart = a.get("usuario/cartera") or []
quedan = [x for x in cart if not es(x)]
if len(quedan) != len(cart):
    a.put("usuario/cartera", quedan)
    for k in ("usuario/decisiones_cartera", "cartera/avisados"):
        d = a.get(k) or {}
        if isinstance(d, dict) and d.pop("IBB", None) is not None:
            a.put(k, d)
lista = a.get("usuario/lista") or []
print(f"::notice::IBB estaba en la cartera: {'sí, sacado' if len(quedan) != len(cart) else 'no'} · está en Mi lista: {'sí' if any(es(x) for x in lista) else 'no'}")
