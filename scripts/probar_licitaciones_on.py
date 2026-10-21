"""Prueba qué titulares aparecen sobre licitaciones de ONs en las noticias (Google News, gratis)."""
from mesa.datos import gratis

vistos, out = set(), []
for q in ('obligaciones negociables licitación', '"licita" ON clase', '"aviso de suscripción" obligaciones negociables',
          'colocación obligaciones negociables hoy', 'emisión de ON dólares licitará'):
    for n in gratis.buscar_noticias(q, horas=96, max_items=15):
        if n["titulo"] not in vistos:
            vistos.add(n["titulo"])
            out.append(f"{n.get('fecha', '')[:16]} {n['titulo'][:140]}")
print("::notice::" + str(len(out)) + " titulares | " + " || ".join(out[:30])[:3900])
