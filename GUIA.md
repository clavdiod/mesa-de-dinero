# Guía de puesta en marcha

Son 5 pasos. Todo se hace desde el navegador (sirve el celular). Tiempo estimado: 30-40 minutos.

## 1. Cloudflare: espacio de datos y token

1. Creá una cuenta gratis en **dash.cloudflare.com**.
2. **Storage & Databases → KV → Create** → nombre `mesa`. Copiá el **ID** del espacio → será `CF_KV_ID`.
3. Copiá tu **Account ID** (aparece en la página principal de Workers & Pages) → `CLOUDFLARE_ACCOUNT_ID`.
4. **My Profile → API Tokens → Create Token → plantilla "Edit Cloudflare Workers"** → `CLOUDFLARE_API_TOKEN`.

## 2. Secretos en GitHub

En el repo: **Settings → Secrets and variables → Actions → New repository secret**. Cargá:

| Secreto | Qué es |
|---|---|
| `IOL_USUARIO` / `IOL_CLAVE` | Tu usuario y clave de IOL (con la API habilitada) |
| `ANTHROPIC_API_KEY` | Clave de console.anthropic.com (para Noticias, Hechos, Calificadoras, Debate y Jefe) |
| `MESA_INGESTA_TOKEN` | Contraseña larga entre GitHub y Cloudflare (te la paso generada) |
| `VAPID_PUBLICA` / `VAPID_PRIVADA` | Claves de los avisos al celular (te las paso generadas) |
| `VAPID_CONTACTO` | `mailto:tu-email` |
| `EMAIL_PERMITIDO` | El email con el que vas a entrar a la web |
| `CF_KV_ID`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | Del paso 1 |
| `MESA_WORKER_URL` | Se completa en el paso 3 |
| `MESA_GITHUB_TOKEN` | Opcional, para el botón "Analizar ahora": token fine-grained de GitHub con permiso *Actions: Read and write* solo sobre este repo |

## 3. Publicar la web

1. En el repo: **Actions → deploy-web → Run workflow**.
2. Al terminar, la web queda en `https://mesa-de-dinero.<tu-subdominio>.workers.dev`. Cargá esa dirección como secreto `MESA_WORKER_URL`.

## 4. Proteger la web (Cloudflare Access)

1. En Cloudflare: **Zero Trust** (plan Free) → **Access → Applications → Add → Self-hosted**.
2. Dominio: el de tu web. Política **Allow** → *Emails* → tu email. Método de ingreso: código por email.
3. Segunda aplicación para la ruta de la mesa automática: mismo dominio con ruta `api/kv`, política **Bypass → Everyone**. (Esa ruta igual exige el `MESA_INGESTA_TOKEN`; sin él responde 401.)

Resultado: solo vos entrás a la web, y GitHub Actions puede guardar datos con su token.

## 5. Probar y arrancar

1. **Actions → configurar → Run workflow**: se conecta a IOL, descubre los nombres exactos de los paneles y muestra un ejemplo. Gasta unas 10-15 consultas.
2. **Actions → ronda → Run workflow** (forzar = true): corre una ronda completa.
3. Abrí la web, agregá tus tickers en **Mi lista**, cargá tu **capital** y tocá **Activar avisos** (en iPhone, primero agregala a la pantalla de inicio).

Desde ahí corre sola: días hábiles cada 5-10 min de 10:30 a 17:00, cierre a las 17:10, calificadoras a las 10:00, ranking los viernes y capacitación el primer día hábil del mes.

## Mes de prueba

Las primeras 4-6 semanas tomalo como prueba sin plata: mirá las propuestas, aprobá o rechazá, y dejá que el registro mida. Si la **esperanza** de la mesa (pestaña Propuestas → Registro) sale negativa, no se opera con plata hasta corregirla.
