"""Lectura real del Corresponsal (sin guardar nada)."""
from collections import Counter

from mesa.agentes import mundo
from mesa.nucleo.config import emisores

tit = mundo.leer()
fu = Counter(n["fuente"] for n in tit)
temas = mundo.detectar_temas(tit)
emp = mundo.detectar_empresas(tit, mundo.claves_empresas(emisores()))
print("::notice::" + f"{len(tit)} titulares de {len(fu)} fuentes: " + ", ".join(f"{k} {v}" for k, v in fu.most_common(25)))
print("::notice::TEMAS || " + " || ".join(f"{t['nombre']} ({t['n']}): " + " | ".join(x["titulo"][:90] for x in t["titulares"][:3]) for t in temas)[:3900])
print("::notice::EMPRESAS || " + " || ".join(f"{e['ticker']} {'+' if e['dir'] > 0 else '-'}{' rumor' if e['rumor'] else ''}: {e['titulares'][0]['titulo'][:100]} [{e['titulares'][0]['motivo']}]" for e in emp)[:3900])
