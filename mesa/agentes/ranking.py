"""Orden de las propuestas (20/11, Clau: "poné primero la que es más probable de ganar más plata en menos tiempo").

Cada propuesta lleva cuánto se espera ganar POR MES (neto de comisión) y qué tan seguido llegó a +5% en un mes, según la
prueba con historia de su propia regla. La app las ordena 1º, 2º, 3º... por ganancia esperada por mes.
- Posiciones de 3 meses: rendimiento típico de su regla (en dólares) dividido 3.
- Posiciones de 12 meses (Graham, Lynch, Greenblatt): lo que le ganaron al S&P más lo que rindió el S&P típico (~12% anual), dividido 12.
- Operaciones cortas del Comité: (veces que llegó al objetivo × objetivo − veces que tocó el stop × stop − comisión) / meses del plazo,
  con los casos parecidos del propio papel (ficha en frío)."""
from __future__ import annotations

SP_ANUAL = 12.0
TIPOS = {  # ganancia típica por mes (%), llegó a +5% en un mes (%) — scripts/probar_rebote_usd, probar_kostolany, probar_plazos, probar_murphy
    "rebote": (4.4 / 3, 69), "retroceso": (3.9 / 3, None), "panico_cedears": (6.8 / 3, 61), "panico_acciones": (3.9 / 3, 64),
    "graham": ((3.3 + SP_ANUAL) / 12, None), "greenblatt": ((3.4 + SP_ANUAL) / 12, None),
    "lynch_caja": ((15.2 + SP_ANUAL) / 12, None), "lynch_combo": ((4.2 + SP_ANUAL) / 12, None),
}


def puntaje(p: dict) -> dict:
    tipo = p.get("tipo_posicion")
    if p.get("linea") == "posicion" and tipo:
        if tipo == "panico":
            g = "panico_cedears" if (p.get("sector") or "").lower() != "acciones" and "CEDEAR" in (p.get("resumen_jefe") or "") else "panico_acciones"
            g = "panico_cedears" if "en CEDEARs" in (p.get("resumen_jefe") or "") else g
        elif tipo == "lynch":
            g = "lynch_caja" if "caja neta" in (p.get("resumen_jefe") or "") else "lynch_combo"
        else:
            g = tipo
        mes, p1 = TIPOS.get(g, (0.0, None))
        return {"ganancia_mes_pct": round(mes, 2), "llega_5_1m_pct": p1, "base": g}
    pl, h = p.get("plan") or {}, ((p.get("ficha_frio") or {}).get("historia") or {})
    try:
        obj = (pl["objetivo"] / pl["entrada"] - 1) * 100
        stp = (1 - pl["stop"] / pl["entrada"]) * 100
        meses = max(0.25, float(p.get("ruedas") or 10) / 21)
        if h.get("llega_obj") is not None:
            esp = (h["llega_obj"] / 100 * obj - h["toca_stop"] / 100 * stp - 1.2) / meses
            n = float(h.get("casos") or 0)
            esp *= n / (n + 30)  # con pocos casos parecidos el número es poco confiable: se achica hacia cero
            return {"ganancia_mes_pct": round(esp, 2), "llega_5_1m_pct": None, "base": f"{int(n)} casos parecidos del papel"}
    except Exception:
        pass
    return {"ganancia_mes_pct": None, "llega_5_1m_pct": None, "base": None}
