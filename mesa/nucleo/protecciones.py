"""Protecciones automáticas (como las de freqtrade) y memoria por papel (como TradingAgents).

Protecciones: frenos fijos que el Jefe no puede discutir. Miran las propuestas del Jefe ya cerradas (aprobadas o no:
todas se siguen en papel).
- Racha de stops: 3 o más stops en las últimas 2 ruedas → ese día no se proponen compras nuevas.
- Mala semana: la suma de resultados (en R, con comisión) de los últimos 10 días corridos es -3R o peor → pausa.
- Penitencia: un papel cuyas 2 últimas propuestas terminaron perdiendo queda fuera 7 días desde la última.

Memoria por papel: cada idea cerrada sobre un papel (propuesta del Jefe o pronóstico) deja una línea con lo que pasó
y una lección corta; el debate del papel la muestra arriba ("la última vez con este papel...").
"""
from __future__ import annotations

from datetime import date, timedelta

CERRADAS = ("stop", "objetivo", "tiempo")
STOPS_RACHA, RUEDAS_RACHA = 3, 2
PEOR_R, DIAS_SEMANA = -3.0, 10
DIAS_PENITENCIA = 7
NOMBRE_ORIGEN = {"jefe": "Propuesta del Jefe", "anticipador": "Anticipador", "anticipo": "Anticipo NY", "mundo": "Corresponsal",
                 "ganadores": "Cazador", "profesionales": "Wall Street", "oportunidad": "Oportunidad"}


def _ruedas_atras(hoy: date, n: int) -> list[str]:
    out, d = [], hoy
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d -= timedelta(days=1)
    return out


def _cerradas(props: list[dict]) -> list[dict]:
    return sorted((p for p in props if (p.get("seguimiento") or {}).get("estado") in CERRADAS and p["seguimiento"].get("fecha_cierre")),
                  key=lambda p: p["seguimiento"]["fecha_cierre"])


def evaluar(props: list[dict], hoy: date) -> dict:
    cer = _cerradas(props)
    motivos = []
    ruedas = set(_ruedas_atras(hoy, RUEDAS_RACHA))
    stops = [p for p in cer if p["seguimiento"]["estado"] == "stop" and p["seguimiento"]["fecha_cierre"] in ruedas]
    if len(stops) >= STOPS_RACHA:
        motivos.append(f"Racha de stops: {len(stops)} en las últimas {RUEDAS_RACHA} ruedas ({', '.join(p['ticker'] for p in stops[-5:])}). "
                       "Hoy no se proponen compras nuevas: el mercado no está acompañando.")
    desde = (hoy - timedelta(days=DIAS_SEMANA)).isoformat()
    suma = round(sum(p["seguimiento"].get("r_neto", p["seguimiento"].get("r", 0)) or 0 for p in cer if p["seguimiento"]["fecha_cierre"] >= desde), 2)
    if suma <= PEOR_R:
        motivos.append(f"Mala racha: las propuestas cerradas en {DIAS_SEMANA} días suman {_r(suma)}R. Pausa hasta que se recupere.")
    pen = {}
    por_tk: dict[str, list[dict]] = {}
    for p in cer:
        por_tk.setdefault(p["ticker"], []).append(p)
    for tk, xs in por_tk.items():
        ult = xs[-2:]
        if len(ult) == 2 and all((x["seguimiento"].get("r_neto", x["seguimiento"].get("r", 0)) or 0) < 0 for x in ult):
            hasta = date.fromisoformat(ult[-1]["seguimiento"]["fecha_cierre"]) + timedelta(days=DIAS_PENITENCIA)
            if hasta >= hoy:
                pen[tk] = {"hasta": hasta.isoformat(), "motivo": f"Las 2 últimas propuestas de {tk} perdieron "
                           f"({', '.join(fecha_corta(x['seguimiento']['fecha_cierre']) for x in ult)}). Fuera hasta el {fecha_corta(hasta.isoformat())}."}
    return {"fecha": hoy.isoformat(), "pausa": bool(motivos), "motivos": motivos, "penitencia": pen, "suma_r_10d": suma}


def _r(x: float) -> str:
    return f"{x:+.1f}".replace(".", ",")


def fecha_corta(f: str) -> str:
    return f"{f[8:10]}/{f[5:7]}"


# ---------- memoria por papel ----------
def _leccion_propuesta(p: dict) -> str:
    seg, pl = p["seguimiento"], p.get("plan") or {}
    ent, cie = seg.get("fecha_entrada") or p["fecha"], seg["fecha_cierre"]
    dias = sum(1 for i in range((date.fromisoformat(cie) - date.fromisoformat(ent)).days + 1)
               if (date.fromisoformat(ent) + timedelta(days=i)).weekday() < 5)
    r = seg.get("r_neto", seg.get("r", 0)) or 0
    favor = sorted({s.get("agente") for s in (p.get("senales") or []) if (s.get("direccion") or 0) > 0 and s.get("agente")})
    from ..agentes.revision import nombre
    quien = f" (a favor: {', '.join(nombre(a) for a in favor[:4])})" if favor else ""
    if seg["estado"] == "objetivo":
        res, lec = f"llegó al objetivo en {dias} ruedas ({_r(r)}R)", "la tesis funcionó; si vuelve a dar la misma combinación, pesa a favor"
    elif seg["estado"] == "stop" and dias <= 2:
        res, lec = f"tocó el stop en {dias} rueda{'s' if dias > 1 else ''} ({_r(r)}R)", "se cayó enseguida: entrada apurada o stop muy corto para cómo se mueve"
    elif seg["estado"] == "stop":
        res, lec = f"tocó el stop en {dias} ruedas ({_r(r)}R)", "la idea no se dio; revisar qué analista se equivocó antes de repetirla"
    elif r > 0.3:
        res, lec = f"se venció el plazo ganando {_r(r)}R", "fue en la dirección correcta pero más lento de lo esperado"
    else:
        res, lec = f"se venció el plazo sin moverse ({_r(r)}R)", "idea lenta: el papel no reaccionó en el plazo"
    return (f"El Jefe lo propuso el {fecha_corta(p['fecha'])} a {pl.get('entrada')}{quien}: {res}. Lección: {lec}.")


ESTADO_PRON = {"se_dio": "se dio", "fallo": "falló (tocó el stop)", "no_se_dio": "no se dio en el plazo"}


def _leccion_pron(x: dict) -> str:
    org = NOMBRE_ORIGEN.get(x.get("origen"), x.get("origen"))
    mejor = x.get("mejor")
    extra = f"; llegó a {_r(mejor)}% en el mejor momento" if isinstance(mejor, (int, float)) else ""
    lec = {"se_dio": "esta herramienta acertó con este papel", "fallo": "con este papel la señal falló: tomarla con más cuidado",
           "no_se_dio": "no reaccionó en el plazo"}.get(x["estado"], "")
    return f"{org} lo marcó el {fecha_corta(x['fecha'])} (objetivo {_r(x.get('objetivo_pct') or 0)}%): {ESTADO_PRON.get(x['estado'], x['estado'])}{extra}. Lección: {lec}."


def memoria(props: list[dict], libreta: list[dict], maximo: int = 6) -> dict[str, list[dict]]:
    """{ticker: [{fecha, origen, ok, texto}]} lo más nuevo primero."""
    out: dict[str, list[dict]] = {}
    for p in _cerradas(props):
        r = p["seguimiento"].get("r_neto", p["seguimiento"].get("r", 0)) or 0
        out.setdefault(p["ticker"], []).append({"fecha": p["seguimiento"]["fecha_cierre"], "origen": "jefe", "ok": r > 0,
                                                "texto": _leccion_propuesta(p)})
    for x in libreta or []:
        if x.get("estado") in ESTADO_PRON and x.get("origen") != "jefe":
            out.setdefault(x["ticker"], []).append({"fecha": str(x.get("fecha_cierre") or x.get("vence") or x["fecha"])[:10], "origen": x.get("origen"),
                                                    "ok": x["estado"] == "se_dio", "texto": _leccion_pron(x)})
    return {tk: sorted(xs, key=lambda y: y["fecha"], reverse=True)[:maximo] for tk, xs in out.items()}
