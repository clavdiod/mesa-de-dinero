"""24/11: ¿qué le pasó hoy a Noche de Nueva York (ADRs)? Solo lectura; imprime datos de mercado, nada de la cartera."""
import json
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
est = a.get("ui/estado") or {}
e = est.get("estado") or est
adr = e.get("adr")
print(f"::notice::ui/estado fecha={est.get('fecha') or e.get('fecha')} hora={est.get('hora') or e.get('hora')} adr={'sí' if adr else 'NO'}")
if adr:
    print("::notice::adr hora=" + str(adr.get("hora")) + " filas=" + json.dumps(adr.get("filas"), ensure_ascii=False)[:1500])
    print("::notice::adr vivo=" + json.dumps(adr.get("vivo"), ensure_ascii=False)[:1000])
d = a.get("adr/datos") or {}
print(f"::notice::adr/datos fecha={d.get('fecha')} adrs={len(d.get('adrs') or {})}")
for k in ("GGAL", "TGS", "YPF", "PAM"):
    s = (d.get("adrs") or {}).get(k) or []
    print(f"::notice::{k} ultimas={s[-4:]}")
ccl = ((a.get("macro/series") or {}).get("series") or {}).get("ccl") or {}
print("::notice::ccl ultimas=" + json.dumps(sorted(ccl.items())[-4:]))
vig = (est.get("vigia") or e.get("vigia") or {}).get("agentes", {}).get("adr")
print("::notice::vigia adr=" + json.dumps(vig))
fotos = a.get("adr/fotos/2026-11-24") or []
print(f"::notice::fotos hoy={len(fotos)} horas={[f.get('hora') for f in fotos][:5]}...{[f.get('hora') for f in fotos][-3:]}")
