from mesa.datos.gratis import _S
for u in ("https://tablero.bymaeduca.com.ar/robots.txt", "https://www.bymaeduca.com.ar/robots.txt"):
    try:
        r = _S.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        print(f"EDU| {u} {r.status_code}: {r.text[:800]!r}")
    except Exception as ex:
        print(f"EDU| {u} ERR {ex}")
