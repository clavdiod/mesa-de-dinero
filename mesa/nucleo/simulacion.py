"""Simulación en papel: "¿qué hubiera pasado si comprábamos 1.000 nominales?".

Cada oportunidad (corto / mediano) y cada propuesta del Jefe se compra en papel:
- Oportunidades: al precio de venta del momento en que aparece (compra a mercado).
- Propuestas del Jefe: orden límite en su precio de entrada; si no se da en 5 días, "no se dio".
Se cierra en el objetivo, en el stop (si el mismo día toca los dos, se asume el stop) o al vencer el plazo.
El resultado se mide en pesos, descontando comisión de compra y de venta.
Sirve para saber si las propuestas eran viables y para que el ranking premie a los agentes que ganan plata.
"""
from __future__ import annotations

from datetime import date, timedelta

from .config import config

GRUPOS_CADA_100 = {"soberanos", "ons", "letras", "bonos"}  # bonos/ONs/letras cotizan cada 100 nominales


def _cfg() -> dict:
    return {"nominales": 1000, "dias_limite": 5, **(config().get("simulacion") or {})}


def _factor(grupo: str | None) -> float:
    return 0.01 if (grupo or "") in GRUPOS_CADA_100 else 1.0


def _moneda(tk: str, t: dict) -> str:
    m = str(t.get("moneda") or "").lower()
    if "dolar" in m or "usd" in m:
        return "USD"
    if "peso" in m or "ars" in m:
        return "ARS"
    return "USD" if t.get("grupo") in GRUPOS_CADA_100 and tk[-1:] in ("D", "C") else "ARS"


def _tc(ctx, moneda: str) -> float:
    """Tipo de cambio para pasar a pesos lo que cotiza en dólares (MEP del momento de la compra)."""
    if moneda != "USD":
        return 1.0
    return float(ctx.extra.get("mep_al30") or (ctx.dolares.get("bolsa") or {}).get("venta") or 0) or 1.0


def _resultado(p: dict, salida: float) -> dict:
    """Ganancia en pesos y % sobre lo invertido, con comisión en la compra y en la venta.
    Lo que cotiza en dólares se pasa a pesos con el MEP del día de compra (mide el acierto, no el dólar)."""
    com = config()["capital"]["comision_ida_vuelta_pct"] / 2 / 100
    f, n = _factor(p.get("grupo")) * float(p.get("tc") or 1), p["nominales"]
    invertido = p["entrada"] * n * f
    bruto = (salida - p["entrada"]) * n * f
    neto = bruto - invertido * com - salida * n * f * com
    return {"ganancia": round(neto, 2), "ganancia_pct": round(neto / invertido * 100, 2) if invertido else 0.0,
            "invertido": round(invertido * (1 + com), 2)}


class Simulador:
    def __init__(self, almacen):
        self.a = almacen
        self.pos: list[dict] = almacen.get("sim/posiciones") or []
        self._firma0 = self._firma()

    def _firma(self) -> str:
        """Lo que importa guardar enseguida: qué posiciones hay y en qué estado (no el precio de cada ronda)."""
        return "|".join(f"{p['id']}:{p['estado']}" for p in self.pos)

    def _activa(self, clave: str) -> bool:
        return any(p["clave"] == clave and p["estado"] in ("pendiente", "abierta") for p in self.pos)

    def abrir(self, ops: dict, nuevas_jefe: list[dict], ctx, por_tk: dict[str, list], fecha: date, hora: str) -> int:
        """Registra en papel las oportunidades y propuestas nuevas. Devuelve cuántas se abrieron."""
        cfg, n = _cfg(), 0
        hoy = fecha.isoformat()

        def agentes(tk: str, extra: str) -> list[str]:
            return sorted({s.agente for s in por_tk.get(tk, []) if s.direccion > 0 and s.agente != extra} | {extra})

        for plazo, lista in (ops or {}).items():
            for o in lista:
                clave = f"{plazo}|{o['ticker']}|{o['setup']}"
                if self._activa(clave) or any(p["clave"] == clave and p["fecha"] == hoy for p in self.pos):
                    continue
                pl, t = o["plan"], ctx.titulo(o["ticker"]) or {}
                mon = _moneda(o["ticker"], t)
                self.pos.insert(0, {
                    "moneda": mon, "tc": _tc(ctx, mon),
                    "id": f"{hoy}|{clave}", "clave": clave, "origen": plazo, "setup": o["setup"],
                    "semaforo": o["semaforo"], "ticker": o["ticker"], "grupo": t.get("grupo"),
                    "aprobada": bool((o.get("mesa") or {}).get("aprobada")),
                    "fecha": hoy, "hora": hora, "nominales": cfg["nominales"], "entrada": pl["entrada"],
                    "objetivo": pl["objetivo"], "stop": pl["stop"], "vence": pl.get("vence"),
                    "estado": "abierta", "fecha_entrada": hoy, "ultimo": pl["entrada"],
                    "agentes": agentes(o["ticker"], f"oportunidades_{plazo}")})
                n += 1
        for e in nuevas_jefe or []:
            pl, t = e["plan"], ctx.titulo(e["ticker"]) or {}
            mon = _moneda(e["ticker"], t)
            clave = f"jefe|{e['ticker']}"
            if self._activa(clave):
                continue
            lim = (fecha + timedelta(days=cfg["dias_limite"] * 7 // 5)).isoformat()
            self.pos.insert(0, {
                "moneda": mon, "tc": _tc(ctx, mon), "id": f"{hoy}|{clave}|{e.get('id')}", "clave": clave, "origen": "jefe", "setup": "Propuesta del Jefe",
                "semaforo": "verde", "aprobada": True, "ticker": e["ticker"], "grupo": t.get("grupo"), "fecha": hoy, "hora": hora,
                "nominales": cfg["nominales"], "entrada": pl["entrada"], "objetivo": pl["objetivo"], "stop": pl["stop"],
                "vence": pl.get("vence"), "limite_hasta": lim, "estado": "pendiente",
                "agentes": agentes(e["ticker"], "jefe")})
            n += 1
        return n

    def actualizar(self, precios: dict[str, dict], fecha: date) -> None:
        hoy = fecha.isoformat()
        for p in self.pos:
            if p["estado"] not in ("pendiente", "abierta"):
                continue
            t = precios.get(p["ticker"])
            if not t or not t.get("ultimo"):
                continue
            ult = t["ultimo"]
            lo, hi = t.get("minimo") or ult, t.get("maximo") or ult
            if hoy in (p.get("fecha"), p.get("fecha_entrada")):  # el mín/máx del día pudo ser antes de comprar
                lo = hi = ult
            if p["estado"] == "pendiente":
                if lo <= p["entrada"]:
                    p.update(estado="abierta", fecha_entrada=hoy)
                    lo = hi = ult
                elif hoy > p.get("limite_hasta", hoy):
                    p.update(estado="no_se_dio", fecha_cierre=hoy)
                    continue
                else:
                    continue
            p["ultimo"] = ult
            if lo <= p["stop"]:
                cierre, salida = "stop", p["stop"]
            elif hi >= p["objetivo"]:
                cierre, salida = "objetivo", p["objetivo"]
            elif p.get("vence") and hoy >= p["vence"]:
                cierre, salida = "plazo", ult
            else:
                p.update({k + "_actual": v for k, v in _resultado(p, ult).items() if k != "invertido"})
                continue
            p.update(estado=cierre, salida=salida, fecha_cierre=hoy, **_resultado(p, salida))

    def resumen(self) -> dict:
        cerr = [p for p in self.pos if p["estado"] in ("objetivo", "stop", "plazo")]
        abiertas = [p for p in self.pos if p["estado"] == "abierta"]

        def stats(xs: list[dict]) -> dict:
            if not xs:
                return {"cerradas": 0}
            g = [p["ganancia"] for p in xs]
            return {"cerradas": len(xs), "ganadoras_pct": round(sum(1 for x in g if x > 0) / len(g) * 100, 1),
                    "ganancia": round(sum(g), 2), "promedio_pct": round(sum(p["ganancia_pct"] for p in xs) / len(xs), 2),
                    "invertido": round(sum(p["invertido"] for p in xs), 2)}

        def por(campo: str) -> dict:
            grupos: dict[str, list] = {}
            for p in cerr:
                grupos.setdefault(p.get(campo) or "—", []).append(p)
            return {k: stats(v) for k, v in grupos.items()}

        ag: dict[str, list] = {}
        for p in cerr:
            for a in p.get("agentes", []):
                ag.setdefault(a, []).append(p)
        # "aprobada" = lo que la mesa te mostró (comité + Jefe). Las de antes del comité (sin la marca) cuentan aparte.
        ok = lambda p: p.get("aprobada") or p.get("origen") == "jefe"
        seguidas = [p for p in cerr if ok(p)]
        return {"total": stats(seguidas), "todas": stats(cerr),
                "observacion": stats([p for p in cerr if not ok(p)]),
                "abiertas": sum(1 for p in abiertas if ok(p)),
                "latente": round(sum(p.get("ganancia_actual", 0) for p in abiertas if ok(p)), 2),
                "abiertas_observacion": sum(1 for p in abiertas if not ok(p)),
                "pendientes": sum(1 for p in self.pos if p["estado"] == "pendiente"),
                "no_se_dieron": sum(1 for p in self.pos if p["estado"] == "no_se_dio"),
                "por_origen": por("origen"), "por_setup": por("setup"), "por_semaforo": por("semaforo"),
                "por_agente": {k: stats(v) for k, v in ag.items()}, "nominales": _cfg()["nominales"]}

    def guardar(self, forzar: bool = True) -> None:
        """Si no hubo altas ni cierres, solo se guarda cuando `forzar` (cada 30 minutos) para cuidar escrituras."""
        if not forzar and self._firma() == self._firma0:
            return
        # se guardan todas las activas y las últimas 600 cerradas
        activas = [p for p in self.pos if p["estado"] in ("pendiente", "abierta")]
        resto = [p for p in self.pos if p["estado"] not in ("pendiente", "abierta")][:600]
        self.pos = activas + resto
        self.pos.sort(key=lambda p: (p.get("fecha_cierre") or p["fecha"], p.get("hora", "")), reverse=True)
        self.a.put("sim/posiciones", self.pos)
        self.a.put("sim/resumen", self.resumen())
