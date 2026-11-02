"""Saca de la campanita los avisos de hoy que no son tuyos (posiciones en papel como VIST y radar del resto del mercado)."""
from mesa.nucleo.almacen import almacen_por_defecto
a = almacen_por_defecto()
tuyos = {str(c.get("ticker", "")).upper() for c in (a.get("usuario/cartera") or [])} | {str((x.get("ticker") if isinstance(x, dict) else x) or "").upper() for x in (a.get("usuario/lista") or [])}
al = a.get("ui/alertas") or []
def mio(x):
    t = str(x.get("ticker", "")).split(" ")[0].replace("📡", "").strip().upper()
    return t in tuyos or t[:-1] in tuyos or t in ("AL/GD",) or "cobr" in str(x.get("texto", "")).lower() or "Comité" in str(x.get("texto", ""))
n = [x for x in al if x.get("fecha") != "2026-11-02" or mio(x)]
a.put("ui/alertas", n)
print(f"::notice::quitados {len(al) - len(n)} avisos ajenos de hoy; quedan {len(n)}")
