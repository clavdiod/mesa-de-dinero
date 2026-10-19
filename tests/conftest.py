import math
import random
from datetime import date, timedelta

import pytest


def serie(n=260, inicio=1000.0, semilla=1, tendencia=0.0005, vol=0.018, hasta=date(2026, 10, 16)):
    random.seed(semilla)
    velas, p = [], inicio
    d = hasta - timedelta(days=int(n * 1.45))
    while len(velas) < n:
        d += timedelta(days=1)
        if d.weekday() >= 5:
            continue
        r = random.gauss(tendencia, vol) + 0.01 * math.sin(len(velas) / 9)
        ap = p
        p = max(1.0, p * (1 + r))
        velas.append({"fecha": d.isoformat(), "apertura": ap, "maximo": max(ap, p) * 1.006,
                      "minimo": min(ap, p) * 0.994, "cierre": p, "volumen": random.randint(50000, 150000)})
    return velas


@pytest.fixture
def almacen(tmp_path, monkeypatch):
    monkeypatch.delenv("MESA_WORKER_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("MESA_DATOS_LOCAL", str(tmp_path / "datos"))
    from mesa.nucleo.almacen import AlmacenLocal
    return AlmacenLocal(tmp_path / "datos")
