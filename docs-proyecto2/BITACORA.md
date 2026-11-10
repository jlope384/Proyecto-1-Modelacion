# Bitácora del Proyecto 2

Registro de lo hecho sobre el código del Proyecto 1, para retomar sin releer el chat. Branch: `proyecto-2` (sale de `main` en `bcc1540`; `main` no se tocó). Plan seguido: `PLAN_IMPLEMENTACION.md`. Instrucciones de origen: `02_instrucciones_reutilizar_codigo.md`.

**Estado: Fases 0–9 del documento 02 terminadas y UI nueva (handoff de diseño) conectada a la API. Sigue la Fase 10 (README, informe, presentación).**

Cómo ejecutar: desde `backend/`, `.venv/bin/python -m casino.piso` (autochequeo) y `.venv/bin/python app.py` (API en :5000); `cd frontend && npm run dev` (:5173). Los scripts de `src/` se corren desde la raíz. Dependencias de análisis en `requirements.txt` de la raíz (Flask y matplotlib).

## Fase 0 — Línea base (commit `línea base P1`)

- Se descartaron los cambios sin commitear de `main` (`README.md` y el guion de presentación de `Modelos.jsx`), por decisión del usuario.
- Se trabaja en una branch del mismo repo, no en un repo copiado.
- `linea_base_p1.json`: `simular_dia(horas=24, semilla=1)` con el código de P1 → 755 llegadas, 680 atendidos, 75 abandonos, ingreso 108,786.44. Sin las series largas (`esperas_min` y series por hora).

## Fase 1 — Borrar lo que no se usa

- Borrados `docker-compose.yml`, los dos `Dockerfile`, los dos `.dockerignore` y `frontend/nginx.conf`.
- `gunicorn` fuera de `backend/requirements.txt` (solo lo usaba Docker). Queda `Flask==3.0.3`.

## Fase 2 — Quitar carreras y póker

- Backend: borrados `carreras.py` y `poker.py`; limpiados `simulacion.py` (`JUEGOS` queda con 4 juegos, sin `m_cuotas`), `validacion.py` y `app.py` (sin rutas `/api/carreras/*` ni `/api/poker/*`). Se conservó `comparar_estrategias_blackjack`.
- Frontend: borrados `Carreras.jsx` y `Poker.jsx`; limpiados `App.jsx`, `Tabs.jsx`, `Simulacion.jsx`, `Modelos.jsx` (secciones 5 y 6) y `App.css` (bloques `.cr-*` y `.pk-*`). `Carta.jsx` se queda (Blackjack). En `Simulacion.jsx` también se quitó el aviso de "corrida lenta", que solo podían disparar esos dos juegos.
- `backend/casino/__init__.py` no existe (lo ignora `.gitignore`; `casino` es namespace package), así que el paso del documento 02 sobre ese archivo no aplica.
- Verificado: autochequeo OK, imports OK, `npm run build` limpio, rutas restantes responden 200 y las borradas 404.
- **Pendiente:** `README.md` todavía describe P1 (carreras, póker). Tiene una nota arriba; se reescribe en la Fase 10. No se hizo el rediseño de UI (`03_instrucciones_ui.md`), ni se cambió el prefijo "Q" de `Piso.jsx`.

## Fase 3 — Parámetros nuevos

- `llegadas.generar(..., tasa_por_hora=None, factor=1.0)`: la tasa efectiva es `tasa_por_hora[h] * factor`; `lambda_max` se calcula dentro.
- `piso.simular_dia(..., factor_llegadas=1.0, tasa_por_hora=None, paciencia_media_min=None)`; `ValueError` si factor o paciencia ≤ 0. La salida añade `factor_llegadas` y `paciencia_media_min`, y `tasa_por_hora` es la efectiva.
- `/api/piso` acepta `factor_llegadas` y `paciencia_media_min` (400 si son inválidos).
- No se parametrizaron bankroll ni estadía (punto opcional, sin uso todavía).
- **Punto de control cumplido:** con los valores por defecto el resultado es idéntico a `linea_base_p1.json` (0 claves distintas), con ambos métodos del generador.
- Sensibilidad, promedio de 8 semillas (1–8), 24 h:

| Cambio | Llegadas | P(abandono) |
|---|---|---|
| Base | 795 | 10.4% |
| `factor_llegadas=1.2` | 959 | 15.3% |
| `paciencia_media_min=4` | 795 | 10.8% |
| `paciencia_media_min=16` | 795 | 9.6% |

- **Hallazgos para el GA:** (1) el abandono casi no responde a la paciencia, lo domina la capacidad; (2) la configuración base ya está en ~10.4%, sobre el límite de 10% de la restricción; (3) una sola semilla no sirve para ver efectos (con semilla 1, paciencia 4 dio *menos* abandono): siempre promediar réplicas.

## Fase 4 — Hold de cada juego

Detalle y snippets en `hold_juegos.md`.

- **Dados:** todas las apuestas de P1 eran justas (EV 0), no solo `par_impar`. Se añadió la apuesta `"field"` (gana 2,3,4,9,10,11,12; 1:1, y 2:1 en 2 y 12) y el piso la usa: `_APUESTA_DADOS = ("field", None)`. Ventaja 1/18 = 5.56%. Las apuestas viejas siguen en la pestaña Dados.
- **Tragamonedas:** `PAGOS_TRIO` `[2, 3, 8, 50, 300]` → `[2, 3, 7, 40, 216]`. Ventaja 4.475% → 7.325% (Nevada sept. 2021: 7.32%). Afecta también a la pestaña interactiva.
- **Ruleta:** sin cambios, 2.70% (europea).
- **Blackjack:** medido, 200,000 manos, semilla 2024: hold 0.92%, IC 95% [0.48%, 1.37%].
- `_demo()` de `piso.py` ahora verifica los retornos teóricos de dados y tragamonedas y que `ingreso_teorico_por_juego` sea > 0 (esa clave no incluye blackjack).
- `linea_base_p2.json`: nueva referencia (semilla 1 → 755 llegadas, 695 atendidos, 60 abandonos, ingreso 88,102). Sustituye a la de P1 a partir de aquí.
- Hold empírico del piso (10 días): tragamonedas 7.14%, ruleta 1.77%, dados 6.07%, blackjack 0.39%.
- **Hallazgos para el GA:** (1) blackjack y ruleta dejan muy poco por apuesta frente a tragamonedas y dados; el GA tenderá a quitarles mesas, y en Nevada son los juegos con más win por unidad, así que la calibración (Fase 6) tendrá que revisar apuestas, ritmo de juego o reglas; (2) el ingreso diario es muy ruidoso (con semilla 1 la ruleta perdió 1,221 ese día; el ingreso total va de ~88,000 a ~160,000 según la semilla), lo que confirma la necesidad de réplicas y números aleatorios comunes en el fitness; (3) el win % de mesas de Nevada es sobre el drop y no se compara con la ventaja por apuesta: solo tragamonedas es comparable.

## Fase 5 y 5A — Lectores de datos

Detalle, etiquetas y comandos en `datos/README.md`. Scripts en `src/datos/` (solo biblioteca estándar + `pdftotext`).

- **Estructura:** `datos/crudos/{nevada,gkl}/`, `datos/procesados/`, `src/datos/`.
- **Nevada:** `descargar_nevada.py` bajó 2023-01 a 2024-12 (24 meses) y 2021-09. Los PDF no se versionan (`.gitignore`), se regeneran con el script. Desde 2025 el sitio redirige a `www.gaming.nv.gov/siteassets/...` y varios meses dan 404, por eso se usó 2023-2024.
- **`nevada_a_csv.py`:** el script del documento 02 no funcionaba tal cual: (1) con `pdftotext -layout` las columnas salen revueltas; se cambió a `-raw`, que deja cada juego en una línea con sus 15 números; (2) el bloque estatal está en la página 4, no en la 1; se leen las páginas 1 a 6.
- **Punto de control 5A cumplido:** septiembre 2021 reproduce exactamente la tabla de verificación (47.69 / 114.89 / 83.81 / 6.37 miles por unidad al mes; mezcla 67.4%). 1,797 filas, 24 juegos por mes (Pai Gow falta en 2023-04 por traer 14 números; no se usa).
- **`nevada_referencia.py`:** `nevada_referencia.csv` con calibración = 2023 y validación = 2024, para blackjack, ruleta, dados y tragamonedas: mezcla de ingreso (sobre el total y sobre los 4 juegos), win por unidad al mes, unidades por local y win percent, con la desviación mensual. Cuadra con la fila "12 meses" del informe de diciembre 2023.

| Métrica (2023 → 2024) | Blackjack | Ruleta | Dados | Tragamonedas |
|---|---|---|---|---|
| Win por unidad al mes (miles USD) | 55.3 → 55.4 | 88.9 → 84.1 | 122.3 → 114.8 | 6.87 → 6.89 |
| Mezcla dentro de los 4 juegos | 10.6% → 10.5% | 3.7% → 3.5% | 3.7% → 3.5% | 82.0% → 82.5% |
| Unidades por local | 17.8 → 18.1 | 4.4 → 4.5 | 3.1 → 3.3 | 401 → 407 |
| Win % | 14.8 → 14.3 (drop) | 19.8 → 17.3 (drop) | 16.7 → 16.3 (drop) | 7.17 → 7.21 |

- **Grand Korea Leisure (`gkl_a_csv.py`):** confirmado CP949, 11 columnas, las 5 de edad son conteos enteros (sin vacíos ni negativos), 3 sucursales (Coex, Dragon City, Lotte Busan), 2015-01-01 a 2026-06-23, sin duplicados. Visitantes diarios = suma de las columnas de edad. Se excluyen **2020-2022**, no solo 2020-2021: 2022 promedió 1,502 visitantes/día, 35% de 2019. Promedios diarios (3 sucursales): 2023 = 2,331, 2024 = 2,702.
- Factores por día de la semana (3 sucursales, 2023 → 2024): lun 0.94/0.94, mar 0.87/0.93, mié 0.85/0.88, jue 0.86/0.87, vie 0.97/0.98, sáb 1.30/1.23, dom 1.21/1.16. Patrón estable: sirve para calibrar con 2023 y validar con 2024.
- **Kangwon Land:** la página de data.go.kr da 404; se omite, como permite el documento 02.
- **Hallazgos para la Fase 6:** (1) por unidad, dados > ruleta > blackjack ≫ tragamonedas en Nevada, al revés de lo que hoy produce el simulador (ver Fase 4): la calibración debe acercar el win por mesa; (2) el 82% del win de los 4 juegos es de tragamonedas, con ~400 máquinas por cada ~26 mesas por local; (3) GKL no tiene horas: el perfil horario sigue siendo supuesto, solo se calibra el nivel diario y el factor por día.

## Fase 6 — Calibración y validación

Detalle en `calibracion.md`. Script `src/calibracion/calibrar.py`, escenario compartido `src/modelo/escenario.py`, salidas en `resultados/calibracion/`.

- Piso base = Nevada 2023 unidades por local / 4 → 100 máquinas, 4 blackjack, 1 ruleta, 1 dados; área 142 (máquina 1, BJ 6, ruleta 8, dados 10, estimación). Demanda proporcional a los puestos del piso base (supuesto).
- Llegadas = GKL 2023 (776.9 visitantes/día por sucursal) × 3 sesiones por visitante (supuesto) → 2,331 sesiones/día; abandono base 9.2%.
- **Hallazgo:** las "unidades por local" de Nevada no son un mismo piso (máquinas en ~310 locales, mesas en ~100). Se agregó `unidades_estatales` a `nevada_referencia.csv` y la mezcla se compara como *mezcla implícita* (win por unidad simulado × unidades estatales).
- Único parámetro calibrado: `escala_bankroll_mesas` = 18.01, contra la mezcla de tragamonedas 2023 (82.03%).
- Validación 2024: hold de tragamonedas +3.5%, factores por día MAE 0.037, mezcla de tragamonedas −2.1%; **reparto entre mesas mal reproducido** (dados +99%, ruleta +56%, blackjack −31% en win por unidad). Se guarda una calibración alternativa por juego para sensibilidad.
- Motor: `simular_dia` acepta `escala_bankroll_mesas` (número o dict) y `flujos_por_cliente` (números aleatorios comunes reales; varianza de la diferencia entre pisos ~11× menor). Con valores por defecto, idéntico a `linea_base_p2.json`; autochequeo OK.

## Fase 7 — Algoritmo genético

Detalle en `genetico.md`. Script `src/optimizacion/genetico.py`, pruebas `tests/test_genetico.py` (4 OK), salidas en `resultados/optimizacion/` y `resultados/optimizacion_escala_por_juego/`.

- GA a mano: cromosoma de enteros, área constante con reparación, torneo 3, cruce de un punto, mutación ±1, elitismo 2, fitness con penalización por abandono > 10%, CRN + caché + re-evaluación con 30 semillas nuevas.
- **Resultado:** base 100/4/1/1 → mejorada **84/5/1/2**: ingreso +5.5% (IC95 +11.6k a +91.2k), abandono 8.78% → 9.36%. Área 142 comprobada por código.
- Con la calibración por juego el GA llega al **mismo reparto**, mejora +4.7% pero no significativa con 30 réplicas.

## Fase 8 — Experimentos

Detalle en `experimentos.md`. Script `src/experimentos/correr.py`, salidas en `resultados/experimentos/`.

- Base 100/4/1/1 contra mejorada 84/5/1/2 con las mismas semillas (CRN, `flujos_por_cliente=True`): principal y calibración por juego con 100 réplicas; llegadas ×0.8/1.2/1.4 y paciencia 4/12 min con 30. 700 días simulados, semillas desde 7001.
- **Resultado principal:** +5.8 % de ingreso, IC95 [+3.4, +8.2] %, abandono 9.11 % → 9.67 %. Con calibración por juego +3.3 %, IC95 [+0.1, +6.4] %: significativa con 100 réplicas.
- Con llegadas +20 % y +40 % ninguno de los dos pisos cumple el 10 % de abandono; con paciencia 4 min la mejorada queda en 10.13 %.
- Consistencia: conservación en las 700 réplicas, Little con error máximo 1.85 %.
- `comparacion_real.json`: tabla Real (2024) / Base / Mejorada con MAE, y filas estimadas (abandono, espera, ingreso) sin referencia real.
- Cada réplica se guarda al terminar en `replicas.jsonl`; el script retoma lo que falta.

## Fase 9 — Gráficas

- `src/visualizacion/graficas.py` (matplotlib, solo lee `resultados/`) → 6 PNG en `resultados/graficas/`: llegadas por día, comparación real, convergencia del GA, base contra mejorada, sensibilidad y diferencias pareadas.

## UI nueva (handoff de diseño `casino-panel-handoff`)

- Se borró la UI vieja de P1 (pestañas jugables, saldo, `App.css`, `components/`, `hooks/`, `utils/`) y se reescribió `frontend/src` con el diseño del handoff (`styles/panel.css` + `styles/extra.css`, imágenes en `src/assets/`), en React + Vite + Chart.js.
- Pestañas y conexión con Python:

| Pestaña | Ruta | Parte del proyecto |
|---|---|---|
| El piso | `POST /api/piso` | `casino/piso.py` con los parámetros calibrados (`escenario.argumentos`) |
| Armar piso | `GET /api/config`, `POST /api/piso` | Área por unidad del modelo, win por unidad de la Fase 8; botón que simula la configuración |
| Datos reales | `GET /api/datos/referencia` | `comparacion_real.json` (Fase 8) y `llegadas_dia_semana.csv` (Fase 6) |
| Optimización | `GET /api/optimizacion/resultado`, `POST /api/optimizacion/correr`, `GET /api/optimizacion/estado` | `resultado.json` e `historial.csv` (Fase 7); la versión mini lanza `genetico.py --prueba` (~30 s) |
| Escenarios | `GET /api/escenarios` | `escenarios.json` (Fase 8) |
| Validación | `GET /api/validacion` | `validacion.validar_lcg`, `validar_replicado` por juego (100 semillas), Little y conservación (Fase 8), hold teórico contra simulado |
| Fuentes | — | Estático: datasets, supuestos, uso de IA y reproducción |

- `backend/app.py` se reescribió: solo quedan las rutas de arriba y `/api/salud`. Las rutas de juegos interactivos y el saldo se quitaron. Cada GET devuelve 404 con el comando que genera el archivo si falta.
- Hold teórico contra simulado: prueba z sobre ingreso − h₀·apostado por día (100 días del piso base); los cuatro juegos pasan con |z| ≤ 1.96.
- `casino/piso.py` agrega `abandonos_por_hora` a la salida (no consume números aleatorios; la línea base no cambia).
- `backend/casino/__init__.py` (ignorado por git) todavía importaba `carreras`; se quitó esa línea porque rompía `from casino import ...`.
- Verificado: `npm run build` limpio, API probada con el cliente de Flask y a través del proxy de Vite, versión mini del GA de punta a punta, y capturas de las 7 pestañas con datos reales de la API.
- Pendiente de la UI: confirmar el derecho de uso de las fotos de `src/assets/` (eran capturas de referencia del handoff) y completar en Fuentes quién revisó lo generado con IA.

## Sensibilidad al área por unidad

- `genetico.py`: nuevo `--area blackjack=…,ruleta=…,dados=…` (enteros) y caché en disco por simulación (`cache_simulaciones.jsonl`) para retomar corridas. Con áreas por defecto el resultado de `--prueba` es idéntico al anterior; las 4 pruebas siguen OK.
- GA completo con mesas −25 % (5/6/8) → **76/6/2/2** y +25 % (8/10/13) → **95/3/1/2**. Salidas en `resultados/optimizacion_area_menos25/` y `resultados/optimizacion_area_mas25/`.
- `src/experimentos/sensibilidad_area.py`: compara cada reparto con la base con las 100 semillas de la Fase 8 (reutiliza réplicas) → +7.6 %, +5.8 % y +3.3 %, las tres significativas. Con mesas más grandes el abandono queda en 10.13 % y 84/5/1/2 no cabe.
- Conclusión: la segunda mesa de dados es robusta; el número de mesas de blackjack y ruleta depende del área supuesta.
- Panel: tarjeta nueva en Escenarios (`/api/escenarios` agrega `sensibilidad_area`); gráfica `7_sensibilidad_area.png`.

## Panel: barras en prisma y guion

- `frontend/src/components/charts.jsx`: plugin de Chart.js que dibuja cada barra vertical como prisma (cara frontal, lateral oscura, tapa en rombo) sobre una columna fantasma de alto completo. Tooltip y leyenda siguen siendo los de Chart.js. Las PNG de `resultados/graficas/` siguen planas (son para el informe impreso).
- `guion_presentacion.md`: guion de 15 minutos para 4 personas, con demostración y preguntas de defensa.

## Siguiente

1. Fase 10: reescribir `README.md` (todavía describe P1), informe PDF y presentación de 15 minutos.
