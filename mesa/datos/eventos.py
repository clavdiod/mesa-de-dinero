"""Calendario de eventos: cobros de bonos y ONs, balances y dividendos (CEDEARs), fechas macro.

Fuentes, todas gratis y sin gastar el cupo de IOL:
- config/eventos.yaml: fechas macro verificadas (Reserva Federal, INDEC, etc.).
- config/bonos_flujos.yaml: flujos de los soberanos en dólares (bajados una vez de IOL).
- usuario/ons (KV): flujos de ONs cargados por el usuario en la web.
- Nasdaq (calendario público de balances y dividendos de EE.UU.): para los CEDEARs. Se baja una vez
  por día en el cierre y queda guardado en eventos/eeuu.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

import yaml

from ..nucleo.config import RAIZ
from ..nucleo.http import sesion

_UA = {"User-Agent": "Mozilla/5.0 (mesa-de-dinero, uso personal)", "Accept": "application/json"}


def _yaml(nombre: str, defecto):
    try:
        return yaml.safe_load((RAIZ / "config" / nombre).read_text(encoding="utf-8")) or defecto
    except FileNotFoundError:
        return defecto


def flujos_bonos() -> dict[str, dict]:
    """ticker -> {emisor, moneda, flujos}. Incluye los Bonares (AL) y las variantes D/C de cada bono."""
    doc = _yaml("bonos_flujos.yaml", {})
    bonos = dict(doc.get("bonos") or {})
    for al, gd in (doc.get("equivalentes") or {}).items():
        if gd in bonos:
            bonos[al] = bonos[gd]
    for tk in list(bonos):
        bonos.setdefault(tk + "D", bonos[tk])
        bonos.setdefault(tk + "C", bonos[tk])
    return bonos


def _habil(d: date) -> date:
    """Si el pago cae fin de semana, se cobra el lunes (los feriados se ignoran: aproximado)."""
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def cobros(desde: date, dias: int, ons_usuario: dict, interes: set[str] | None = None) -> list[dict]:
    """Pagos de bonos/ONs en los próximos `dias`. Si `interes` viene, solo esos tickers (base, sin D/C)."""
    hasta = desde + timedelta(days=dias)
    fuentes = {**{k: v for k, v in flujos_bonos().items() if not re.search(r"[DC]$", k)}, **(ons_usuario or {})}
    out = []
    if interes is not None:  # un solo aviso general para los soberanos (pagan todos el mismo día)
        fechas = {_habil(date.fromisoformat(str(f["fecha"]))) for b in ("GD30", "GD35", "GD38") for f in fuentes.get(b, {}).get("flujos", [])}
        for d in sorted(x for x in fechas if desde <= x <= hasta):
            out.append({"fecha": d.isoformat(), "tipo": "cobro", "ticker": "AL/GD", "fuerte": False,
                        "nombre": "Pagan los bonos soberanos en dólares (Globales GD y Bonares AL)"})
    for tk, on in fuentes.items():
        if interes is not None and tk not in interes:
            continue
        for f in on.get("flujos", []):
            fd = date.fromisoformat(str(f["fecha"]))
            pago = _habil(fd)
            if desde <= pago <= hasta:
                i, a = float(f.get("interes", 0)), float(f.get("amortizacion", 0))
                partes = ([f"renta {i:g}%"] if i else []) + ([f"amortización {a:g}%"] if a else [])
                out.append({"fecha": pago.isoformat(), "tipo": "cobro", "ticker": tk, "fuerte": False,
                            "nombre": f"Paga {' + '.join(partes)} (cada 100 nominales originales)",
                            "monto_c100": round(i + a, 4)})
    return out


def eeuu(tickers: set[str], desde: date, dias: int = 21) -> list[dict]:
    """Balances y dividendos de empresas de EE.UU. (para CEDEARs) desde el calendario público de Nasdaq."""
    s, out = sesion(2), []
    for k in range(dias + 1):
        d = desde + timedelta(days=k)
        if d.weekday() >= 5:
            continue
        for tipo, url in (("balance", "earnings"), ("dividendo", "dividends")):
            try:
                r = s.get(f"https://api.nasdaq.com/api/calendar/{url}?date={d.isoformat()}", headers=_UA, timeout=20)
                datos = (r.json().get("data") or {}) if r.ok else {}
            except Exception:
                continue
            filas = (datos.get("rows") or (datos.get("calendar") or {}).get("rows") or [])
            for f in filas:
                sym = str(f.get("symbol") or "").upper().replace(".", "")
                if sym not in tickers:
                    continue
                if tipo == "balance":
                    cuando = {"time-pre-market": "antes de la apertura de EE.UU.", "time-after-hours": "después del cierre de EE.UU."}.get(
                        f.get("time"), "")
                    out.append({"fecha": d.isoformat(), "tipo": "balance", "ticker": sym, "fuerte": False,
                                "nombre": f"Balance de {f.get('name') or sym} {cuando}".strip()})
                else:
                    monto = f.get("dividend_Rate") or f.get("dividendRate") or ""
                    out.append({"fecha": d.isoformat(), "tipo": "dividendo", "ticker": sym, "fuerte": False,
                                "nombre": f"Corte de dividendo de {f.get('companyName') or sym} (US$ {monto} por acción)",
                                "pago": f.get("payment_Date") or f.get("paymentDate")})
    return out


def armar(almacen, hoy: date, dias: int = 45, interes: set[str] | None = None) -> list[dict]:
    """Calendario combinado de los próximos `dias` (sin consultas externas: usa lo guardado)."""
    hasta = (hoy + timedelta(days=dias)).isoformat()
    macro = [{**e, "tipo": e.get("tipo", "macro")} for e in _yaml("eventos.yaml", [])
             if hoy.isoformat() <= str(e.get("fecha")) <= hasta]
    ev = macro + cobros(hoy, dias, almacen.get("usuario/ons") or {}, interes)
    ev += [e for e in (almacen.get("eventos/eeuu") or {}).get("eventos", [])
           if hoy.isoformat() <= e["fecha"] <= hasta and (interes is None or e["ticker"] in interes)]
    lic_todo = almacen.get("eventos/licitaciones") or []
    lic = lic_todo.get("eventos", []) if isinstance(lic_todo, dict) else lic_todo
    ev += [{**e, "mio": True} for e in lic if hoy.isoformat() <= e.get("fecha", "") <= hasta]
    # avisos de pago de ONs/bonos publicados en MAE: "mío" si el emisor es de mi cartera, lista u ONs cargadas
    pagos_mae = lic_todo.get("pagos") if isinstance(lic_todo, dict) else None
    if pagos_mae:
        from ..agentes.mae import coincide_emisor
        from ..nucleo.config import nombre_emisor
        nombres = [n for n in {nombre_emisor(t) for t in (interes or set())} if n]
        for e in pagos_mae:
            if hoy.isoformat() <= e["fecha"] <= hasta:
                ev.append({**e, "mio": coincide_emisor(e.get("empresa") or "", nombres)})
    ev.sort(key=lambda e: (e["fecha"], e.get("tipo", "")))
    return ev


def actualizar_licitaciones(almacen, hoy: date, hora: str = "", forzar: bool = False) -> dict:
    """Licitaciones del MAE (gratis). Se piden a la mañana y se refrescan una vez a la tarde
    (a veces se publican el mismo día). Se guardan solo si cambiaron."""
    from . import gratis
    guardado = almacen.get("eventos/licitaciones") or {}
    if isinstance(guardado, list):
        guardado = {}
    tarde = hora >= "13:00"
    if not forzar and guardado.get("fecha") == hoy.isoformat() and (not tarde or guardado.get("tarde")):
        return guardado
    try:
        evs = gratis.licitaciones_mae(hoy - timedelta(days=1), hoy + timedelta(days=45))
    except Exception as ex:
        print(f"[licitaciones] {ex}")
        return guardado
    # no todas las ONs se licitan en el sistema del MAE: se suman los titulares de las últimas 48 h
    noticias = []
    try:
        import re
        fuera = re.compile(r"calificaci|ratifica|app\b", re.I)
        vistos = set()
        for q in ("obligaciones negociables", "nueva ON dólares empresa", "ON licita tasa clase", "emisión de deuda corporativa ON"):
            for n in gratis.buscar_noticias(q, horas=120, max_items=10):
                t = n["titulo"]
                clave = t[:50].lower()
                es_on = re.search(r"\bONs?\b", t) or "negociable" in t.lower()
                if clave in vistos or not es_on or fuera.search(t):
                    continue
                vistos.add(clave)
                noticias.append({"titulo": t, "link": n.get("link"), "fecha": n.get("fecha")})
    except Exception as ex:
        print(f"[licitaciones] noticias: {ex}")
    avisos, pagos = {}, []
    try:
        from ..agentes import mae as _mae
        avisos = _mae.avisos_licitacion(gratis.mae_documentos("boletin-mpmae"), hoy)
        pagos = _mae.pagos(gratis.mae_documentos("pagoamortizrenta"), hoy, [])
    except Exception as ex:
        print(f"[licitaciones] avisos MAE: {ex}")
    nuevo = {"fecha": hoy.isoformat(), "hora": hora, "tarde": tarde, "fuente": "MAE / A3 Mercados", "eventos": evs,
             "noticias": noticias[:8], "avisos": avisos, "pagos": pagos}
    almacen.put("eventos/licitaciones", nuevo)
    return nuevo
