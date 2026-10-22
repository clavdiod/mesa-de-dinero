"""Noticias de papeles puntuales, como las ve el debate."""
from mesa.agentes import mundo

out = []
for tk, local in (("IREN", False), ("SATL", False), ("RIOT", False), ("LOMA", True)):
    nombre = {"LOMA": "Loma Negra"}.get(tk) or mundo.nombre_yahoo(tk)
    info = mundo.noticias_papel(tk, nombre, local)
    s = mundo.senal_papel(tk, info)
    out.append(f"{tk} [{nombre}] {len(info['titulares'])} tit. -> dir {s.direccion} f {s.fuerza}: {s.texto[:300]}")
print("::notice::" + " ||| ".join(out)[:3900])
