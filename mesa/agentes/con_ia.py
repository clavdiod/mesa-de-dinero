"""Agentes que usan IA: Noticias, Hechos del emisor, Calificadoras, Debate y Jefe.
Todos tienen una regla de respaldo para cuando no hay clave o la IA falla."""
from __future__ import annotations

import json
import re

from ..datos import gratis
from ..nucleo.config import emisores, nombre_emisor
from ..nucleo.contexto import Contexto
from ..nucleo.ia import IA
from ..nucleo.modelos import Senal

_NEG = re.compile(r"renunci|default|concurso|quiebra|sanci|multa|investigaci|rebaj|downgrade|p[eé]rdida|"
                  r"suspend|imputa|denuncia|incumpl|reestructur", re.I)
_POS = re.compile(r"recompra|dividendo|mejora|upgrade|ganancia|r[eé]cord|adquiere|acuerdo|aprob", re.I)


def _tickers_en(texto: str) -> list[str]:
    out = []
    for tk, d in emisores().items():
        clave = (d or {}).get("clave") or tk
        if re.search(rf"\b{re.escape(tk)}\b", texto) or re.search(rf"\b{re.escape(clave)}\b", texto, re.I):
            out.append(tk)
    return out


# 8. Noticias -----------------------------------------------------------------------------------
def noticias(ctx: Contexto, ia: IA, almacen=None) -> list[Senal]:
    """Solo llama a la IA si llegaron titulares nuevos desde la última ronda (ahorra costo)."""
    import hashlib
    items = ctx.noticias[:40]
    if not items:
        return []
    firma = hashlib.sha1("|".join(n["titulo"] for n in items).encode()).hexdigest()
    previo = almacen.get("noticias/ultimo") if almacen is not None else None
    if previo and previo.get("firma") == firma:
        return [Senal(**s) for s in previo["senales"]]
    out = _noticias(items, ia)
    if almacen is not None:
        almacen.put("noticias/ultimo", {"firma": firma, "senales": [s.dict() for s in out]})
    return out


def _noticias(items: list[dict], ia: IA) -> list[Senal]:
    lista = "\n".join(f"{i}. {n['titulo']} — {n['resumen'][:200]}" for i, n in enumerate(items))
    res = ia.json(
        "Sos el analista de noticias de una mesa de dinero argentina. Para cada titular que afecte a un activo "
        "argentino concreto (acción, bono, ON), indicá ticker BYMA, dirección (+1 positivo, -1 negativo) e "
        "intensidad 0-1. Ignorá lo que no mueve precios. Formato: {\"items\":[{\"i\":0,\"ticker\":\"GGAL\","
        "\"dir\":1,\"fuerza\":0.5,\"motivo\":\"...\"}]}",
        f"Tickers válidos: {', '.join(emisores().keys())}\nTitulares:\n{lista}")
    out = []
    if res and isinstance(res, dict):
        for it in res.get("items", []):
            try:
                n = items[int(it["i"])]
                out.append(Senal("noticias", it["ticker"].upper(), int(it["dir"]), float(it["fuerza"]),
                                 f"{it.get('motivo', '')} ({n['titulo']})", {"link": n["link"], "fuente": n["fuente"]}))
            except Exception:
                continue
        return out
    # respaldo: palabras clave
    for n in items:
        txt = f"{n['titulo']} {n['resumen']}"
        tks = _tickers_en(txt)
        d = -1 if _NEG.search(txt) else (1 if _POS.search(txt) else 0)
        for tk in tks:
            if d:
                out.append(Senal("noticias", tk, d, 0.3, n["titulo"], {"link": n["link"], "regla": True}))
    return out


# 10. Hechos del emisor --------------------------------------------------------------------------
def hechos_emisor(ctx: Contexto, ia: IA, tickers: list[str], almacen) -> list[Senal]:
    """Busca hechos relevantes de cada emisor (1 búsqueda por emisor por día, guardada en el almacén).
    Un hecho grave (renuncia del CEO, default, sanción) congela compras en ese ticker."""
    hoy = ctx.fecha.isoformat()
    guardado = almacen.get(f"hechos/{hoy}") or {}
    out = []
    for tk in tickers:
        nombre = nombre_emisor(tk)
        if not nombre:
            continue
        if tk not in guardado:
            items = gratis.buscar_noticias(f'"{nombre}" (hecho relevante OR renuncia OR directorio OR balance)', horas=72)
            res = None
            if items:
                res = ia.json(
                    "Sos el analista de hechos relevantes. Decidí si alguna noticia es un hecho relevante del emisor "
                    "que pueda generar volatilidad (renuncia de directivos, balance, default, cambio de control, juicio, "
                    "dividendo, emisión). Formato: {\"hay\":true,\"grave\":false,\"dir\":-1,\"resumen\":\"...\"}",
                    f"Emisor: {nombre} ({tk})\n" + "\n".join(f"- {i['titulo']}" for i in items[:10]))
                if res is None:
                    txt = " ".join(i["titulo"] for i in items[:10])
                    neg = bool(_NEG.search(txt))
                    res = {"hay": neg, "grave": False, "dir": -1 if neg else 0, "resumen": items[0]["titulo"] if neg else ""}
            guardado[tk] = {"res": res or {"hay": False}, "titulos": [i["titulo"] for i in items[:5]],
                            "links": [i["link"] for i in items[:5]]}
        r = guardado[tk]["res"]
        ctx.hechos[tk] = guardado[tk]
        if r.get("hay"):
            grave = bool(r.get("grave"))
            out.append(Senal("hechos_emisor", tk, int(r.get("dir", 0)), 0.8 if grave else 0.4,
                             ("HECHO GRAVE: " if grave else "Hecho relevante: ") + r.get("resumen", ""),
                             {"links": guardado[tk]["links"]}, veto=grave and int(r.get("dir", 0)) < 0, evaluable=False))
    almacen.put(f"hechos/{hoy}", guardado)
    return out


# 11. Calificadoras (corre una vez por día) --------------------------------------------------------
CONSULTAS_CALIF = [
    "calificación Argentina Moody's", "calificación Argentina Fitch", "calificación Argentina S&P",
    "FIX SCR calificación obligaciones negociables", "Moody's Local Argentina calificación",
]


def calificadoras(ia: IA, almacen, fecha) -> dict:
    items = []
    for q in CONSULTAS_CALIF:
        items += gratis.buscar_noticias(q, horas=48, max_items=8)
    res = ia.json(
        "Sos el analista de calificadoras. Detectá SOLO cambios concretos de nota, perspectiva o 'en revisión' "
        "de Moody's, S&P, Fitch, FIX o Moody's Local sobre Argentina o emisores argentinos. Formato: "
        "{\"cambios\":[{\"emisor\":\"...\",\"ticker\":\"YPFD o SOBERANO o null\",\"agencia\":\"...\",\"antes\":\"...\","
        "\"despues\":\"...\",\"perspectiva\":\"...\",\"dir\":1,\"link\":\"...\"}]}",
        "\n".join(f"- {i['titulo']} ({i['link']})" for i in items[:40])) if items else {"cambios": []}
    if res is None:  # respaldo sin IA: solo guarda titulares para revisar a mano
        res = {"cambios": [], "titulares": [i["titulo"] for i in items[:15]]}
    res["fecha"] = fecha.isoformat()
    almacen.put("calificadoras/ultimo", res)
    hist = almacen.get("calificadoras/historial") or []
    hist = ([{**c, "fecha": fecha.isoformat()} for c in res.get("cambios", [])] + hist)[:200]
    almacen.put("calificadoras/historial", hist)
    return res


def senales_calificadoras(ctx: Contexto, datos: dict) -> list[Senal]:
    out = []
    for c in (datos or {}).get("cambios", []):
        tk = (c.get("ticker") or "").upper()
        tks = ["AL30D", "GD30D", "AL35D", "GD35D"] if tk == "SOBERANO" else ([tk] if tk else [])
        for t in tks:
            out.append(Senal("calificadoras", t, int(c.get("dir", 0)), 0.6,
                             f"{c.get('agencia')}: {c.get('antes')} → {c.get('despues')} ({c.get('perspectiva', '')})",
                             c, evaluable=False))
    return out


# Debate ---------------------------------------------------------------------------------------
def debate(ia: IA, expediente: dict) -> dict:
    exp = json.dumps(expediente, ensure_ascii=False, default=str)[:6000]
    base = ("Sos parte de una mesa de dinero argentina. Usá SOLO los datos del expediente (precios, señales de "
            "los agentes, historia de gráficos parecidos, hechos y calificaciones). Máximo 3 oraciones, concretas.")
    alc = ia.texto(base + " Tu rol: el ALCISTA. Defendé la compra con el mejor argumento.", exp)
    baj = ia.texto(base + " Tu rol: el BAJISTA. Atacá la compra con el mejor argumento: qué puede salir mal.", exp)
    if alc is None or baj is None:
        pos = [s["texto"] for s in expediente["senales"] if s["direccion"] > 0][:2]
        neg = [s["texto"] for s in expediente["senales"] if s["direccion"] < 0][:2]
        alc = alc or (" ".join(pos) or "Sin argumentos alcistas fuertes.")
        baj = baj or (" ".join(neg) or "El riesgo principal es el clima general del mercado argentino.")
    return {"alcista": alc.strip(), "bajista": baj.strip()}


# 13. Jefe -------------------------------------------------------------------------------------
def jefe(ia: IA, candidatos: list[dict], cupo: int, contexto_txt: str) -> list[dict]:
    """Elige hasta `cupo` propuestas. Cada candidato ya pasó por Riesgo. Respaldo: mayor puntaje."""
    if cupo <= 0 or not candidatos:
        return []
    resumen = json.dumps([{k: c[k] for k in ("id", "ticker", "puntaje", "plan", "debate", "riesgo", "historiador")
                           if k in c} for c in candidatos], ensure_ascii=False, default=str)[:9000]
    res = ia.json(
        "Sos el Jefe de una mesa de dinero argentina. Recibís candidatos ya aprobados por Riesgo, con el debate "
        f"alcista/bajista. Elegí como máximo {cupo}, solo los de convicción real; elegir cero está bien. "
        "Explicá en 2 oraciones claras para alguien que decide desde el celular. Formato: "
        "{\"elegidos\":[{\"id\":\"...\",\"confianza\":\"alta|media\",\"resumen\":\"...\"}],\"descartados\":[{\"id\":\"...\",\"motivo\":\"...\"}]}",
        f"Contexto: {contexto_txt}\nCandidatos: {resumen}", rapido=False)
    por_id = {c["id"]: c for c in candidatos}
    if res and isinstance(res, dict):
        out = []
        for e in res.get("elegidos", [])[:cupo]:
            c = por_id.get(e.get("id"))
            if c:
                out.append({**c, "confianza": e.get("confianza", "media"), "resumen_jefe": e.get("resumen", "")})
        for d in res.get("descartados", []):
            if d.get("id") in por_id:
                por_id[d["id"]]["motivo_descarte"] = d.get("motivo")
        return out
    elegidos = sorted(candidatos, key=lambda c: c["puntaje"], reverse=True)[:cupo]
    return [{**c, "confianza": "media", "resumen_jefe": "Elegida por puntaje (Jefe sin IA disponible)."} for c in elegidos]


# Licitaciones del Tesoro (1 vez por día) --------------------------------------------------------
def licitaciones(ia: IA, almacen, fecha) -> dict:
    """Busca el llamado/resultado de la próxima licitación del Tesoro (LECAP, BONCAP, duales, CER)."""
    items = gratis.buscar_noticias("licitación Tesoro Finanzas LECAP BONCAP", horas=168, max_items=15)
    items += gratis.buscar_noticias("licitación del Tesoro llamado instrumentos vencimientos", horas=168, max_items=10)
    res = ia.json(
        "Sos el analista de pesos y tasas de una mesa argentina. Con estos titulares, identificá la PRÓXIMA licitación "
        "del Tesoro (y si hay, el resultado de la última). Formato: {\"proxima\":{\"fecha\":\"AAAA-MM-DD o null\","
        "\"liquidacion\":\"AAAA-MM-DD o null\",\"instrumentos\":[\"...\"],\"vencimientos_a_cubrir\":\"...\"},"
        "\"ultima\":{\"fecha\":\"...\",\"rollover_pct\":null,\"tasas\":\"...\"},\"lectura\":\"2 oraciones\"}",
        "\n".join(f"- {i['titulo']} ({i['fecha']})" for i in items[:25])) if items else None
    if res is None:
        res = {"titulares": [{"titulo": i["titulo"], "link": i["link"], "fecha": i["fecha"]} for i in items[:8]]}
    res["actualizado"] = fecha.isoformat()
    almacen.put("licitaciones/ultimo", res)
    return res
