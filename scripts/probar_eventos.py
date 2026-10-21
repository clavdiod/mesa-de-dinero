"""Prueba la fuente de balances/dividendos de EE.UU. (Nasdaq) y guarda el resultado del día. No imprime secretos."""
from datetime import date, timedelta, datetime, timezone

from mesa.datos import eventos
from mesa.nucleo.almacen import almacen_por_defecto

hoy = (datetime.now(timezone.utc) - timedelta(hours=3)).date()
a = almacen_por_defecto()
panel = a.get("ui/panel") or {}
simb = {tk for tk, x in (panel.get("titulos") or {}).items() if x[4] == "cedears"}
cedears = {s for s in simb if not (s[-1:] in ("D", "C") and s[:-1] in simb)}
ev = eventos.eeuu(cedears, hoy, 21)
a.put("eventos/eeuu", {"fecha": hoy.isoformat(), "eventos": ev})
bal = [e for e in ev if e["tipo"] == "balance"]
div = [e for e in ev if e["tipo"] == "dividendo"]
print(f"::notice::CEDEARs={len(cedears)} balances={len(bal)} dividendos={len(div)} ejemplos: " +
      " | ".join(f"{e['fecha']} {e['ticker']} {e['nombre'][:60]}" for e in (bal[:5] + div[:3])))
