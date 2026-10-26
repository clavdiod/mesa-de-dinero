"""23. Corresponsal: lo que pasa en el mundo y en las empresas, antes de que llegue al precio.

Lee cada 30 minutos portales y diarios del mundo y de Argentina (Reuters, Bloomberg, CNBC, BBC, Al Jazeera,
Ámbito, Cronista, Infobae, La Nación, iProUP...; Google Noticias en español e inglés) y busca dos cosas:

1) Temas del mundo que mueven precios: clima de guerra en el Golfo (sube el petróleo y el oro), la OPEP recorta,
   la Reserva Federal baja o sube tasas, aranceles, estímulo en China, sequía, Vaca Muerta, el FMI...
   Cada tema tiene su "mapa de efectos": qué papeles suben y cuáles bajan.
2) Empresas: rumores y hechos (cierra sucursales, despidos, concurso, nuevo desarrollo, inversión, adquisición).

Para no reaccionar a un solo titular, un tema necesita aparecer en al menos 2 titulares distintos (o 1 de una fuente
grande). Un rumor pesa menos que un hecho. Lleva su propia estadística por tema: si un tema no anticipa bien el
precio, se silencia solo; si acierta, pesa más.
Redes sociales (X): su lectura automática es paga, así que no se usa; los portales levantan lo importante en minutos.
"""
from __future__ import annotations

import re
from urllib.parse import quote_plus

from ..nucleo.modelos import Senal

FUENTES_RSS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
    "https://feeds.marketwatch.com/marketwatch/topstories/",
    "https://www.ambito.com/rss/pages/economia.xml",
    "https://www.ambito.com/rss/pages/finanzas.xml",
    "https://www.cronista.com/files/rss/finanzas-mercados.xml",
    "https://www.cronista.com/files/rss/economia.xml",
    "https://www.infobae.com/arc/outboundfeeds/rss/category/economia/",
    "https://www.lanacion.com.ar/arc/outboundfeeds/rss/category/economia/",
    "https://www.iproup.com/rss",
]
# búsquedas en Google Noticias (agrupa Reuters, Bloomberg, AP, FT, WSJ y diarios locales)
BUSQUEDAS_EN = ["Brazil markets real Bovespa", "oil prices Middle East", "Strait of Hormuz", "OPEC output", "Federal Reserve rates", "tariffs trade war",
                "China stimulus", "stock market today", "Reuters business"]
BUSQUEDAS_ES = ["Brasil mercados real Bovespa", "elecciones Brasil mercados", "petróleo Medio Oriente", "Wall Street hoy", "empresa cierra sucursales Argentina", "despidos empresa Argentina",
                "Vaca Muerta inversión", "nuevo desarrollo empresa argentina"]
FUENTES_GRANDES = ("reuters", "bloomberg", "cnbc", "bbc", "financial times", "wsj", "wall street journal", "ap news", "associated press",
                   "ámbito", "ambito", "cronista", "infobae", "la nación", "lanacion", "clarín", "clarin")

PETROLEO = ["YPFD", "VIST", "PAMP", "XOM", "CVX", "OXY", "PBR", "SLB"]
ORO = ["GLD", "GOLD", "NEM"]
DEFENSA = ["LMT", "RTX", "NOC"]
BRASIL = ["PBR", "VALE", "ITUB", "BBD", "NU", "XP", "STNE", "PAGS", "MELI", "EWZ", "ERJ", "SID", "GGB", "BSBR", "ABEV"]
INDICES = ["SPY", "QQQ", "DIA"]
EMERGENTES = ["EWZ", "GGAL", "BMA", "YPFD"]


def _r(p: str) -> re.Pattern:
    return re.compile(p, re.I)


# tema: (nombre, [patrones que deben aparecer TODOS], efectos {ticker: dirección}, fuerza base, explicación)
TEMAS = [
    ("tension_golfo", "Clima de guerra en Medio Oriente / el Golfo",
     [_r(r"guerra|ataque|atac|misil|bombarde|escalada|bloqueo|represalia|\bwar\b|attack|airstrike|strikes? on|missile|escalat|retaliat|drone|blockade|seiz"),
      _r(r"ir[aá]n|golfo p[eé]rsico|ormuz|hormuz|arabia saud|saudi|hut[ií]|houthi|persian gulf|red sea|mar rojo|tanker|buque petrolero|petrolero")],
     {**{t: 1 for t in PETROLEO + ORO + DEFENSA}, **{t: -1 for t in INDICES}}, 0.45,
     "Si hay riesgo de que se corte el petróleo del Golfo, sube el crudo (petroleras), sube el oro y la defensa; las bolsas se cubren."),
    ("opep_recorta", "La OPEP recorta producción",
     [_r(r"opep|opec"), _r(r"recort\w* (de )?(la )?producci|recorte de producci|production cuts?|output cuts?|cuts? (output|production)|curb (output|production)")], {t: 1 for t in PETROLEO}, 0.4,
     "Menos oferta de petróleo: sube el crudo y las petroleras."),
    ("petroleo_baja", "Baja el petróleo (más oferta o se calma el conflicto)",
     [_r(r"petr[oó]leo|crudo|brent|wti|\boil\b|opep|opec|alto el fuego|ceasefire|tregua|acuerdo de paz|peace deal"),
      _r(r"cae|caen|baja|desplom|hunde|plunge|slump|tumble|fall|drop|aument\w* (la )?producci|raise output|boost output|alto el fuego|ceasefire|tregua|acuerdo de paz|peace deal")],
     {t: -1 for t in PETROLEO}, 0.35, "Petróleo más barato: pierden las petroleras."),
    ("petroleo_sube", "Sube el petróleo",
     [_r(r"petr[oó]leo|crudo|brent|wti|\boil\b"), _r(r"sube|suben|dispara|salta|trepa|surge|jump|soar|rall|spike|climb")],
     {t: 1 for t in PETROLEO}, 0.3, "Crudo más caro: ganan las petroleras (YPF, Vista, Pampa y las de EE.UU.)."),
    ("fed_baja", "La Reserva Federal baja (o va a bajar) tasas",
     [_r(r"\bfed\b|reserva federal|federal reserve|powell"), _r(r"baja|recort|rebaj|cut|dovish|ease|lower rates")],
     {**{t: 1 for t in INDICES + EMERGENTES}, "AL30": 1, "GD30": 1}, 0.35,
     "Tasas más bajas en EE.UU.: entra plata a acciones y a emergentes como Argentina."),
    ("fed_sube", "La Reserva Federal sube tasas o se endurece",
     [_r(r"\bfed\b|reserva federal|federal reserve|powell"), _r(r"sube las tasas|subida de tasas|hike|hawkish|endurec|raise rates|higher for longer")],
     {**{t: -1 for t in INDICES + EMERGENTES}, "AL30": -1, "GD30": -1}, 0.35,
     "Tasas más altas en EE.UU.: sale plata de acciones y de emergentes."),
    ("aranceles", "Aranceles / guerra comercial",
     [_r(r"arancel|tariff|guerra comercial|trade war|aduaner")], {**{t: -1 for t in INDICES}, "BABA": -1, "FXI": -1, "AAPL": -1}, 0.3,
     "Más aranceles: golpean a las bolsas y a China."),
    ("china_estimulo", "Estímulo económico en China",
     [_r(r"china|chin[ao]s|beijing|pek[ií]n"), _r(r"est[ií]mulo|stimulus|rescate|bazooka")], {"VALE": 1, "BABA": 1, "FXI": 1, "RIO": 1}, 0.35,
     "China gasta más: suben metales y acciones chinas."),
    ("recesion_eeuu", "Miedo a recesión en EE.UU.",
     [_r(r"recesi[oó]n|recession"), _r(r"ee\.?\s?uu|estados unidos|\bu\.?s\.?\b|american|wall street")],
     {**{t: -1 for t in INDICES}, **{t: 1 for t in ORO}}, 0.3, "Con miedo a recesión bajan las bolsas y sube el oro."),
    ("chips_restriccion", "Restricciones a chips / semiconductores",
     [_r(r"chip|semiconductor|nvidia"), _r(r"restric|prohib|\bban\b|export control|controles? (a la|de) export")],
     {"NVDA": -1, "AMD": -1, "TSM": -1, "AVGO": -1}, 0.35, "Menos ventas de chips a China: pierden los fabricantes."),
    ("vaca_muerta", "Buenas noticias de Vaca Muerta / energía",
     [_r(r"vaca muerta|\brigi\b|neuqu[eé]n|argentina lng|\bypf\b"), _r(r"inversi[oó]n|descubr|r[eé]cord|aprob|inaugur|export|acuerdo|firm")],
     {"YPFD": 1, "VIST": 1, "PAMP": 1, "TGSU2": 1, "TGNO4": 1}, 0.35, "Más inversión y producción en Vaca Muerta: ganan YPF, Vista, Pampa y las transportadoras."),
    ("fmi", "Acuerdo o desembolso del FMI",
     [_r(r"\bfmi\b|\bimf\b|fondo monetario"), _r(r"desembols|acuerdo|aprob|approv|disburs|waiver|revisi[oó]n aprob")],
     {"AL30": 1, "GD30": 1, "GD35": 1, "GGAL": 1, "BMA": 1}, 0.35, "Más dólares y respaldo del FMI: suben bonos y bancos."),
    ("sequia", "Sequía / problemas en la cosecha argentina",
     [_r(r"sequ[ií]a|drought|helada|inundaci"), _r(r"campo|cosecha|soja|ma[ií]z|trigo|agro|crop|harvest")], {"CRES": -1}, 0.3,
     "Menos cosecha: menos dólares y pierde el agro."),
    ("brasil_crisis", "Brasil: cae la bolsa o se desploma el real",
     [_r(r"brasil|brazil|bovespa|ibovespa|\breal brasile|brazilian real|lula|bolsonaro"),
      _r(r"desplom|derrumb|hunde|se cae|caen|cae |p[aá]nico|crisis|plunge|slump|tumble|sell-?off|crash|sink|devalu|d[eé]ficit|fiscal|deuda p[uú]blica|record low|m[ií]nimo hist")],
     {**{t: -1 for t in BRASIL}, "TXAR": -1, "ALUA": -1}, 0.45,
     "Brasil es el principal socio comercial de Argentina: si se cae su bolsa o su moneda, pierden las empresas brasileñas (Petrobras, Vale, bancos, Nubank, MercadoLibre) y las argentinas que le venden (acero, aluminio, autos)."),
    ("brasil_alivio", "Brasil: rebota la bolsa o se fortalece el real",
     [_r(r"brasil|brazil|bovespa|ibovespa|\breal brasile|brazilian real"),
      _r(r"rebot|recuper|sube|suben|repunt|r[eé]cord|rall|rebound|recover|surge|jump|soar|ajuste fiscal|fiscal (plan|package|deal)")],
     {t: 1 for t in BRASIL}, 0.35, "Se calma Brasil: rebotan las brasileñas y MercadoLibre."),
    ("huracan_golfo", "Huracán en el Golfo de México",
     [_r(r"hurac[aá]n|hurricane|tormenta tropical|tropical storm"), _r(r"golfo de m[eé]xico|gulf of mexico|texas|louisiana|luisiana")],
     {t: 1 for t in ["XOM", "CVX", "OXY", "YPFD", "VIST"]}, 0.25, "Un huracán frena pozos y refinerías del Golfo: sube el crudo."),
]

# empresas: palabras para reconocerlas en titulares (además de las de config/emisores.yaml)
EMPRESAS_CEDEAR = {
    "AAPL": ["apple"], "MSFT": ["microsoft"], "GOOGL": ["google", "alphabet"], "AMZN": ["amazon"], "META": ["meta platforms", "facebook", "instagram"],
    "TSLA": ["tesla"], "NVDA": ["nvidia"], "AMD": ["amd"], "INTC": ["intel"], "MELI": ["mercado libre", "mercadolibre"], "KO": ["coca-cola", "coca cola"],
    "PEP": ["pepsico"], "MCD": ["mcdonald"], "WMT": ["walmart"], "DIS": ["disney"], "NFLX": ["netflix"], "BA": ["boeing"], "JPM": ["jpmorgan", "jp morgan"],
    "BAC": ["bank of america"], "C": ["citigroup", "citibank"], "GS": ["goldman sachs"], "XOM": ["exxon"], "CVX": ["chevron"], "PBR": ["petrobras"],
    "VALE": ["vale s.a", "minera vale"], "BABA": ["alibaba"], "TSM": ["tsmc", "taiwan semiconductor"], "PFE": ["pfizer"], "JNJ": ["johnson & johnson"],
    "MRNA": ["moderna"], "NKE": ["nike"], "SBUX": ["starbucks"], "UBER": ["uber"], "SPOT": ["spotify"], "PYPL": ["paypal"], "V": ["visa inc"],
    "MA": ["mastercard"], "ORCL": ["oracle"], "CRM": ["salesforce"], "ADBE": ["adobe"], "AVGO": ["broadcom"], "QCOM": ["qualcomm"], "MSTR": ["microstrategy", "strategy inc"],
    "COIN": ["coinbase"], "GLOB": ["globant"], "DESP": ["despegar"], "LMT": ["lockheed"], "RTX": ["raytheon", "rtx corp"], "NOC": ["northrop"],
    "SLB": ["schlumberger", "slb"], "OXY": ["occidental"], "NEM": ["newmont"], "GOLD": ["barrick"], "HMY": ["harmony gold"], "ARCO": ["arcos dorados"],
}
NEGATIVO = _r(r"cierra (sus |las )?sucursal|cierre de (sus )?sucursal|cierra (su |la )?planta|cierre de (la )?planta|despid|cesant|concurso preventivo|"
              r"quiebra|default|incumpl|renunci[aó] (el|la) (ceo|presidente)|investigaci[oó]n|allanamiento|multa|demanda|sanci[oó]n|suspende|"
              r"huelga|paro\b|hackeo|ciberataque|retira del mercado|recall|ca[ií]da de (las )?ventas|pérdida|perdi[oó]|layoff|bankrupt|lawsuit|"
              r"probe|fine[ds]?\b|recall|downgrade|cuts? (its |the )?(price )?target|lowers? (its |the )?(price )?target|(fell|falls|plunges?|sinks?|tumbles?) \d+%|"
              r"recorta (el |su )?precio objetivo|baja (el |su )?precio objetivo|se desploma|rebaja (la )?calificaci|profit warning|cuts? jobs|closes? stores|plant closure")
POSITIVO = _r(r"nuevo desarrollo|descubr|inversi[oó]n de|invertir[aá]|adquiere|adquisici[oó]n|compra (de|a) |acuerdo con|contrato|"
              r"(ganancias?|ventas|producci[oó]n|facturaci[oó]n) r[eé]cord|r[eé]cord de (ganancias|ventas|producci[oó]n)|"
              r"aprob|lanza|lanzamiento|expansi[oó]n|abre (nuevas|una nueva)|inaugur|dividendo|recompra|ganancia r[eé]cord|supera (las )?expectativas|"
              r"beats? (estimates|expectations)|raises? (its |the )?(price )?target|(jumps?|soars?|surges?|rallies) \d+%|sube (el |su )?precio objetivo|record (profit|revenue|sales)|approval|breakthrough|buyback|acquires?|partnership|upgrade|raises guidance")
RUMOR = _r(r"rumor|versiones|trascendi[oó]|seg[uú]n fuentes|analiza|evaluar[ií]a|podr[ií]a|reportedly|sources say|people familiar|considering|in talks")


def url_google(q: str, idioma: str = "es") -> str:
    if idioma == "en":
        return f"https://news.google.com/rss/search?q={quote_plus(q)}+when:1d&hl=en-US&gl=US&ceid=US:en"
    return f"https://news.google.com/rss/search?q={quote_plus(q)}+when:1d&hl=es-419&gl=AR&ceid=AR:es-419"


def leer(horas: int = 12) -> list[dict]:
    from ..datos import gratis
    urls = FUENTES_RSS + [url_google(q, "en") for q in BUSQUEDAS_EN] + [url_google(q, "es") for q in BUSQUEDAS_ES]
    return gratis.noticias(urls, horas=horas, max_items=2000)


def _texto(n: dict) -> str:
    return f"{n.get('titulo', '')} {n.get('resumen', '')}"


def _grande(n: dict) -> bool:
    t = f"{n.get('fuente', '')} {n.get('titulo', '')}".lower()
    return any(f in t for f in FUENTES_GRANDES)


def detectar_temas(titulares: list[dict]) -> list[dict]:
    out = []
    for clave, nombre, patrones, efectos, fuerza, explica in TEMAS:
        hits = [n for n in titulares if all(p.search(n.get("titulo") or "") for p in patrones)]  # solo el título: el resumen mete ruido
        if not hits:
            continue
        unicos = list({n["titulo"][:70].lower(): n for n in hits}.values())
        if len(unicos) < 2 and not any(_grande(n) for n in unicos):
            continue
        out.append({"tema": clave, "nombre": nombre, "explica": explica, "efectos": efectos, "n": len(unicos),
                    "fuerza": round(min(fuerza + 0.15, fuerza + 0.02 * (len(unicos) - 2)), 2),
                    "titulares": [{"titulo": n["titulo"], "link": n.get("link"), "fuente": n.get("fuente")} for n in unicos[:5]]})
    # si hay tensión en el Golfo, "sube el petróleo" queda incluido; "baja" y "sube" a la vez se anulan
    claves = {t["tema"] for t in out}
    if {"petroleo_sube", "petroleo_baja"} <= claves:
        a, b = (next(t for t in out if t["tema"] == k) for k in ("petroleo_sube", "petroleo_baja"))
        out = [t for t in out if t["tema"] != ("petroleo_baja" if a["n"] >= b["n"] else "petroleo_sube")]
    if "tension_golfo" in claves:
        out = [t for t in out if t["tema"] != "petroleo_sube"]
    return sorted(out, key=lambda t: -t["n"])


def claves_empresas(emisores: dict) -> dict[str, list[str]]:
    out = {tk: list(v) for tk, v in EMPRESAS_CEDEAR.items()}
    for tk, e in (emisores or {}).items():
        if e.get("sector") == "soberanos":
            continue
        cl = [x for x in {e.get("clave"), e.get("nombre")} if x and len(x) >= 4]
        if cl:
            out.setdefault(tk, []).extend(c.lower() for c in cl)
    return out


def detectar_empresas(titulares: list[dict], claves: dict[str, list[str]]) -> list[dict]:
    out: dict[str, dict] = {}
    for n in titulares:
        t = n.get("titulo") or ""
        tl = f" {t.lower()} "
        neg, pos = NEGATIVO.search(t), POSITIVO.search(t)
        if not (neg or pos) or (neg and pos):
            continue
        for tk, cl in claves.items():
            if any(re.search(rf"(?<![\w]){re.escape(c)}(?![\w])", tl) for c in cl):
                d = -1 if neg else 1
                rumor = bool(RUMOR.search(t))
                e = out.setdefault(tk, {"ticker": tk, "dir": 0, "rumor": rumor, "titulares": []})
                e["dir"] += d
                e["rumor"] = e["rumor"] and rumor
                e["titulares"].append({"titulo": t, "link": n.get("link"), "fuente": n.get("fuente"), "dir": d,
                                       "motivo": (neg or pos).group(0)})
    return [e for e in out.values() if e["dir"] != 0]


def marcar_novedad(temas: list[dict], conteos: dict, fecha: str) -> dict:
    """Un tema que aparece todos los días (ruido de fondo) no es noticia: lo que mueve precios es el cambio.
    Se compara la cantidad de titulares de hoy con el promedio de los días anteriores."""
    for t in temas:
        previos = [n for f, n in sorted((conteos.get(t["tema"]) or {}).items()) if f < fecha][-10:]
        base = sum(previos) / len(previos) if previos else 0
        t["base"] = round(base, 1)
        t["nuevo"] = (not previos and t["n"] >= 2) or (base > 0 and t["n"] >= 1.5 * base) or (len(previos) < 10 and base == 0)
        h = conteos.setdefault(t["tema"], {})
        h[fecha] = max(h.get(fecha, 0), t["n"])
    for k in list(conteos):
        conteos[k] = dict(sorted(conteos[k].items())[-20:])
    return conteos


def factor_tema(stats: dict, tema: str) -> float:
    """Aprende de lo que ya pasó: con 10 casos o más, si el tema no anticipó bien el precio pesa menos (o se silencia)."""
    s = (stats or {}).get(tema) or {}
    if s.get("casos", 0) < 10:
        return 1.0
    hit, ret = s["aciertos"] / s["casos"], s["suma_ret"] / s["casos"]
    if hit < 0.45 or ret < 0:
        return 0.0 if hit < 0.4 else 0.5
    return 1.3 if hit >= 0.55 and ret >= 0.5 else 1.0


def senales(temas: list[dict], empresas: list[dict], existe, stats: dict | None = None) -> list[Senal]:
    out = []
    for t in temas:
        f = factor_tema(stats, t["tema"])
        if f == 0 or t.get("nuevo") is False:  # tema de fondo que se repite todos los días: no es noticia
            continue
        tit = t["titulares"][0]["titulo"]
        for tk, d in t["efectos"].items():
            if existe(tk):
                out.append(Senal("mundo", tk, d, round(min(0.8, t["fuerza"] * f), 2),
                                 f"{t['nombre']} ({t['n']} titulares, ej.: «{tit[:110]}»). {t['explica']}",
                                 {"tema": t["tema"], "titulares": t["titulares"][:3]}))
    for e in empresas:
        if not existe(e["ticker"]):
            continue
        d = 1 if e["dir"] > 0 else -1
        f = factor_tema(stats, "empresa_rumor" if e["rumor"] else "empresa_hecho")
        if f == 0:
            continue
        base = 0.25 if e["rumor"] else 0.4
        ej = e["titulares"][0]
        out.append(Senal("mundo", e["ticker"], d, round(min(0.7, (base + 0.05 * (len(e["titulares"]) - 1)) * f), 2),
                         f"{'Rumor' if e['rumor'] else 'Noticia'} de la empresa: «{ej['titulo'][:140]}» ({ej['motivo']}).",
                         {"tema": "empresa_rumor" if e["rumor"] else "empresa_hecho", "titulares": e["titulares"][:3]}))
    # una señal por ticker: si dos temas chocan, se suman
    por: dict[str, Senal] = {}
    for s in out:
        p = por.get(s.ticker)
        if not p:
            por[s.ticker] = s
            continue
        neto = p.direccion * p.fuerza + s.direccion * s.fuerza
        if abs(neto) < 0.1:
            por.pop(s.ticker)
            continue
        por[s.ticker] = Senal("mundo", s.ticker, 1 if neto > 0 else -1, round(min(0.8, abs(neto)), 2), p.texto + " " + s.texto,
                              {"tema": p.datos.get("tema"), "temas": [p.datos.get("tema"), s.datos.get("tema")],
                               "titulares": (p.datos.get("titulares") or [])[:2] + (s.datos.get("titulares") or [])[:1]})
    return list(por.values())


def alertas_radar(temas: list[dict], empresas: list[dict], existe) -> list[dict]:
    out = []
    for t in temas:
        if t["n"] >= 3 and t.get("nuevo") is not False:
            sube = [tk for tk, d in t["efectos"].items() if d > 0 and existe(tk)][:6]
            baja = [tk for tk, d in t["efectos"].items() if d < 0 and existe(tk)][:4]
            out.append({"tipo": "mundo", "tipos": ["mundo"], "ticker": t["nombre"].upper()[:40], "grupo": "macro", "valor": t["n"],
                        "severidad": "alta" if t["n"] >= 6 else "media",
                        "texto": f"🌍 {t['nombre']} ({t['n']} titulares). {t['explica']}"
                                 + (f" A favor: {', '.join(sube)}." if sube else "") + (f" En contra: {', '.join(baja)}." if baja else "")})
    for e in empresas:
        if existe(e["ticker"]) and not e["rumor"] and abs(e["dir"]) >= 1:
            out.append({"tipo": "mundo", "tipos": ["mundo"], "ticker": e["ticker"], "grupo": "acciones", "valor": e["dir"], "severidad": "media",
                        "texto": f"📰 {e['ticker']}: «{e['titulares'][0]['titulo'][:140]}»."})
    return out


# ---------- estadística propia por tema (aprende sola) ----------
def anotar(log: list[dict], sens: list[Senal], precio, fecha: str) -> bool:
    """Una anotación por tema, ticker y día, con el precio del momento. Devuelve si agregó algo."""
    ya = {(x["fecha"], x["tema"], x["ticker"]) for x in log}
    nuevo = False
    for s in sens:
        for tema in s.datos.get("temas") or [s.datos.get("tema")]:
            p = precio(s.ticker)
            if tema and p and (fecha, tema, s.ticker) not in ya:
                log.append({"fecha": fecha, "tema": tema, "ticker": s.ticker, "dir": s.direccion, "precio": p})
                ya.add((fecha, tema, s.ticker))
                nuevo = True
    return nuevo


def evaluar(log: list[dict], stats: dict, precio, hoy: str, dias: int = 7) -> tuple[list[dict], dict]:
    """Las anotaciones de hace 7 días corridos (~5 ruedas) se cierran: ¿el precio fue para donde dijo el tema?"""
    from datetime import date
    from ..nucleo.calibracion import _sumar
    quedan = []
    for x in log:
        if (date.fromisoformat(hoy) - date.fromisoformat(x["fecha"])).days < dias:
            quedan.append(x)
            continue
        p = precio(x["ticker"])
        if p and x.get("precio"):
            _sumar(stats.setdefault(x["tema"], {}), (p / x["precio"] - 1) * 100 * x["dir"], 0.5)
    return quedan, stats


# ---------- noticias de un papel puntual (para el debate) ----------
def nombre_yahoo(simbolo_us: str) -> str | None:
    """Nombre de la empresa en Yahoo (gratis), para buscar sus noticias. Ej.: IREN -> 'IREN Limited'."""
    from ..datos.gratis import _S, _UA_JSON
    try:
        r = _S.get("https://query2.finance.yahoo.com/v1/finance/search", params={"q": simbolo_us, "quotesCount": 3, "newsCount": 0},
                   headers=_UA_JSON, timeout=15).json()
        for q in r.get("quotes") or []:
            if (q.get("symbol") or "").upper() == simbolo_us.upper():
                return q.get("longname") or q.get("shortname")
    except Exception as ex:
        print(f"[mundo] nombre {simbolo_us}: {ex}")
    return None


def _limpiar_nombre(n: str) -> str:
    return re.sub(r",?\s+(inc\.?|corp(oration)?\.?|ltd\.?|limited|plc|s\.a\.?|holdings?|co\.?|group|n\.v\.?|class [a-c])\b.*$", "", n, flags=re.I).strip() or n


def noticias_papel(ticker: str, nombre: str | None, local: bool) -> dict:
    """Busca titulares de los últimos 3 días del papel y los clasifica (buenos / malos / sin impacto claro)."""
    from ..datos import gratis
    base = _limpiar_nombre(nombre) if nombre else ticker
    if local:
        urls = [url_google(f'"{base}"', "es").replace("when:1d", "when:3d")]
    else:
        urls = [url_google(f'"{base}" OR "{ticker} stock"', "en").replace("when:1d", "when:3d"),
                url_google(f'"{base}"', "es").replace("when:1d", "when:3d")]
    tit = gratis.noticias(urls, horas=72, max_items=25)
    clave = base.lower().split()[0] if base else ticker.lower()
    tit = [n for n in tit if clave in n["titulo"].lower() or ticker.lower() in n["titulo"].lower()]
    clas = []
    for n in tit[:12]:
        t = n["titulo"]
        neg, pos = NEGATIVO.search(t), POSITIVO.search(t)
        d = 0 if (neg and pos) or not (neg or pos) else (-1 if neg else 1)
        clas.append({"titulo": t, "link": n.get("link"), "fuente": n.get("fuente"), "fecha": n.get("fecha"), "dir": d,
                     "rumor": bool(RUMOR.search(t)), "motivo": (neg or pos).group(0) if d else None})
    return {"nombre": base, "titulares": clas}


def senal_papel(ticker: str, info: dict, stats: dict | None = None) -> Senal:
    tits = info.get("titulares") or []
    con = [t for t in tits if t["dir"]]
    neto = sum(t["dir"] * (0.5 if t["rumor"] else 1) for t in con)
    nombre = info.get("nombre") or ticker
    if not tits:
        return Senal("mundo", ticker, 0, 0.0, f"Busqué noticias de {nombre} de los últimos 3 días: no encontré nada. Sin novedades que muevan el precio.",
                     {"tema": "papel", "titulares": []}, evaluable=False)
    if abs(neto) < 1:
        ej = "; ".join(f"«{t['titulo'][:90]}»" for t in tits[:2])
        return Senal("mundo", ticker, 0, 0.0, f"Noticias de {nombre} en los últimos 3 días ({len(tits)}), sin impacto claro: {ej}.",
                     {"tema": "papel", "titulares": tits[:4]}, evaluable=False)
    d = 1 if neto > 0 else -1
    principales = [t for t in con if t["dir"] == d]
    f = factor_tema(stats, "empresa_rumor" if all(t["rumor"] for t in principales) else "empresa_hecho") or 0.5
    fuerza = round(min(0.6, (0.25 + 0.08 * (abs(neto) - 1)) * f), 2)
    ej = principales[0]
    return Senal("mundo", ticker, d, fuerza,
                 f"Noticias de {nombre} ({len(tits)} en 3 días, {len(principales)} {'buenas' if d > 0 else 'malas'}): «{ej['titulo'][:130]}»"
                 + (" (rumor)" if ej["rumor"] else "") + ".",
                 {"tema": "empresa_rumor" if all(t["rumor"] for t in principales) else "empresa_hecho", "titulares": tits[:4]})
