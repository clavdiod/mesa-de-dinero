"""16/11: estructura del JSON del tablero BYMA Educa."""
import re, json
from mesa.datos.gratis import _S
html = _S.get("https://tablero.bymaeduca.com.ar", headers={"User-Agent": "Mozilla/5.0"}, timeout=60).text
scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S)
out = []
for s in sorted(scripts, key=len, reverse=True)[:4]:
    s2 = s.strip()
    try:
        d = json.loads(s2)
    except Exception:
        m = re.search(r"=\s*(\{.*\})\s*;?\s*$", s2, re.S)
        try:
            d = json.loads(m.group(1)) if m else None
        except Exception:
            d = None
    if not isinstance(d, dict):
        out.append(f"script {len(s2)} no es JSON: {s2[:120]!r}"); continue
    for k, v in d.items():
        if isinstance(v, dict):
            sub = {kk: (f"lista {len(vv)}" if isinstance(vv, list) else type(vv).__name__) for kk, vv in v.items()}
            filas = v.get("rows") or []
            ej = filas[0] if filas and isinstance(filas[0], dict) else None
            out.append(f"[{k}] {sub} · campos fila: {list(ej.keys())[:60] if ej else ''}")
            for kk, vv in v.items():
                if isinstance(vv, list) and vv and isinstance(vv[0], (list, dict)) and kk != "rows":
                    out.append(f"   {k}.{kk}[0] = {json.dumps(vv[0], ensure_ascii=False)[:300]}")
            if ej:
                for kk, vv in ej.items():
                    if isinstance(vv, list) and vv:
                        out.append(f"   fila.{kk} = lista de {len(vv)}: {json.dumps(vv[:3], ensure_ascii=False)[:250]}")
        elif isinstance(v, list):
            out.append(f"[{k}] lista {len(v)}: {json.dumps(v[0], ensure_ascii=False)[:300] if v else ''}")
        else:
            out.append(f"[{k}] = {str(v)[:120]}")
[print("EDU| " + o) for o in out]
