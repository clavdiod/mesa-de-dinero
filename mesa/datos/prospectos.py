"""Ficha de cada licitación: lee el aviso de suscripción (PDF público de A3/MAE) y arma un resumen en castellano.

Los PDF están en SharePoint de A3 (mercadoabierto.sharepoint.com); con "download=1" se bajan directo.
Se lee una sola vez por documento (se guarda la ficha en KV). Sin IA: se buscan los campos que todos los avisos
traen con el mismo nombre ("Moneda", "Fecha de Vencimiento", "Amortización", "Monto mínimo de suscripción"...).
"""
from __future__ import annotations

import io
import re

HOST_DOCS = "mercadoabierto.sharepoint.com"

CAMPOS = [  # (clave, título para mostrar, patrón del rótulo en el aviso)
    ("moneda", "Moneda", r"Moneda(?: de (?:emisión|denominaci[oó]n)(?: e integraci[oó]n)?)?"),
    ("integracion", "Se paga con", r"Moneda de (?:suscripci[oó]n|integraci[oó]n)(?: e integraci[oó]n)?"),
    ("pago", "Paga en", r"Moneda de [Pp]ago(?: de los [Ss]ervicios[^:]{0,60})?"),
    ("tasa", "Tasa", r"Tasa de [Ii]nter[eé]s(?: [Aa]plicable)?"),
    ("margen", "Margen", r"Margen(?: [Aa]plicable| de [Cc]orte)?"),
    ("vencimiento", "Vencimiento", r"Fecha de [Vv]encimiento"),
    ("amortizacion", "Amortización", r"Amortizaci[oó]n(?: del [Cc]apital)?"),
    ("intereses", "Pago de intereses", r"Fechas? de [Pp]ago de [Ii]ntereses"),
    ("emision", "Emisión y liquidación", r"Fecha de [Ee]misi[oó]n y [Ll]iquidaci[oó]n"),
    ("periodo", "Período de licitación", r"Per[ií]odo de (?:[Ll]icitaci[oó]n|[Ss]ubasta)(?: [Pp][uú]blica)?"),
    ("minimo", "Monto mínimo", r"Monto [Mm][ií]nimo de [Ss]uscripci[oó]n"),
    ("precio", "Precio de emisión", r"Precio de [Ee]misi[oó]n|Precio de [Ss]uscripci[oó]n"),
    ("calificacion", "Calificación", r"Calificaci[oó]n(?: de [Rr]iesgo)?"),
    ("garantia", "Garantía", r"Entidad de [Gg]arant[ií]a|Garant[ií]a"),
]
_ROTULO = re.compile(r"(?:(?<=\s)|^)(?:[A-ZÁÉÍÓÚÑ][\wáéíóúñ/()\-]*(?:\s+(?:de|del|la|las|los|y|e|en|bajo|a|[A-ZÁÉÍÓÚÑ][\wáéíóúñ/()\-]*)){0,11})\s?:\s")


def url_descarga(u: str) -> str:
    return u + ("&" if "?" in u else "?") + "download=1"


def texto_pdf(contenido: bytes, paginas: int = 25) -> str:
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(contenido))
    t = " ".join((p.extract_text() or "") for p in r.pages[:paginas])
    return re.sub(r"\s+", " ", t.replace("­", "")).strip()


def bajar_texto(u: str) -> str | None:
    from .gratis import _S
    try:
        r = _S.get(url_descarga(u), timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        if r.content[:4] != b"%PDF":
            return None
        return texto_pdf(r.content)
    except Exception as ex:
        print(f"[prospectos] {ex}")
        return None


def _valor(texto: str, patron: str) -> str | None:
    m = re.search(rf"(?:{patron})\s?:\s", texto)
    if not m:
        return None
    resto = texto[m.end(): m.end() + 420]
    sig = _ROTULO.search(resto, 25)  # corta en el próximo "Rótulo: "
    v = resto[: sig.start()] if sig else resto
    # si es muy largo, hasta el primer punto después de 60 caracteres
    if len(v) > 260:
        p = v.find(". ", 60)
        v = v[: p + 1] if 0 < p < 300 else v[:260] + "…"
    return v.strip(" ;,") or None


def ficha(texto: str) -> dict:
    campos = {}
    for clave, _, pat in CAMPOS:
        v = _valor(texto, pat)
        if v:
            campos[clave] = v
    extra = {}
    m = re.search(r"tasa (?:nominal anual )?fija (?:del? )?(\d+(?:,\d+)?) ?%", texto, re.I)
    if m:
        extra["tasa_fija"] = m.group(1)
    for m in re.finditer(r"[Tt]asa[^.]{0,160}?\b(TAMAR|BADLAR|CER|UVA|[Dd][oó]lar [Ll]inked)\b", texto):
        ref = m.group(1).upper().replace("Ó", "O")
        if ref not in extra.get("referencias", []):
            extra.setdefault("referencias", []).append(ref)
    m = re.search(r"vencimiento a los (\d+) (?:\(\w+\) )?meses", texto, re.I)
    if m:
        extra["plazo_meses"] = int(m.group(1))
    m = re.search(r"\b([A-D]{1,3}\d?[+\-]?(?:sf)?\s?\(arg\)|[A-D]{1,3}\d?[+\-]?\.ar)", texto)
    if m:
        extra["nota"] = m.group(1)
    m = re.search(r"\b([A-ZÁÉÍÓÚ][a-záéíóúñ]+(?: [A-ZÁÉÍÓÚ][a-záéíóúñ]+){0,3} S\.G\.R\.)", texto)
    if m:
        extra["sgr"] = m.group(1).strip()
    return {"campos": campos, "extra": extra}


def resumen(ev: dict, fi: dict | None) -> str:
    """Una o dos frases para entender la licitación de un vistazo."""
    fi = fi or {"campos": {}, "extra": {}}
    ex, ca = fi.get("extra") or {}, fi.get("campos") or {}
    clase = {"ON": "Obligación negociable", "Fideicomiso": "Fideicomiso financiero", "VCP": "Valor de corto plazo"}.get(ev.get("clase"), "Emisión")
    mon = "en dólares" if "USD" in str(ev.get("moneda") or "").upper() else "en pesos" if ev.get("moneda") else ""
    partes = [f"{clase} de {ev.get('emisor') or 'la empresa'} {mon}".strip()]
    if ex.get("tasa_fija"):
        partes.append(f"tasa fija de {ex['tasa_fija']}% anual")
    elif ex.get("referencias"):
        partes.append(f"tasa variable ({' / '.join(ex['referencias'][:2])} + margen)")
    if ev.get("licita"):
        partes.append(f"en la licitación se ofrece {'el margen' if 'margen' in ev['licita'] else 'la tasa' if 'tasa' in ev['licita'] else 'el precio'}")
    if ex.get("plazo_meses"):
        partes.append(f"vence a los {ex['plazo_meses']} meses")
    elif ca.get("vencimiento"):
        partes.append(f"vence: {ca['vencimiento'][:60]}")
    if ex.get("sgr"):
        partes.append(f"garantizada por {ex['sgr']}")
    if ex.get("nota"):
        partes.append(f"calificación {ex['nota']}")
    frase = ", ".join(partes).rstrip(".") + "."
    if ev.get("hora_cierre"):
        frase += (f" Se oferta el {ev['fecha'][8:10]}/{ev['fecha'][5:7]} de {ev.get('hora_inicio')} a {ev['hora_cierre']} h por tu bróker"
                  + (f" (colocadores: {ev['colocador'][:90]})" if ev.get("colocador") else "") + ".")
    m = re.search(r"(?:U\$S|US\$|V/N\s?\$?|\$)\s?[\d.,]+", ca.get("minimo") or "")
    if m:
        frase += f" Mínimo: {m.group(0)}."
    return frase


PALABRAS_VACIAS = {"ON", "FF", "BAJO", "MEDIANO", "IMPACTO", "AMPLIADO", "CLASE", "SERIE", "PYME", "GAR", "GARANTIZADA", "VCP", "LICITACION",
                   "FACTURAS", "SA", "S.A.", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "BI", "MI", "CNV", "DE", "LA", "DEL", "Y"}


def clave_emisor(titulo: str) -> str | None:
    """'ON BAJO IMPACTO COLGAS CLASE I' -> 'COLGAS'; 'FF ... ALZ AGROCAP SERIE V-FACTURAS' -> 'AGROCAP'."""
    palabras = [w for w in re.split(r"[\s\-]+", titulo.upper()) if w and w not in PALABRAS_VACIAS and not w.isdigit() and len(w) >= 4]
    return max(palabras, key=len) if palabras else None


def documentos_de(ev: dict, docs: list[dict]) -> list[dict]:
    k = clave_emisor(ev.get("titulo") or "")
    if not k:
        return []
    out = [{"fecha": (d.get("fecha") or "")[:10], "titulo": re.sub(r"^MP\s*A3\s*-\s*(RES|ANU|ADE)\s*-\s*|\.pdf$", "", d.get("titulo") or "", flags=re.I).strip(),
            "url": d.get("url")} for d in docs if k in (d.get("titulo") or "").upper() and d.get("url")]
    return sorted(out, key=lambda d: d["fecha"], reverse=True)[:8]


def completar(evs: list[dict], docs: list[dict], fichas: dict, hoy_iso: str, dias: int = 10, max_pdfs: int = 8) -> bool:
    """Agrega a cada ON/fideicomiso cercano sus documentos, la ficha (aviso de suscripción + adendas) y el resumen."""
    from datetime import date, timedelta
    lim = (date.fromisoformat(hoy_iso) + timedelta(days=dias)).isoformat()
    bajados, cambio = 0, False
    for ev in evs:
        if ev.get("clase") not in ("ON", "Fideicomiso", "VCP", "Otra") or not (hoy_iso <= ev.get("fecha", "") <= lim):
            continue
        dd = documentos_de(ev, docs)
        ev["documentos"] = [{"fecha": d["fecha"], "titulo": d["titulo"], "url": d["url"]} for d in dd]
        base = next((d for d in dd if re.search(r"aviso de suscrip", d["titulo"], re.I)), None)
        adendas = [d for d in dd if re.search(r"adenda|complementario", d["titulo"], re.I)]
        fi = {"campos": {}, "extra": {}}
        sup = next((d for d in dd if re.search(r"suplemento", d["titulo"], re.I)), None)
        # el suplemento tiene todas las condiciones: se lee primero (si hay) y el aviso y las adendas lo corrigen
        for d in ([sup] if sup else []) + ([base] if base else []) + list(reversed(adendas)):
            f = fichas.get(d["url"])
            if f is None and bajados < max_pdfs:
                bajados += 1
                t = bajar_texto(d["url"])
                f = ficha(t) if t else {"campos": {}, "extra": {}, "sin_texto": True}
                fichas[d["url"]] = f
                cambio = True
            if f:
                fi["campos"].update(f.get("campos") or {})
                fi["extra"].update(f.get("extra") or {})
        ev["ficha"] = fi
        ev["resumen"] = resumen(ev, fi)
    return cambio
