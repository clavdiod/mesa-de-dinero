"""Analista de volúmenes de tu cartera (06/11). Pedido de Clau: "que vea volúmenes no normales de compra o venta y nos avise".

Solo papeles tuyos (acciones argentinas: es donde está probado) y solo lo que la historia mostró que significa algo.
Probado 06/11 con 66 acciones argentinas, 10 años, en dólares, entrada al día siguiente, neto de 1,2% de comisión.
Un día cualquiera: a 5 ruedas -1,1% (suben 39%), a 20 ruedas -0,5% (suben 42%).
- Compra fuerte (2,5 veces el volumen, sube 2%+, cerca del máximo del día): 20 ruedas +2,2%, suben 49%.
- Venta fuerte (2,5 veces, cae 2%+, cerca del mínimo): la semana siguiente -1,5% (suben 40%); a 20 ruedas +0,1% (igual que siempre).
- Venta fuerte en el mínimo del año: a 20 ruedas +3,5%, suben 51% (muchas veces es la descarga final).
- Agotamiento (un día de venta con 3 veces el volumen y -4%, y al otro día volumen normal sin perforar): 20 ruedas +4,0%, suben 55%.
- Venta sostenida 3 días (lo de TRAN): 20 ruedas +1,5%, suben 46%: no anticipa más caída.
"""
from __future__ import annotations

import statistics as st


def _n(x: float, d: int = 1) -> str:
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def avisos(cartera: list[dict], titulo, velas, hoy: str, hora: str, avisados: dict) -> list[dict]:
    """titulo(tk) -> panel de hoy; velas(tk) -> historial diario (sin hoy). avisados se modifica (un aviso por tipo y día)."""
    out = []
    if not ("12:00" <= (hora or "") <= "17:05"):  # antes del mediodía la proyección del volumen del día es poco confiable
        return out
    h, m = (int(x) for x in hora.split(":")[:2])
    frac = min(1.0, max(0.15, (h * 60 + m - 630) / 390))  # rueda 10:30-17:00
    for pos in cartera or []:
        tk = str(pos.get("ticker") or "").upper()
        t = titulo(tk) or {}
        if t.get("grupo") != "acciones" or not t.get("ultimo") or not t.get("volumen"):
            continue
        vs = [v for v in velas(tk) if v.get("cierre") and v.get("fecha") != hoy]  # solo días cerrados
        vols = [v["volumen"] for v in vs[-21:-1] if v.get("volumen")]
        if len(vols) < 15 or not st.mean(vols):
            continue
        prom = st.mean(vols)
        rel = t["volumen"] / frac / prom
        ult, ant = t["ultimo"], t.get("cierre_anterior") or vs[-1]["cierre"]
        var = (ult / ant - 1) * 100
        hi, lo = t.get("maximo") or ult, t.get("minimo") or ult
        posd = (ult - lo) / (hi - lo) if hi > lo else 0.5
        min_anual = min(v["cierre"] for v in vs[-252:]) if len(vs) >= 120 else None
        tipo = texto = None
        # 1) agotamiento: ayer venta fuerte, hoy volumen normal y sin perforar (se mira desde las 15:00)
        ay = vs[-1]
        rel_ay = (ay.get("volumen") or 0) / (st.mean([v["volumen"] for v in vs[-22:-2] if v.get("volumen")]) or 1)
        var_ay = (ay["cierre"] / vs[-2]["cierre"] - 1) * 100 if len(vs) > 1 else 0
        if hora >= "15:00" and rel_ay >= 3 and var_ay <= -4 and rel < 1.2 and ult >= ay["cierre"]:
            tipo = "agotamiento"
            texto = (f"🟡 {tk}: la venta parece agotarse. Ayer operó {_n(rel_ay)} veces su volumen normal y cayó {_n(var_ay)}%; "
                     f"hoy el volumen volvió a lo normal ({_n(rel)} veces) y no perforó ({'+' if var >= 0 else ''}{_n(var)}%). "
                     f"En 10 años de acciones argentinas, después de esto subió 55 de cada 100 veces en el mes siguiente (+4% promedio), "
                     f"contra 42 de cada 100 un día cualquiera. Es la mejor señal de volumen que encontramos: buena razón para no vender por pánico.")
        elif rel >= 2.5 and var >= 2 and posd >= 0.7:
            tipo = "compra"
            texto = (f"🟢 {tk}: compradores fuertes. Va camino a {_n(rel)} veces su volumen normal, sube {_n(var)}% y opera cerca del máximo del día. "
                     f"En 10 años, después de días así subió 49 de cada 100 veces en el mes siguiente (+2,2% promedio), contra 42 de cada 100 un día cualquiera. "
                     f"Señal a favor de mantener.")
        elif rel >= 2.5 and var <= -2 and posd <= 0.3:
            tipo = "venta"
            en_min = min_anual is not None and ult <= min_anual
            texto = (f"🔴 {tk}: vendedores fuertes. Va camino a {_n(rel)} veces su volumen normal, cae {_n(var)}% y opera cerca del mínimo del día. "
                     f"En 10 años, después de días así la semana siguiente suele seguir floja (-1,5% promedio), pero a un mes no cambia nada. "
                     + ("Además está en su mínimo del año: ahí la venta fuerte muchas veces es la descarga final (a un mes subió 51 de cada 100, +3,5% promedio). "
                        if en_min else "")
                     + "No es motivo para vender por sí solo: lo que manda es tu alarma de venta.")
        if not tipo or avisados.get(f"vol:{tk}") == f"{hoy}|{tipo}":
            continue
        avisados[f"vol:{tk}"] = f"{hoy}|{tipo}"
        out.append({"fecha": hoy, "hora": hora, "ticker": f"{tk} (volumen)", "texto": texto, "tipo_aviso": "volumen"})
    return out
