"""Libreta de pronósticos: cada cosa que la mesa anticipa queda anotada y se controla sola.

Por cada pronóstico se guarda: qué dijo (sube/baja, cuánto y en cuánto tiempo), el precio de ese momento,
y en cada ronda se mide el mejor y el peor precio que tuvo después. Estados:
  esperando  -> todavía no hay precio de BYMA para tomar de referencia (ej. lista hecha al cierre)
  en_curso   -> corriendo el plazo
  se_dio     -> llegó al objetivo dentro del plazo
  fallo      -> fue en contra hasta el stop antes de llegar al objetivo
  no_se_dio  -> venció el plazo sin llegar
"""
from __future__ import annotations

from datetime import date, timedelta

ORIGENES = {"anticipador": "Anticipador (días antes)", "anticipador_arg": "Anticipador ARG", "anticipador_mundo": "Anticipador Mundo", "anticipo": "Anticipo Nueva York (horas antes)",
            "mundo": "Corresponsal (noticias)", "ganadores": "Cazador de ganadores", "profesionales": "Herramientas de Wall Street", "jefe": "Comité", "oportunidad": "Oportunidad confirmada"}
MAX = 600


def _vence(desde: date, dias_corridos: int) -> str:
    return (desde + timedelta(days=dias_corridos)).isoformat()


def anotar(libreta: list[dict], p: dict) -> bool:
    """p: {origen, ticker, dir, objetivo_pct, stop_pct?, vence, fecha, hora, texto, ref?}. No duplica."""
    pid = f"{p['origen']}|{p['ticker']}|{p.get('clave') or p['fecha']}"
    if any(x["id"] == pid for x in libreta):
        return False
    libreta.insert(0, {"id": pid, "estado": "esperando" if not p.get("ref") else "en_curso", "mejor": 0.0, "peor": 0.0,
                       "ahora_pct": 0.0, **{k: v for k, v in p.items() if k != "clave"}})
    del libreta[MAX:]
    return True


def actualizar(libreta: list[dict], precios: dict[str, dict], hoy: date, byma_abierto: bool) -> bool:
    """Mide cada pronóstico abierto con el panel de la ronda. Devuelve si algún estado cambió."""
    cambio = False
    h = hoy.isoformat()
    for x in libreta:
        if x["estado"] not in ("esperando", "en_curso"):
            continue
        t = precios.get(x["ticker"]) or {}
        ult = t.get("ultimo")
        if x["estado"] == "esperando":
            if h > x["vence"]:
                x["estado"], cambio = "no_se_dio", True
            elif ult and byma_abierto:
                # lista hecha al cierre: se toma la apertura del día siguiente (lo primero que se podía comprar)
                ref = (t.get("apertura") or ult) if x.get("origen") == "anticipador" else ult
                x.update(ref=ref, estado="en_curso", fecha_ref=h)
                cambio = True
            continue
        if not ult:
            continue
        d, ref = x["dir"], x["ref"]
        hi, lo = t.get("maximo") or ult, t.get("minimo") or ult
        if h == x.get("fecha_ref", x["fecha"]):  # el máximo/mínimo del día pudo ser antes del pronóstico
            hi = lo = ult
        favor = ((hi if d > 0 else lo) / ref - 1) * 100 * d
        contra = ((lo if d > 0 else hi) / ref - 1) * 100 * d
        x["ultimo"] = ult
        x["ahora_pct"] = round((ult / ref - 1) * 100 * d, 2)
        x["mejor"] = round(max(x["mejor"], favor), 2)
        x["peor"] = round(min(x["peor"], contra), 2)
        if x.get("stop_pct") and x["peor"] <= -x["stop_pct"] and x["mejor"] < x["objetivo_pct"]:
            x.update(estado="fallo", fecha_cierre=h)
            cambio = True
        elif x["mejor"] >= x["objetivo_pct"]:
            x.update(estado="se_dio", fecha_cierre=h)
            cambio = True
        elif h > x["vence"]:
            x.update(estado="no_se_dio", fecha_cierre=h)
            cambio = True
    return cambio


def cerrar_dia(libreta: list[dict], hoy: date) -> bool:
    """Al final del día, los pronósticos que vencían hoy (ej. anticipos de horas) y no se dieron, se cierran."""
    cambio = False
    for x in libreta:
        if x["estado"] in ("esperando", "en_curso") and x["vence"] <= hoy.isoformat() and x.get("cierra_en_el_dia"):
            x.update(estado="no_se_dio", fecha_cierre=hoy.isoformat())
            cambio = True
    return cambio


def resumen(libreta: list[dict]) -> dict:
    out = {}
    for x in libreta:
        r = out.setdefault(x["origen"], {"nombre": ORIGENES.get(x["origen"], x["origen"]), "se_dio": 0, "fallo": 0, "no_se_dio": 0,
                                         "en_curso": 0, "esperando": 0, "suma_final": 0.0, "cerrados": 0})
        r[x["estado"]] += 1
        if x["estado"] in ("se_dio", "fallo", "no_se_dio"):
            r["cerrados"] += 1
            r["suma_final"] = round(r["suma_final"] + (x["objetivo_pct"] if x["estado"] == "se_dio" else
                                                         -x["stop_pct"] if x["estado"] == "fallo" else x.get("ahora_pct", 0)), 2)
    for r in out.values():
        r["acierto_pct"] = round(r["se_dio"] / r["cerrados"] * 100, 1) if r["cerrados"] else None
        r["promedio_pct"] = round(r["suma_final"] / r["cerrados"], 2) if r["cerrados"] else None
    return out


# ---------- de cada fuente de la mesa a la libreta ----------
def desde_anticipador(lista: dict, hoy: date, hora: str, origen: str = "anticipador") -> list[dict]:
    if not lista.get("lista"):
        return []
    f = lista.get("fecha") or hoy.isoformat()
    base = date.fromisoformat(f)
    h, m = int(lista.get("horizonte") or 5), float(lista.get("meta") or 5.0)
    plazo_txt = "en la semana" if h <= 5 else f"en {h} ruedas"
    return [{"origen": origen, "ticker": x["ticker"], "dir": 1, "objetivo_pct": m, "vence": _vence(base, h * 7 // 5 + 1),
             "fecha": f, "hora": hora, "clave": f, "prob": x.get("prob"),
             "texto": f"Sube {m:.0f}% o más {plazo_txt} ({x.get('prob', 0) * 100:.0f}% de probabilidad). " + ", ".join(x.get("razones") or [])}
            for x in lista["lista"][:10]]


def desde_anticipos(atrasos: list[dict], hoy: date, hora: str) -> list[dict]:
    out = []
    for a in atrasos:
        if abs(a["atraso"]) < 2:
            continue
        d = 1 if a["atraso"] > 0 else -1
        out.append({"origen": "anticipo", "ticker": a["ticker"], "dir": d, "objetivo_pct": round(max(1.0, abs(a["atraso"]) / 2), 2),
                    "vence": hoy.isoformat(), "cierra_en_el_dia": True, "fecha": hoy.isoformat(), "hora": hora,
                    "ref": None if a.get("antes_de_abrir") else a.get("precio_cedear"),
                    "texto": f"En Nueva York va {a['us']:+.1f}%: el CEDEAR debería {'subir' if d > 0 else 'bajar'} {abs(a['atraso']):.1f}% (se da si recorre la mitad en el día)."})
    return out


def desde_mundo(sens, hoy: date, hora: str, precio) -> list[dict]:
    return [{"origen": "mundo", "ticker": s.ticker, "dir": s.direccion, "objetivo_pct": 2.0, "stop_pct": 3.0, "vence": _vence(hoy, 7),
             "fecha": hoy.isoformat(), "hora": hora, "ref": precio(s.ticker), "texto": s.texto[:240]}
            for s in sens if s.fuerza >= 0.35]


def desde_plan(origen: str, ticker: str, plan: dict, hoy: date, hora: str, texto: str, clave: str | None = None) -> dict | None:
    e, o, st = plan.get("entrada"), plan.get("objetivo"), plan.get("stop")
    if not (e and o and st) or o <= e:
        return None
    return {"origen": origen, "ticker": ticker, "dir": 1, "objetivo_pct": round((o / e - 1) * 100, 2), "stop_pct": round((1 - st / e) * 100, 2),
            "vence": plan.get("vence") or _vence(hoy, 14), "fecha": hoy.isoformat(), "hora": hora, "ref": e, "clave": clave,
            "texto": texto[:240]}


def desde_ganadores(sens, hoy: date, hora: str, precio) -> list[dict]:
    """Ideas del Cazador de ganadores: objetivo +8% en su plazo (20 ruedas ≈ 4 semanas), stop -8%."""
    return [{"origen": s.agente, "ticker": s.ticker, "dir": 1, "objetivo_pct": 8.0, "stop_pct": 8.0,
             "vence": _vence(hoy, int((s.datos or {}).get("plazo") or 20) * 7 // 5), "fecha": hoy.isoformat(), "hora": hora,
             "ref": precio(s.ticker), "texto": s.texto[:240]} for s in sens if s.agente in ("ganadores", "profesionales") and not (s.datos or {}).get("confirmacion")]
