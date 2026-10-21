"""Prueba las series macro gratis (argentinadatos)."""
import requests

out = []
for nombre, url in (("riesgo_pais", "https://api.argentinadatos.com/v1/finanzas/indices/riesgo-pais"),
                    ("inflacion", "https://api.argentinadatos.com/v1/finanzas/indices/inflacion"),
                    ("oficial", "https://api.argentinadatos.com/v1/cotizaciones/dolares/oficial"),
                    ("ccl", "https://api.argentinadatos.com/v1/cotizaciones/dolares/contadoconliqui")):
    try:
        d = requests.get(url, timeout=30).json()
        out.append(f"{nombre}: {len(d)} datos, últimos {d[-2:]}")
    except Exception as e:
        out.append(f"{nombre}: ERROR {e}")
print("::notice::" + " | ".join(out)[:3800])
