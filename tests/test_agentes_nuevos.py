from datetime import date

from mesa.agentes import analistas
from mesa.nucleo.contexto import Contexto


class Cache:
    def __init__(self, series):
        self.s = series
        self.indice = {k: 1 for k in series}

    def velas(self, tk):
        return self.s.get(tk, [])


def _velas(precios, vol=1000):
    return [{"fecha": f"2026-01-{(i % 28) + 1:02d}", "cierre": p, "maximo": p * 1.01, "minimo": p * 0.99, "volumen": vol}
            for i, p in enumerate(precios)]


def test_fuerza_relativa_premia_al_que_mas_sube_y_castiga_al_que_mas_cae():
    series, panel = {}, []
    for i in range(10):
        sube = 1 + (i - 4.5) / 100           # pendientes distintas: de -4,5% a +4,5% por cada 20 ruedas
        precios = [100 * sube ** (k / 20) for k in range(70)]
        tk = f"T{i}"
        series[tk] = _velas(precios[:-1])
        panel.append({"simbolo": tk, "ultimo": precios[-1]})
    ctx = Contexto(date(2026, 10, 21), "12:00", {"acciones": panel}, cache=Cache(series))
    out = {s.ticker: s.direccion for s in analistas.fuerza_relativa(ctx)}
    assert out.get("T9") == 1 and out.get("T0") == -1 and "T5" not in out


def test_volumen_proyectado_detecta_temprano():
    series = {"TXAR": _velas([690] * 30, vol=1000)}
    # a las 12:00 (90 de 390 minutos) ya operó 700: proyecta ~3.000, 3 veces lo normal
    panel = [{"simbolo": "TXAR", "ultimo": 712, "maximo": 714, "minimo": 690, "variacion": 3.0, "volumen": 700}]
    ctx = Contexto(date(2026, 10, 21), "12:00", {"acciones": panel}, cache=Cache(series))
    s = analistas.volumen_flujo(ctx)
    assert s and s[0].direccion == 1 and s[0].datos["vol_rel_proyectado"] > 2.5
