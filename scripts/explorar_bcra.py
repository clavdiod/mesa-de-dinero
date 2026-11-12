from mesa.datos.gratis import _S
vs = []
for off in (0, 1000):
    r = _S.get(f"https://api.bcra.gob.ar/estadisticas/v4.0/monetarias?offset={off}&limit=1000", timeout=30, verify=False)
    vs += r.json().get("results") or []
k = ("3500", "TAMAR", "BADLAR", "CER", "plazo fijo", "Plazo fijo", "anda", "UVA", "nflaci", "Reservas", "Base monetaria")
print("::notice::" + " | ".join(f"{v['idVariable']}:{v['descripcion'][:60]}={v.get('ultValorInformado')}({v.get('ultFechaInformada')})" for v in vs if any(x in v["descripcion"] for x in k))[:7000])
