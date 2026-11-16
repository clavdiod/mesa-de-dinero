"""16/11: ¿qué expone tablero.bymaeduca.com.ar? HTML, scripts y posibles endpoints de datos."""
import re
from mesa.datos.gratis import _S
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)", "Accept": "text/html,application/json"}
base = "https://tablero.bymaeduca.com.ar"
try:
    r = _S.get(base, headers=H, timeout=30)
    html = r.text
    print(f"::notice::{r.status_code} {len(html)} bytes · título: {re.findall(r'<title>(.*?)</title>', html)[:1]}")
    srcs = re.findall(r'src="([^"]+\\.js[^"]*)"', html)
    print("::notice::scripts: " + " | ".join(srcs[:10]))
    urls = set()
    for s in srcs[:6]:
        u = s if s.startswith("http") else base + "/" + s.lstrip("/")
        js = _S.get(u, headers=H, timeout=30).text
        urls |= set(re.findall(r'https?://[a-zA-Z0-9./_\-]+(?:api|data|historic|serie|cotiz)[a-zA-Z0-9./_\-?=&]*', js))
        urls |= set("REL:" + x for x in re.findall(r'["\'](/api/[a-zA-Z0-9/_\-]+)', js))
    print("::notice::endpoints: " + " | ".join(sorted(urls)[:40]))
    print("::notice::texto: " + re.sub(r"<[^>]+>", " ", html)[:1500].replace("\n", " "))
except Exception as ex:
    print(f"::notice::ERR {ex}")
