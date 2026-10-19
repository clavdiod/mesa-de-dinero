# Mesa de dinero

Equipo de 13 agentes que sigue el mercado argentino en horario de rueda y propone operaciones para que **vos** decidas. La mesa **nunca envía órdenes**: propone, vos aprobás o rechazás en tu web, y la orden la cargás vos en tu broker.

Este repo es público y tiene **solo el código**. Tu cartera, Mi lista, el registro, el caché de históricos y el contador de IOL viven privados en Cloudflare (KV), detrás de Cloudflare Access.

## Los agentes

| # | Agente | Qué hace | Cómo |
|---|---|---|---|
| 1 | Acciones | Subas/bajas con volumen anormal, arriba/abajo de su media | reglas |
| 2 | CEDEARs | Dólar implícito de cada CEDEAR contra la mediana: baratos y caros | reglas |
| 3 | ONs | TIR con los flujos del prospecto, contra el resto de las ONs | reglas |
| 4 | Soberanos | MEP y CCL implícitos, canje, brecha GD vs AL, riesgo país | reglas |
| 5 | Pesos y tasas | Caución corta | reglas |
| 6 | Técnico | Quiebres de máximos/mínimos, RSI, medias, soportes | reglas (se capacita) |
| 7 | Macro / dólar | Clima de mercado: riesgo país, brecha, reservas | reglas |
| 8 | Noticias | Titulares que mueven activos concretos | IA (solo si hay titulares nuevos) |
| 9 | Historiador | Gráficos parecidos en la historia y qué pasó después; soportes | reglas (se capacita) |
| 10 | Hechos del emisor | Renuncias, balances, juicios, dividendos: un hecho grave congela compras | IA, 1 búsqueda por emisor por día |
| 11 | Calificadoras | Cambios de nota/perspectiva de Moody's, S&P, Fitch, FIX, Moody's Local | IA, 1 vez por día |
| 12 | Riesgo | Arma entrada/stop/objetivo, mide R neto de comisiones, liquidez, sector, clima, calendario; puede vetar | reglas |
| 13 | Jefe | Lee el debate alcista/bajista y elige hasta 3 propuestas por día (o ninguna) | IA |

## Reglas que siempre se cumplen

- **Cupo de IOL (25.000 consultas/mes):** cada consulta se cuenta. Paneles completos (no ticker por ticker), puntas solo de Mi lista y posiciones abiertas, frecuencia 5 min en la primera y última hora y 10 min al mediodía. Al 80% la mesa baja la frecuencia sola; al 95% solo corre el cierre.
- **Caché primero:** un histórico ya guardado nunca se vuelve a pedir. Las velas diarias se arman gratis con el panel del cierre. Solo se pide lo que falta.
- **Riesgo:** 1R = 1% del capital (editable), máximo 3 propuestas por día, tope de pérdida diaria (2R) y semanal (4R), máximo 2 por sector, salida por tiempo a las 10 ruedas, clima malo → medio tamaño, riesgo país > 670 → no bancos ni soberanos.
- **Medición:** toda propuesta se sigue en prueba aunque la rechaces, en R neto. Ranking semanal por agente (aciertos y esperanza): titular (vota doble), normal, a prueba (vota la mitad), banco (no vota tras ~2 meses abajo). Capacitación mensual con validación fuera de muestra y tu aprobación.

## Puesta en marcha

Ver **[GUIA.md](GUIA.md)** (paso a paso desde el celular).

## Desarrollo

```bash
pip install -r requirements.txt
python -m pytest -q                      # pruebas
python -m mesa.ronda --simular --forzar  # ronda completa con datos de prueba, sin IOL ni IA
```
