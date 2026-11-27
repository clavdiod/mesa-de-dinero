"""27/11: con canal ntfy, todo sale por ntfy (lo sin novedad con prioridad baja) y no se usa la app de la mesa."""
from mesa.nucleo import push


class Alm(dict):
    def get(self, k, d=None):
        return super().get(k, d)

    def put(self, k, v):
        self[k] = v


def _espiar(monkeypatch, ok=True):
    enviados, web = [], []
    monkeypatch.setattr(push, "_respaldo", lambda a, t, x, p=4: enviados.append((t, p)) or ok)
    monkeypatch.setattr(push, "enviar", lambda subs: web.append(len(subs)) or {"enviadas": len(subs), "vencidas": []})
    return enviados, web


def test_canal_ntfy_manda_todo_por_ntfy(monkeypatch):
    enviados, web = _espiar(monkeypatch)
    a = Alm({"usuario/avisos": {"canal": "ntfy"}, "push/suscripciones": [{"endpoint": "https://x"}]})
    push.avisar(a, "Ronda 12:00: sin cambios", "nada nuevo", False)
    push.avisar(a, "🗳️ Comité: comprar X", "objetivo", True)
    assert enviados == [("Ronda 12:00: sin cambios", 2), ("🗳️ Comité: comprar X", 4)] and web == []


def test_canal_ntfy_si_falla_usa_la_app(monkeypatch):
    enviados, web = _espiar(monkeypatch, ok=False)
    a = Alm({"usuario/avisos": {"canal": "ntfy"}, "push/suscripciones": [{"endpoint": "https://x"}]})
    push.avisar(a, "Alerta", "texto", True)
    assert web == [1]


def test_por_defecto_van_los_dos(monkeypatch):
    enviados, web = _espiar(monkeypatch)
    a = Alm({"push/suscripciones": [{"endpoint": "https://x"}]})
    push.avisar(a, "Ronda", "sin cambios", False)
    assert enviados == [("Ronda", 2)] and web == [1]


def test_canal_app_sigue_como_antes(monkeypatch):
    enviados, web = _espiar(monkeypatch)
    a = Alm({"usuario/avisos": {"canal": "app"}, "push/suscripciones": [{"endpoint": "https://x"}]})
    push.avisar(a, "Ronda", "sin cambios", False)
    assert enviados == [] and web == [1]
