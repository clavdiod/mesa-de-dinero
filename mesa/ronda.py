"""Una ronda de la mesa: datos → 13 agentes → debate → Riesgo → Jefe → registro y avisos.

Uso:  python -m mesa.ronda            (decide sola si le toca correr según hora y presupuesto)
      python -m mesa.ronda --forzar   (corre igual, p. ej. botón 'Analizar ahora')
      python -m mesa.ronda --simular  (sin IOL: usa tests/fixtures, para probar)
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date

import yaml

from .agentes import analistas, con_ia, riesgo
from .datos import gratis
from .datos.cache import CacheHistorico
from .datos.consumo import Consumo, PresupuestoAgotado
from .nucleo import push
from .nucleo.almacen import almacen_por_defecto
from .nucleo.config import RAIZ, config, sector
from .nucleo.contexto import Contexto
from .nucleo.ia import IA
from .nucleo.modelos import Senal
from .nucleo.registro import Registro
from .nucleo.reloj import ahora, es_dia_habil, toca_correr


def _eventos() -> list[dict]:
    with open(RAIZ / "config" / "eventos.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f) or []


def cargar_paneles(iol, consumo: Consumo, almacen, simular: bool) -> dict[str, list[dict]]:
    if simular:
        return json.loads((RAIZ / "tests" / "fixtures" / "paneles.json").read_text(encoding="utf-8"))
    nombres = almacen.get("iol/paneles") or {}   # nombres reales descubiertos por scripts/probar_iol.py
    out: dict[str, list[dict]] = {}
    for p in config()["iol"]["paneles"]:
        clave = f"{p['instrumento']}|{p['panel']}"
        inst, pan = nombres.get(clave, (p["instrumento"], p["panel"]))
        if not consumo.puede_consultar(1):
            break
        try:
            out.setdefault(p["grupo"], []).extend(iol.panel(inst, pan))
        except PresupuestoAgotado:
            break
        except Exception as e:
            print(f"[panel] {clave}: {e}")
    return out


def refrescar_puntas(ctx: Contexto, iol, consumo: Consumo, tickers: list[str]) -> None:
    """Puntas detalladas solo para Mi lista y posiciones abiertas, con tope por ronda."""
    tope = config()["iol"]["max_puntas_por_ronda"]
    for tk in tickers[:tope]:
        if not consumo.puede_consultar(1):
            return
        try:
            t = iol.cotizacion(tk, plazo=config()["mercado"]["plazo"])
            base = ctx.por_simbolo.get(tk, {})
            ctx.por_simbolo[tk] = {**base, **{k: v for k, v in t.items() if v not in (None, [])}}
        except Exception as e:
            print(f"[puntas] {tk}: {e}")


def puntaje_ticker(senales: list[Senal], reg: Registro) -> float:
    tot = 0.0
    for s in senales:
        if s.direccion:
            tot += s.direccion * s.fuerza * reg.peso(s.agente)
    return round(tot, 3)


def correr(forzar: bool = False, simular: bool = False) -> dict:
    almacen = almacen_por_defecto()
    ya = ahora()
    hoy = ya.date()
    consumo = Consumo(almacen)

    if not simular and not forzar:
        if not es_dia_habil(hoy, almacen):
            return {"corrio": False, "motivo": "día no hábil"}
        if consumo.solo_cierre():
            return {"corrio": False, "motivo": f"consumo IOL {consumo.pct:.0f}%: solo ronda de cierre"}
        if not toca_correr(ya, consumo.factor_frecuencia()):
            return {"corrio": False, "motivo": "no toca en este horario"}

    iol = None
    if not simular:
        from .datos.iol import IOL
        iol = IOL(consumo, almacen=almacen)
    cache = CacheHistorico(almacen, iol)
    reg = Registro(almacen)
    estado_ui = almacen.get("ui/estado") or {}
    lista = almacen.get("usuario/lista") or []
    cartera = almacen.get("usuario/cartera") or []
    params = almacen.get("params/agentes") or {}
    rp_ayer = (almacen.get("ref/riesgo_pais_cierre") or {}).get("valor")

    paneles = cargar_paneles(iol, consumo, almacen, simular)
    if not any(paneles.values()):
        consumo.guardar()
        return {"corrio": False, "motivo": "sin datos de paneles"}

    ctx = Contexto(fecha=hoy, hora=ya.strftime("%H:%M"), paneles=paneles,
                   dolares={} if simular else gratis.dolares(),
                   riesgo_pais={} if simular else gratis.riesgo_pais(), riesgo_pais_ayer=rp_ayer,
                   reservas={} if simular else gratis.bcra_reservas(),
                   noticias=[] if simular else gratis.noticias(),
                   cache=cache, lista=lista, cartera=cartera, params=params, eventos=_eventos())
    if simular:
        fx = json.loads((RAIZ / "tests" / "fixtures" / "contexto.json").read_text(encoding="utf-8"))
        ctx.dolares, ctx.riesgo_pais, ctx.riesgo_pais_ayer = fx["dolares"], fx["riesgo_pais"], fx["riesgo_pais_ayer"]

    ctx.extra["ons_usuario"] = almacen.get("usuario/ons") or {}
    abiertas = [p["ticker"] for p in reg.abiertas()]
    foco = list(dict.fromkeys(ctx.tickers_lista() + abiertas))
    if iol is not None:
        refrescar_puntas(ctx, iol, consumo, foco)

    ia = IA()
    # --- analistas por reglas ---
    senales: list[Senal] = []
    senales += analistas.macro_dolar(ctx)
    senales += analistas.acciones(ctx)
    senales += analistas.cedears(ctx)
    senales += analistas.ons(ctx)
    senales += analistas.soberanos(ctx)
    senales += analistas.pesos_tasas(ctx)
    senales += con_ia.noticias(ctx, ia, almacen)
    cal = almacen.get("calificadoras/ultimo") or {}
    if cal.get("fecha") == hoy.isoformat():
        senales += con_ia.senales_calificadoras(ctx, cal)

    # candidatos: lo que alguien marcó + Mi lista; con carga de historial una sola vez por ticker
    marcados = [s.ticker for s in senales if s.direccion != 0 and ctx.titulo(s.ticker)]
    candidatos = list(dict.fromkeys(foco + marcados))
    restantes_hist = 5  # máximo de cargas iniciales de historial por ronda (cuida el cupo)
    for tk in candidatos:
        antes = len(cache.velas(tk))
        cache.asegurar(tk, restantes_hist)
        if antes == 0 and cache.velas(tk):
            restantes_hist -= 1
    senales += analistas.tecnico(ctx, candidatos)
    senales += analistas.historiador(ctx, candidatos)

    por_ticker: dict[str, list[Senal]] = {}
    for s in senales:
        por_ticker.setdefault(s.ticker, []).append(s)
    puntajes = {tk: puntaje_ticker(ss, reg) for tk, ss in por_ticker.items() if ctx.titulo(tk)}
    preseleccion = [tk for tk, p in sorted(puntajes.items(), key=lambda x: -x[1]) if p >= 0.6][:8]
    preseleccion += [tk for tk in ctx.tickers_lista() if tk not in preseleccion and puntajes.get(tk, 0) > 0]

    # --- hechos del emisor (solo preseleccionados, 1 búsqueda por emisor por día) ---
    hechos = [] if simular else con_ia.hechos_emisor(ctx, ia, preseleccion, almacen)
    senales += hechos
    vetos = {s.ticker for s in hechos if s.veto}

    # --- Riesgo ---
    propuestas_hoy = reg.de_hoy(hoy)
    estado = {"abiertas": reg.abiertas(), "propuestas_hoy": propuestas_hoy,
              "perdida_dia_r": reg.resultado_periodo(hoy.isoformat()),
              "perdida_semana_r": reg.resultado_periodo(date.fromordinal(hoy.toordinal() - hoy.weekday()).isoformat())}
    ya_propuestos = {p["ticker"] for p in propuestas_hoy} | set(abiertas)
    evaluados = []
    for tk in preseleccion:
        if tk in ya_propuestos:
            continue
        plan = riesgo.armar_plan(ctx, tk)
        if not plan:
            continue
        r = riesgo.evaluar(ctx, plan, estado, vetos)
        plan.tamano_r = r["tamano_r"]
        sh = [s for s in por_ticker.get(tk, [])]
        hist = next((s.datos for s in sh if s.agente == "historiador"), None)
        evaluados.append({"id": hashlib.sha1(f"{hoy}{tk}{ctx.hora}".encode()).hexdigest()[:10], "ticker": tk,
                          "sector": sector(tk), "puntaje": puntajes[tk], "plan": plan.dict(), "riesgo": r,
                          "senales": [s.dict() for s in sh], "historiador": hist})

    cupo = config()["riesgo"]["max_propuestas_dia"] - len(propuestas_hoy)
    # lo que el Jefe ya descartó hoy no se vuelve a debatir salvo que el puntaje haya subido
    descartes = almacen.get(f"jefe/descartes/{hoy.isoformat()}") or {}
    aprobados = [e for e in evaluados if e["riesgo"]["ok"] and e["puntaje"] > descartes.get(e["ticker"], -9)]
    if cupo <= 0:
        aprobados = []
    for e in aprobados[: config()["ia"]["max_candidatos_debate"]]:
        e["debate"] = con_ia.debate(ia, {"ticker": e["ticker"], "plan": e["plan"], "senales": e["senales"],
                                         "hechos": ctx.hechos.get(e["ticker"]), "clima": ctx.extra.get("clima_estado")})
    contexto_txt = (f"Clima {ctx.extra.get('clima_estado')}, riesgo país {ctx.riesgo_pais.get('valor')} "
                    f"(ayer {ctx.riesgo_pais_ayer}), MEP {ctx.extra.get('mep_al30')}, CCL {ctx.extra.get('ccl_al30')}")
    debatidos = [e for e in aprobados if "debate" in e]
    elegidos = con_ia.jefe(ia, debatidos, cupo, contexto_txt)
    ids_elegidos = {e["id"] for e in elegidos}
    for e in debatidos:
        if e["id"] not in ids_elegidos:
            descartes[e["ticker"]] = e["puntaje"]
    if debatidos:
        almacen.put(f"jefe/descartes/{hoy.isoformat()}", descartes)

    cap = {**config()["capital"], **{k: v for k, v in (almacen.get("usuario/capital") or {}).items() if v}}
    un_r = float(cap.get("monto_ars", 0)) * float(cap.get("riesgo_pct", cap.get("riesgo_por_operacion_pct", 1))) / 100
    nuevas = []
    for e in elegidos:
        pl = e["plan"]
        riesgo_unit = pl["entrada"] - pl["stop"]
        cantidad = int(un_r * pl["tamano_r"] / riesgo_unit) if riesgo_unit > 0 and un_r else None
        nuevas.append({**e, "fecha": hoy.isoformat(), "hora": ctx.hora, "decision": "pendiente",
                       "cantidad_sugerida": cantidad, "seguimiento": {"estado": "pendiente"}})
    reg.nuevas(nuevas)

    # --- seguimiento de propuestas y señales ---
    reg.actualizar_seguimiento({k: v for k, v in ctx.por_simbolo.items()}, hoy)
    reg.guardar_senales(hoy, [s.dict() for s in senales],
                        {k: v["ultimo"] for k, v in ctx.por_simbolo.items() if v.get("ultimo")})
    reg.guardar()
    cache.guardar()

    # --- estado para la web ---
    resumen = {
        "fecha": hoy.isoformat(), "hora": ctx.hora, "clima": ctx.extra.get("clima_estado"),
        "indicadores": {k: ctx.extra.get(k) for k in ("mep_al30", "ccl_al30", "canje_pct", "spread_gd_al_30",
                                                       "brecha_mep_pct", "caucion_tna", "ccl_cedears_mediana")},
        "riesgo_pais": ctx.riesgo_pais, "riesgo_pais_ayer": ctx.riesgo_pais_ayer, "dolares": ctx.dolares,
        "reservas": ctx.reservas,
        "senales": [s.dict() for s in senales][:300],
        "evaluados": [{k: e[k] for k in ("ticker", "puntaje", "plan", "riesgo")} for e in evaluados],
        "nuevas": [n["id"] for n in nuevas],
        "lista": {tk: ctx.por_simbolo.get(tk) for tk in ctx.tickers_lista()},
        "precios": {tk: {k: ctx.por_simbolo[tk].get(k) for k in ("ultimo", "variacion", "compra", "venta", "grupo")}
                    for tk in set(ctx.tickers_lista()) | set(abiertas) | set(ctx.extra["ons_usuario"])
                    | {c.get("ticker", "").upper() for c in cartera} if tk in ctx.por_simbolo},
        "tir_ons": ctx.extra.get("tir_ons"),
        "consumo_iol": consumo.resumen(), "ia_llamadas": ia.llamadas,
        "esperanza": reg.esperanza_mesa(),
    }
    almacen.put("ui/estado", {**estado_ui, **resumen})
    previas = almacen.get("ui/alertas") or []
    ya_avisadas = {(a["fecha"], a["ticker"]) for a in previas}
    alertas_lista = [a for a in _alertas_lista(ctx, lista) if (a["fecha"], a["ticker"]) not in ya_avisadas]
    if alertas_lista:
        almacen.put("ui/alertas", (alertas_lista + previas)[:60])
    consumo.guardar()

    if (nuevas or alertas_lista) and not simular:
        subs = almacen.get("push/suscripciones") or []
        res = push.enviar(subs)
        if res["vencidas"]:
            almacen.put("push/suscripciones", [s for s in subs if s.get("endpoint") not in res["vencidas"]])
    return {"corrio": True, "nuevas": len(nuevas), "senales": len(senales), "consumo": consumo.resumen(),
            "diagnostico": {"paneles": {g: len(t) for g, t in paneles.items()},
                            "riesgo_pais": ctx.riesgo_pais.get("valor"), "rp_ayer": ctx.riesgo_pais_ayer,
                            "dolares": sorted(k for k in ctx.dolares if not k.startswith("_")),
                            "noticias": len(ctx.noticias), "con_historial": len(cache.indice),
                            "ia": ia.disponible, "agentes": sorted({s.agente for s in senales}),
                            "ejemplo_soberanos": [t["simbolo"] for t in paneles.get("soberanos", [])[:8]],
                            "ejemplo_cedears": [t["simbolo"] for t in paneles.get("cedears", [])[:8]]}}


def _ar(x: float) -> str:
    return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _alertas_lista(ctx: Contexto, lista: list[dict]) -> list[dict]:
    """Alertas propias de Mi lista: precio objetivo tocado."""
    out = []
    for item in lista:
        t = ctx.titulo(item.get("ticker", ""))
        if not t or not t.get("ultimo") or not item.get("precio"):
            continue
        p = float(item["precio"])
        if (t.get("minimo") or t["ultimo"]) <= p <= (t.get("maximo") or t["ultimo"]):
            out.append({"fecha": ctx.fecha.isoformat(), "hora": ctx.hora, "ticker": item["ticker"],
                        "texto": f"{item['ticker']} tocó tu precio {_ar(p)} (último {_ar(t['ultimo'])})."})
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--forzar", action="store_true")
    ap.add_argument("--simular", action="store_true")
    a = ap.parse_args()
    import traceback
    try:
        r = correr(a.forzar, a.simular)
        print(json.dumps(r, ensure_ascii=False, indent=1, default=str))
        if r.get("corrio"):
            print(f"::notice::Ronda OK: {r['nuevas']} propuestas, {r['senales']} señales, IOL {r['consumo']['total']}/{r['consumo']['tope']} | {json.dumps(r['diagnostico'], ensure_ascii=False)}")
    except Exception as e:
        tb = traceback.extract_tb(e.__traceback__)[-1]
        print(f"::error::{type(e).__name__}: {str(e)[:400]} (en {tb.filename.split('/')[-1]}:{tb.lineno})")
        raise
