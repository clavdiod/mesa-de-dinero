"""22/11 (revisión con Clau: "¿qué se rompería primero?"): el Vigía avisa cuando un agente se queda mudo.

La ronda tiene muchos lugares donde, si una fuente falla (Yahoo, data912, un dato viejo), el error se anota en el log y la
ronda sigue sin ese agente. El puntaje cambia sin que nadie se entere. El Vigía lleva la cuenta de qué agentes hablaron
en cada ronda; si uno que habla casi siempre (en 8 de cada 10 rondas o más) lleva 6 rondas seguidas sin decir nada,
te avisa una vez por día. Cuando vuelve a hablar, la cuenta arranca de nuevo.

No suma escrituras: el estado viaja dentro de ui/estado, que la ronda ya guarda siempre.
"""
from __future__ import annotations

HABITUAL = 0.8      # habla en 8 de cada 10 rondas o más
RONDAS_MUDO = 6     # ~30 a 60 minutos de mercado
SUAVE = 0.1         # cuánto pesa cada ronda nueva en la tasa (promedio móvil)
MIN_RONDAS = 10     # con menos historia no se sabe si es habitual
MIN_DIAS = 3        # 25/11: y tres días vistos, para conocer su silencio normal (Acciones parecía "habitual" con media tarde)
# 25/11 (Acciones, "lleva 6 rondas sin decir nada" a las 12:20): hay agentes que hablan solo cuando pasa algo (Acciones
# necesita volumen 1,5x, que a la mañana todavía no se juntó). Cada agente tiene su silencio normal más largo (max_sin):
# el Vigía avisa solo si el silencio de hoy pasa el doble de eso.
# 24/11: agentes que por diseño hablan solo en una franja (Noche de Nueva York opina hasta las 13 h). Fuera de su
# horario no cuentan: ni como que hablaron ni como que se callaron (antes el Vigía daba una falsa alarma a las 14 h).
HORARIO = {"adr": ("00:00", "13:00")}


def en_horario(ag: str, hora: str) -> bool:
    desde, hasta = HORARIO.get(ag, ("00:00", "23:59"))
    return not hora or desde <= hora[:5] <= hasta


def umbral(x: dict) -> int:
    """Rondas de silencio para avisar: 6, o el doble del silencio normal más largo de ese agente."""
    return max(RONDAS_MUDO, 2 * int(x.get("max_sin", 0)))


def actualizar(previo: dict | None, hablaron: set[str], hoy: str, hora: str) -> tuple[dict, list[dict]]:
    """previo: el estado de la ronda anterior. hablaron: agentes que dejaron alguna señal en esta ronda (aunque sea
    "sin novedades"). Devuelve (estado nuevo, avisos para el celular)."""
    ags = {k: dict(v) for k, v in ((previo or {}).get("agentes") or {}).items()}
    avisos = []
    for ag in set(ags) | set(hablaron):
        if ag not in hablaron and not en_horario(ag, hora):
            continue  # fuera de su franja: callarse es lo normal
        x = ags.setdefault(ag, {"tasa": 0.5, "rondas": 0, "sin": 0})  # nuevo: tiene que demostrar que habla seguido
        x["rondas"] = x.get("rondas", 0) + 1
        if x.get("dia") != hoy:
            x["dia"], x["dias"] = hoy, x.get("dias", 0) + 1
        if ag in hablaron:
            if x.get("sin", 0):
                x["max_sin"] = max(x.get("max_sin", 0), x["sin"])  # un silencio que terminó solo, el mismo día: era normal
            x["tasa"] = round((1 - SUAVE) * x.get("tasa", 1.0) + SUAVE, 3)
            x["sin"] = 0
            x["ultima"] = f"{hoy} {hora}"
            x.pop("tasa_antes", None)
            continue
        if x.get("sin", 0) == 0:
            x["tasa_antes"] = x.get("tasa", 1.0)  # lo habitual que era justo antes de callarse
        x["sin"] = x.get("sin", 0) + 1
        x["tasa"] = round((1 - SUAVE) * x.get("tasa", 1.0), 3)
        if (x["sin"] >= umbral(x) and x.get("tasa_antes", 0) >= HABITUAL and x["rondas"] >= MIN_RONDAS
                and x.get("dias", 0) >= MIN_DIAS and x.get("avisado") != hoy):
            x["avisado"] = hoy
            avisos.append(aviso(ag, x, hoy, hora))
    # los que se fueron hace mucho (agentes dados de baja) dejan de contarse
    ags = {k: v for k, v in ags.items() if v.get("tasa", 0) >= 0.05 or k in hablaron}
    return {"fecha": hoy, "hora": hora, "agentes": ags,
            "mudos": sorted(k for k, v in ags.items() if v.get("sin", 0) >= umbral(v) and v.get("tasa_antes", 0) >= HABITUAL
                            and v.get("dias", 0) >= MIN_DIAS and en_horario(k, hora))}, avisos


def aviso(ag: str, x: dict, hoy: str, hora: str) -> dict:
    try:
        from ..agentes.revision import nombre
        nom = nombre(ag)
    except Exception:
        nom = ag
    ult = x.get("ultima") or ""
    cuando = f" (habló por última vez {'hoy a las ' + ult[11:] if ult[:10] == hoy else 'el ' + ult[8:10] + '/' + ult[5:7] + ' ' + ult[11:]})" if ult else ""
    return {"fecha": hoy, "hora": hora, "ticker": f"⚠️ {nom}", "tipo": "agente_mudo", "agente": ag,
            "texto": f"⚠️ {nom} lleva {x['sin']} rondas sin decir nada{cuando} y casi siempre habla. "
                     "Puede que se haya caído una fuente de datos: mientras tanto la mesa decide sin su voto."}
