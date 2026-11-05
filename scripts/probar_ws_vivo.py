from datetime import datetime, timezone
from mesa.agentes import ws_vivo
from mesa.datos import gratis
h = {"qqq": gratis.yahoo("QQQ", "10y")}
tit = [n["titulo"] for n in gratis.buscar_noticias("Wall Street Nasdaq", horas=6, max_items=3)]
r = ws_vivo.lectura(datetime.now(timezone.utc), {"IBB": "IBBD", "YPF": "YPFD (ADR YPF)", "CEPU": "CEPU (ADR CEPU)"}, h, tit)
print("::notice::" + (r["titulo"] if r else "sin lectura (NY cerrado)"))
for l in (r or {}).get("lineas", []):
    print("::notice::" + l)
print("::notice::titulares: " + " | ".join((r or {}).get("titulares", [])))
