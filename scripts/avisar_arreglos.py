"""22/11: aviso al celular de Clau (lo pidió: "cuando termines mandame la notificación por la app").
Lo anota arriba de los avisos (tipo informe, así la app lo muestra tal cual) y manda el push. No imprime datos personales."""
from mesa.nucleo import push
from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.reloj import ahora

TITULO = "🛠️ Mesa: arreglos listos para aprobar"
TEXTO = ("Los analistas que miran lo mismo (gráfico, noticias, macro) ahora cuentan una sola vez; el Jefe ve quién votó "
         "y cuánto acierta cada uno; y el Vigía te avisa si un agente se queda mudo. Están en el PR #2 de GitHub: "
         "cuando lo apruebes, la mesa los empieza a usar.")
a = almacen_por_defecto()
t = ahora()
al = a.get("ui/alertas") or []
a.put("ui/alertas", ([{"fecha": t.date().isoformat(), "hora": t.strftime("%H:%M"), "ticker": TITULO, "tipo": "informe", "texto": TEXTO}] + al)[:60])
r = push.avisar(a, TITULO, TEXTO, importante=True)
print(f"::notice::aviso enviado a {r.get('enviadas', 0)} celular(es); respaldo: {r.get('respaldo')}")
