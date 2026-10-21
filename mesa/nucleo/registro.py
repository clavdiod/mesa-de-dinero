"""Registro de propuestas y señales, seguimiento en R, ranking de agentes e incentivos.

- Toda propuesta se sigue "en prueba" aunque la rechaces: así se mide si la mesa acierta.
- Las señales de cada agente se guardan una por agente/ticker/día y se evalúan a 5 y 10 ruedas.
- Ranking: % de aciertos y esperanza (en %) por agente; con ≥ minimo_casos se asigna nivel y peso.
"""
from __future__ import annotations

import statistics as st
from datetime import date

from .config import config

ESTADOS_ABIERTOS = ("pendiente", "abierta")


class Registro:
    def __init__(self, almacen):
        self.a = almacen
        self.propuestas: list[dict] = almacen.get("registro/propuestas") or []
        self.pesos: dict = almacen.get("ranking/pesos") or {}
        self.calibracion: dict = almacen.get("ranking/calibracion") or {}
        # Tus decisiones las escribe la web en otra clave (así nunca se pisan con la ronda)
        decisiones = almacen.get("usuario/decisiones") or {}
        for p in self.propuestas:
            if p["id"] in decisiones:
                p["decision"] = decisiones[p["id"]]["decision"]
                p["decision_hora"] = decisiones[p["id"]].get("hora")

    # ---------- propuestas ----------
    def nuevas(self, props: list[dict]) -> None:
        self.propuestas = props + self.propuestas

    def de_hoy(self, fecha: date) -> list[dict]:
        return [p for p in self.propuestas if p["fecha"] == fecha.isoformat()]

    def abiertas(self) -> list[dict]:
        return [p for p in self.propuestas if p["seguimiento"]["estado"] in ESTADOS_ABIERTOS]

    def actualizar_seguimiento(self, precios: dict[str, dict], fecha: date) -> list[dict]:
        """precios: ticker -> {'ultimo','minimo','maximo'}. Devuelve las que cambiaron de estado."""
        cambios = []
        for p in self.abiertas():
            t = precios.get(p["ticker"])
            if not t or not t.get("ultimo"):
                continue
            seg, plan = p["seguimiento"], p["plan"]
            lo, hi, ult = t.get("minimo") or t["ultimo"], t.get("maximo") or t["ultimo"], t["ultimo"]
            # el mínimo/máximo del día pueden haber ocurrido ANTES de proponer o de entrar:
            # ese día se mira solo el último precio de cada ronda
            if fecha.isoformat() in (p.get("fecha"), seg.get("fecha_entrada")):
                lo = hi = ult
            if seg["estado"] == "pendiente":
                if lo <= plan["entrada"]:
                    seg.update(estado="abierta", fecha_entrada=fecha.isoformat(), precio_entrada=plan["entrada"])
                    cambios.append(p)
                elif fecha.isoformat() > plan["vence"]:
                    seg.update(estado="no_ejecutada", fecha_cierre=fecha.isoformat())
                    cambios.append(p)
                continue
            riesgo = plan["entrada"] - plan["stop"]
            if lo <= plan["stop"]:  # si en el mismo día toca stop y objetivo, se asume lo peor
                seg.update(estado="stop", precio_salida=plan["stop"], fecha_cierre=fecha.isoformat(), r=-1.0)
            elif hi >= plan["objetivo"]:
                seg.update(estado="objetivo", precio_salida=plan["objetivo"], fecha_cierre=fecha.isoformat(),
                           r=round((plan["objetivo"] - plan["entrada"]) / riesgo, 2))
            elif fecha.isoformat() >= plan["vence"]:
                seg.update(estado="tiempo", precio_salida=ult, fecha_cierre=fecha.isoformat(),
                           r=round((ult - plan["entrada"]) / riesgo, 2))
            else:
                seg["r_actual"] = round((ult - plan["entrada"]) / riesgo, 2)
                continue
            com = config()["capital"]["comision_ida_vuelta_pct"]
            seg["r_neto"] = round(seg["r"] - com / 100 * plan["entrada"] / riesgo, 2)
            cambios.append(p)
        return cambios

    def resultado_periodo(self, desde: str) -> float:
        """Suma de R neto de las operaciones aprobadas cerradas desde una fecha."""
        return round(sum(p["seguimiento"].get("r_neto", 0) for p in self.propuestas
                         if p.get("decision") == "aprobada" and p["seguimiento"].get("fecha_cierre", "") >= desde), 2)

    def esperanza_mesa(self) -> dict:
        rs = [p["seguimiento"]["r_neto"] for p in self.propuestas if "r_neto" in p["seguimiento"]]
        if not rs:
            return {"casos": 0}
        g, p = [r for r in rs if r > 0], [r for r in rs if r <= 0]
        pa = len(g) / len(rs)
        e = pa * (st.mean(g) if g else 0) + (1 - pa) * (st.mean(p) if p else 0)
        return {"casos": len(rs), "aciertos_pct": round(pa * 100, 1), "esperanza_r": round(e, 3),
                "ganancia_media_r": round(st.mean(g), 2) if g else 0, "perdida_media_r": round(st.mean(p), 2) if p else 0}

    def decidir(self, pid: str, decision: str) -> bool:
        for p in self.propuestas:
            if p["id"] == pid:
                p["decision"] = decision
                return True
        return False

    # ---------- señales ----------
    def guardar_senales(self, fecha: date, senales: list[dict], precios: dict[str, float]) -> None:
        clave = f"senales/{fecha.isoformat()}"
        hoy = self.a.get(clave) or {}
        for s in senales:
            if not s.get("evaluable") or s["direccion"] == 0 or s["ticker"] not in precios:
                continue
            hoy[f"{s['agente']}|{s['ticker']}"] = {"agente": s["agente"], "ticker": s["ticker"], "dir": s["direccion"],
                                                    "fuerza": s["fuerza"], "precio": precios[s["ticker"]]}
        self.a.put(clave, hoy)

    def evaluar_senales(self, fechas_rueda: list[str], cierres: dict[str, dict[str, float]]) -> dict:
        """fechas_rueda: ruedas ordenadas. cierres: ticker -> {fecha: cierre}. Actualiza estadística por agente."""
        stats = self.a.get("ranking/stats") or {}
        evaluado = set(self.a.get("ranking/evaluado") or [])
        hs = config()["ranking"]["horizonte_dias"]
        for i, f in enumerate(fechas_rueda):
            for h in hs:
                if i + h >= len(fechas_rueda) or f"{f}|{h}" in evaluado:
                    continue
                destino = fechas_rueda[i + h]
                for s in (self.a.get(f"senales/{f}") or {}).values():
                    c = cierres.get(s["ticker"], {}).get(destino)
                    if not c or not s["precio"]:
                        continue
                    ret = (c / s["precio"] - 1) * 100 * s["dir"]
                    st_ag = stats.setdefault(s["agente"], {}).setdefault(str(h), {"casos": 0, "aciertos": 0, "suma_ret": 0.0})
                    st_ag["casos"] += 1
                    st_ag["aciertos"] += int(ret > 0)
                    st_ag["suma_ret"] = round(st_ag["suma_ret"] + ret, 4)
                    st_ag["suma_fuerza"] = round(st_ag.get("suma_fuerza", 0.0) + float(s.get("fuerza") or 0.6), 4)
                    # por banda de fuerza (débil / media / fuerte) para calibrar
                    from .calibracion import _sumar, banda
                    _sumar(stats[s["agente"]].setdefault("bandas", {}).setdefault(str(h), {}).setdefault(
                        banda(float(s.get("fuerza") or 0.6)), {}), ret, float(s.get("fuerza") or 0.6))
                evaluado.add(f"{f}|{h}")
        self.a.put("ranking/stats", stats)
        self.a.put("ranking/evaluado", sorted(evaluado)[-2000:])
        return stats

    def ranking(self) -> list[dict]:
        """Nivel y peso por agente según aciertos y esperanza a 10 ruedas (incentivos)."""
        cfg = config()["ranking"]
        stats = self.a.get("ranking/stats") or {}
        filas = []
        for ag, d in stats.items():
            h = d.get("10") or d.get("5") or {"casos": 0}
            if not isinstance(h, dict) or "casos" not in h:
                continue
            casos = h["casos"]
            ac = h["aciertos"] / casos * 100 if casos else 0
            esp = h["suma_ret"] / casos if casos else 0
            filas.append({"agente": ag, "casos": casos, "aciertos_pct": round(ac, 1), "esperanza_pct": round(esp, 2)})
        vistos = {f["agente"] for f in filas}
        filas += [{"agente": ag, "casos": 0, "aciertos_pct": 0.0, "esperanza_pct": 0.0} for ag in self.calibracion if ag not in vistos]
        evaluables = [f for f in filas if f["casos"] >= cfg["minimo_casos"]]
        evaluables.sort(key=lambda f: (f["esperanza_pct"], f["aciertos_pct"]), reverse=True)
        n = len(evaluables)
        historial = self.a.get("ranking/historial_niveles") or {}
        for i, f in enumerate(evaluables):
            if f["esperanza_pct"] > 0 and i < max(1, n // 3):
                nivel = "titular"
            elif f["esperanza_pct"] <= 0 or i >= n - max(1, n // 3):
                nivel = "a_prueba"
            else:
                nivel = "normal"
            # ~2 meses seguidos (8 rankings semanales) a prueba o en el banco → banco, hasta que mejore
            previos = historial.get(f["agente"], [])
            seguidos = 0
            for p in reversed(previos):
                if p not in ("a_prueba", "banco"):
                    break
                seguidos += 1
            if nivel == "a_prueba" and seguidos >= 7 and f["agente"] not in cfg["sin_banco"]:
                nivel = "banco"
            f["nivel"] = nivel
            f["peso"] = cfg["niveles"][nivel]["peso"]
        for f in filas:
            f.setdefault("nivel", "sin_datos")
            f.setdefault("peso", 1.0)
        for f in filas:
            f["calibracion"] = self.calibracion.get(f["agente"])
        # incentivo en plata: con 10+ simulaciones cerradas, quien pierde dinero no puede ser titular
        sim = (self.a.get("sim/resumen") or {}).get("por_agente", {})
        minimo = config().get("simulacion", {}).get("minimo_cerradas_ranking", 10)
        for f in filas:
            d = sim.get(f["agente"]) or {}
            f["sim_cerradas"], f["sim_ganancia"] = d.get("cerradas", 0), d.get("ganancia")
            if f["nivel"] == "titular" and f["sim_cerradas"] >= minimo and (f["sim_ganancia"] or 0) < 0:
                f["nivel"], f["peso"] = "normal", cfg["niveles"]["normal"]["peso"]
                f["motivo"] = "Pierde plata en la simulación"
        return sorted(filas, key=lambda f: f["peso"], reverse=True)

    def cerrar_ranking_semanal(self) -> list[dict]:
        filas = self.ranking()
        historial = self.a.get("ranking/historial_niveles") or {}
        for f in filas:
            historial.setdefault(f["agente"], []).append(f["nivel"])
            historial[f["agente"]] = historial[f["agente"]][-8:]
        self.pesos = {f["agente"]: f["peso"] for f in filas}
        self.a.put("ranking/historial_niveles", historial)
        self.a.put("ranking/pesos", self.pesos)
        self.a.put("ranking/tabla", filas)
        return filas

    def peso(self, agente: str) -> float:
        """Peso del voto = nivel en el ranking × calibración (si promete más de lo que acierta, vale menos)."""
        cal = (self.calibracion.get(agente) or {}).get("factor")
        return float(self.pesos.get(agente, 1.0)) * (float(cal) if cal is not None else 1.0)

    def recalibrar(self) -> dict:
        from .calibracion import calibrar
        self.calibracion = calibrar(self.a.get("ranking/stats") or {}, self.a.get("ranking/stats_historicas") or {})
        self.a.put("ranking/calibracion", self.calibracion)
        return self.calibracion

    def guardar(self) -> None:
        self.a.put("registro/propuestas", self.propuestas[:1500])
