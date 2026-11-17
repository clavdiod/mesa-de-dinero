from datetime import date
from types import SimpleNamespace

from mesa.ronda import _parte_ronda

HOY = date(2026, 11, 17)


def _ctx():
    return SimpleNamespace(hora="14:05", por_simbolo={"GGAL": {}, "YPFD": {}}, extra={"clima_estado": "neutro"},
                           riesgo_pais={"valor": 612.0})


def test_sin_cambios_dice_que_no_invierte_y_por_que():
    p = _parte_ronda(_ctx(), HOY, [], [], [], [{"ticker": "GGAL", "riesgo": {"ok": True}}],
                     [{"ticker": "GGAL"}], [], 3, [{"ticker": "CEPU"}])
    assert p["nivel"] == "sin_cambios" and p["titulo"] == "✅ Ronda 14:05: sin cambios"
    assert "no invertir" in p["texto"] and "GGAL" in p["texto"] and "no aprobó" in p["texto"]
    assert "riesgo país 612" in p["texto"]


def test_atencion_si_hay_compra_o_cartera():
    p = _parte_ronda(_ctx(), HOY, [{"ticker": "TXAR"}], [], [], [], [], [], 3, [])
    assert p["nivel"] == "atencion" and "comprar TXAR" in p["texto"]
    q = _parte_ronda(_ctx(), HOY, [], [{"ticker": "🔴 VENDER CEPU", "texto": "tocó el stop"}], [], [], [], [], 3, [])
    assert q["nivel"] == "atencion" and "VENDER CEPU" in q["texto"]


def test_buen_dia_no_cuenta_como_novedad():
    p = _parte_ronda(_ctx(), HOY, [], [], [{"tipo": "buen_dia", "ticker": "☀️ Buen día", "texto": "x"}], [], [], [], 0, [])
    assert p["nivel"] == "sin_cambios" and "cupo" in p["texto"]
