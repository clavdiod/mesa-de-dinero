"""Pone en la app los aprendizajes y el Cazador de ganadores sin esperar a la próxima ronda."""
import yaml

from mesa.nucleo.almacen import almacen_por_defecto
from mesa.nucleo.config import RAIZ

a = almacen_por_defecto()
est = a.get("ui/estado") or {}
est["aprendizajes"] = yaml.safe_load((RAIZ / "config" / "aprendizajes.yaml").read_text(encoding="utf-8")) or []
lg, pg = a.get("ganadores/lista") or {}, a.get("ganadores/prueba") or {}
est["ganadores"] = {"fecha": lg.get("fecha"), "lista": lg.get("lista") or [], "base": pg.get("base"),
                    "prueba": {k: {"nombre": v["nombre"], "activa": v["activa"], "plazo": v["plazo"],
                                   **((v.get("horizontes") or {}).get(str(v["plazo"])) or {})} for k, v in (pg.get("estrategias") or {}).items()}}
a.put("ui/estado", est)
print(f"::notice::aprendizajes {len(est['aprendizajes'])} · ganadores {len(est['ganadores']['lista'])} · activas {[k for k, v in est['ganadores']['prueba'].items() if v['activa']]}")
