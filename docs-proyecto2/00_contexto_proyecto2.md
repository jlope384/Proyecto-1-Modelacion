# Proyecto 2: contexto del proyecto elegido

CC3074 Modelización y Simulación, UVG 2026. Este archivo resume lo que se decidió y se encontró para el Proyecto 2, para retomar el trabajo sin releer el chat. Solo incluye lo que se va a usar.

## 1. Documento de entrega

Proyecto grupal de 50 puntos, 6 grupos de máximo 5 integrantes, presentación de 15 minutos con demostración y defensa técnica. Python recomendado. El tema es libre pero sujeto a viabilidad y aprobación del docente. Piden:

- Un sistema real con una pregunta de investigación y una métrica principal con unidades y sentido de mejora.
- Una técnica de simulación vista en clase y una técnica adicional investigada.
- Al menos 3 fuentes técnicas, una académica o documentación, y dos limitaciones de la técnica.
- Tres condiciones como mínimo: base, mejorada y sensibilidad. Al menos 30 repeticiones independientes por condición, con semillas, promedio y dispersión.
- Una prueba interna de consistencia, una comparación contra datos de referencia con MAE o error absoluto y relativo, y al menos una prueba de sensibilidad.
- Una tabla Real / Base / Mejorada con las mismas métricas y unidades, con cambio absoluto y porcentual. No se puede afirmar que la realidad cambió si no se implementó y midió la intervención.
- Tres visualizaciones mínimo (comportamiento del sistema, comparación de escenarios, variabilidad o sensibilidad), con título, ejes, unidades, leyenda y explicación.
- Distinguir entre datos reales observados, datos públicos de referencia, estimaciones y datos sintéticos. Los datos sintéticos solos no cuentan como validación.
- Citar todas las fuentes, datasets, herramientas y usos de inteligencia artificial.
- Entregables: informe técnico en PDF, repositorio GitHub con README y `requirements.txt`, evidencia experimental y presentación.

Puntos: problema real y justificación (4), investigación técnica adicional (5), formulación del modelo (5), simulación funcional (7), técnica implementada (6), diseño experimental y validación (5), comparación con escenario real (6), resultados y conclusiones (4), presentación (8).

## 2. Punto de partida: el Proyecto 1

Simulación de un casino con API Flask y frontend React + Vite. Generador propio (LCG) con transformada inversa y aceptación-rechazo. Pruebas estadísticas hechas a mano (chi², KS, rachas), sin numpy ni scipy. El "piso del casino" es un calendario de eventos con `heapq`: llegadas con proceso de Poisson no homogéneo, colas por juego, abandono por impaciencia y verificación con la ley de Little.

Se reutiliza: generador, pruebas estadísticas, `llegadas.py`, `piso.py`, y los juegos ruleta, dados, tragamonedas y blackjack. Se descartan póker y carreras.

Un día simulado del piso tarda unos 0.6 s. Un GA con población 20, 30 generaciones y 10 réplicas son unas 6,000 corridas, cerca de 1 hora, o unos 15 minutos en paralelo.

## 3. El proyecto

**Título:** asignación óptima de mesas y máquinas en el piso de un casino bajo demanda calibrada con datos públicos.

**Pregunta:** con la misma área total, ¿qué reparto de tragamonedas, blackjack, ruleta y dados maximiza el ingreso diario sin que el abandono pase de 10%?

- **Métrica principal:** ingreso diario, se maximiza. **Restricción:** probabilidad de abandono menor o igual a 10%. **Secundarias:** espera, utilización y win por unidad.
- **Modelo:** el piso de P1 con recursos, pesos, factor de llegadas y paciencia parametrizables.
- **Técnica adicional:** algoritmo genético con restricciones, escrito a mano. Cromosoma de enteros (mesas por juego y número de máquinas), restricción de área total constante (es una redistribución, no una ampliación, así que no hacen falta costos), selección por torneo, cruce, mutación y operador de reparación. Fitness con números aleatorios comunes porque la simulación es ruidosa.
- **Experimentos:** base (configuración actual), mejorada (resultado del GA) y sensibilidad (llegadas +20%, paciencia, pesos de juego, área), 30 o más réplicas con semillas, con promedio, desviación e intervalo de confianza de 95%.
- **Pruebas internas:** ley de Little, conservación de clientes (atendidos más abandonos igual a llegadas) y pruebas del generador.
- **Escala:** se usa un piso proporcional a un local de Nevada y se comparan métricas por unidad.
- **Limitaciones del GA a declarar:** fitness ruidoso y óptimos válidos solo en el rango de demanda calibrado.
- **Fuentes técnicas:** se necesitan tres, una de ellas libro o artículo académico (por ejemplo un texto de computación evolutiva o el trabajo clásico de Holland).

## 4. Datos de referencia

### Nevada Gaming Control Board (principal)

Informe mensual de ingresos, un PDF por mes. Septiembre 2021, todos los locales no restringidos:

| Juego | Unidades | Win del mes (miles de $) | Win por unidad al mes (miles de $) | Win percent |
|---|---|---|---|---|
| Twenty One (blackjack) | 1,933 | 92,180 | 47.7 | 15.30 |
| Roulette | 508 | 42,574 | 83.8 | 18.97 |
| Craps | 328 | 37,684 | 114.9 | 16.39 |
| Slots, total | 122,446 | 780,520 | 6.4 | 7.32 |

- Tragamonedas: 67.4% del win de la tabla. Mesas: 32.6%.
- Unidades por local: 16.8 mesas de blackjack, 5.3 de ruleta, 3.3 de craps y unas 380 máquinas.
- En tragamonedas el win percent es win entre dinero jugado, comparable con `ingreso / apostado`. En mesas se calcula sobre el drop y no es el hold que mide el simulador.
- Datos estatales y agregados. Los periodos de 3 y 12 meses permiten calibrar con un periodo y validar con otro.
- Cada PDF se convierte a CSV con el script de la Fase 5A del documento 02.

### Grand Korea Leisure, visitantes diarios (llegadas)

CSV con 119,670 filas, de 2015 a junio 2026, con fecha, sucursal, género, país del pasaporte y cinco columnas de edad (como texto, hay que confirmar si son conteos). Sumando por día se obtienen visitantes diarios y el patrón por día de semana. No trae hora, así que el perfil horario sigue siendo supuesto. Es un casino solo para extranjeros y 2020 a 2021 tiene cierres por COVID, por lo que esos años se excluyen o se tratan aparte. Se descarga desde data.go.kr.

### Opcionales

- **Kangwon Land, usuarios por tipo de juego:** la ficha dice que trae usuarios diarios por tipo de juego (tragamonedas y mesas), pero la página de descarga no devolvió contenido y no se vieron columnas ni fechas. Si el CSV sirve, refuerza la mezcla de juegos; si no, Nevada la cubre.
- **Mendeley, VIG Live Blackjack:** 720 zapatos de blackjack en vivo, CC BY 4.0, solo conteos de cartas por zapato. Sirve para contrastar la distribución de cartas del `Zapato`.

### Tabla de comparación con la realidad

| Métrica | Referencia | Fuente |
|---|---|---|
| Llegadas diarias y variación por día de semana | Real | Grand Korea Leisure |
| Mezcla de ingreso tragamonedas y mesas (67.4 / 32.6%) | Real | Nevada |
| Win por unidad al mes por juego | Real | Nevada |
| Hold de tragamonedas (7.32%) | Real | Nevada |
| Espera y abandono | Sin referencia real, estimado | Supuesto del modelo |

**Limitaciones de los datos:** ninguno trae tiempos de espera ni abandono, los visitantes son diarios y no por hora, y los datos son de contextos distintos (Corea y Nevada), por lo que se comparan proporciones y patrones, no montos absolutos.

## 5. Espera y abandono

No hay referencia real para estas métricas.

- No se ponen como filas validadas en la tabla Real / Base / Mejorada.
- Se mantienen en el modelo porque son el mecanismo que limita al GA. Sin una restricción de congestión, el GA llenaría el piso con el juego de mayor win por unidad.
- Se reportan como salidas estimadas, con parámetros justificados como supuestos y con sensibilidad (por ejemplo paciencia media entre 50% y 150% del valor base).
- En las conclusiones se dice que el reparto recomendado depende de ese supuesto y que lo validado contra datos reales son llegadas, mezcla e ingreso.
- Alternativa: sustituir la restricción de abandono por una de utilización máxima por recurso (por ejemplo 85%), defendible como regla de planeación.

## 6. Hallazgos del código

Revisados leyendo los módulos y ejecutando funciones.

- **Dados con ventaja de la casa cero.** En el piso se usa la apuesta `par_impar` que paga 1:1 con probabilidad 0.5, retorno teórico exactamente 0. La casa no gana nada de dados y el GA nunca asignaría mesas a ese juego. Hay que cambiar la apuesta del piso.
- **Tragamonedas:** ventaja de la casa de 4.475%, contra 7.32% de win percent en Nevada. Decidir si se ajusta la tabla de pagos o se declara la diferencia como error de calibración.
- **Ruleta:** ventaja de la casa de 2.70%, ruleta europea de un solo cero.
- **Blackjack:** usa estrategia básica, el hold hay que medirlo por simulación.
- `TASA_POR_HORA` es una constante global en `llegadas.py` y `PACIENCIA_MEDIA_MIN` se lee como constante en `piso.py`. Hay que volverlos parámetros.
- `simular_dia(horas, metodo, semilla, recursos, pesos_juego)` ya acepta recursos y pesos. Devuelve ingreso, abandono, espera, utilización, ingreso y apostado por juego, y el chequeo de Little.
- `carreras.py` y `poker.py` no se usan en el piso, pero `simulacion.py`, `validacion.py`, `__init__.py` y `app.py` los importan. Hay que editar esos archivos antes de borrarlos.
- `Piso.jsx` muestra el ingreso con prefijo "Q", pero los datos de Nevada están en dólares y el modelo no tiene unidad real. Hay que cambiar la etiqueta.

## 7. Instrucciones preparadas

**Código (`02_instrucciones_reutilizar_codigo.md`), fases 0 a 10 y 5A:** copia y línea base, borrar Docker y `__pycache__`, quitar carreras y póker, parametrizar llegadas y paciencia, revisar el hold de cada juego, lectores de datos, conversión de los PDF de Nevada a CSV, calibración con periodo de validación, algoritmo genético, experimentos, gráficas, y repositorio y entrega.

**Script de Nevada (Fase 5A):** usa `pdftotext` sobre las primeras páginas y toma la tabla "Statewide, All Nonrestricted Locations", donde cada fila de juego tiene 15 números (3 periodos de 5 campos: locales, unidades, win en miles de dólares, cambio porcentual, win percent). Produce un CSV largo con una fila por mes, juego y periodo, y la columna `win_por_unidad_mes_miles`. Se probó con el texto de septiembre 2021 entregado por la herramienta de lectura de PDF y reprodujo los valores de la tabla de Nevada. No se probó con `pdftotext` sobre el PDF local, así que puede requerir un ajuste menor.

**Interfaz (`03_instrucciones_ui.md`), fases U0 a U9:** la UI pasa de casino jugable a panel de análisis. Se conservan React, Vite, Chart.js, `api.js`, `Tabs.jsx` y `Piso.jsx` (ampliada con recursos, factor de llegadas y paciencia). Pestañas finales: El piso, Datos reales, Optimización, Escenarios, Validación y Fuentes. El GA completo no se corre en vivo en la presentación; la UI muestra resultados precalculados en JSON, con una versión mini opcional. Se conservan el frontend y `app.py` recortados.

## 8. Decisiones

| Decisión | Estado |
|---|---|
| Optimización del piso como eje del proyecto, con datos reales de apoyo | Elegida |
| Nevada para ingreso, mezcla y win por unidad; Grand Korea Leisure para llegadas | Elegida |
| GA con restricciones, escrito a mano | Propuesta |
| Restricción de área total constante, sin necesitar costos | Propuesta |
| Espera y abandono como salidas estimadas, fuera de la tabla validada | Propuesta |
| Piso reducido y proporcional a un local de Nevada, comparando por unidad | Propuesta |
| Frontend y `app.py` conservados y recortados para la demostración | Propuesta |

## 9. Pendientes

- Aprobación del tema por el docente.
- Descargar el CSV de Grand Korea Leisure y confirmar columnas, fechas y si las columnas de edad son conteos.
- Intentar el CSV de Kangwon Land; si no sirve, omitirlo.
- Descargar los PDF de Nevada (entre 12 y 36 meses) y correr y verificar el script de la Fase 5A.
- Decidir cómo arreglar el hold de dados y qué hacer con la diferencia de tragamonedas.
- Definir el área equivalente de cada recurso para la restricción del GA (por ejemplo una máquina como 1 unidad y una mesa como k unidades) y justificar k como estimación.
- Conseguir tres fuentes técnicas para el GA, una de ellas académica.
- Dividir el trabajo entre integrantes. El informe pide contribuciones por integrante y todos presentan.
- Ninguna instrucción se ha ejecutado todavía: son documentos de plan, no cambios hechos al código.

## 10. Archivos

Todos en `Proyecto-1-Modelacion/docs-proyecto2/`:

| Archivo | Contenido |
|---|---|
| `00_contexto_proyecto2.md` | Este resumen |
| `01_plan_proyecto2.md` | Plan del proyecto por partes del documento de entrega |
| `02_instrucciones_reutilizar_codigo.md` | Fases para reutilizar el código, incluido el script de Nevada |
| `03_instrucciones_ui.md` | Fases para transformar la interfaz |

No se modificó ningún archivo de código del Proyecto 1.

## 11. Fuentes

- Nevada Gaming Control Board, Monthly Revenue Report, septiembre 2021: https://gaming.nv.gov/uploadedFiles/gamingnvgov/content/about/gaming-revenue/2021Sep-gri.pdf
- Grand Korea Leisure, Daily visitor information: https://www.data.go.kr/data/15116743/fileData.do
- Kangwon Land, Casino Customer Status by Game Type: https://www.data.go.kr/dcat/metadata/15121887
- VIG Live Blackjack Hand Totals, Mendeley Data: https://data.mendeley.com/datasets/43x8637vfg/1
- Documento del proyecto: Proyecto_2_Modelizacion_y_Simulacion_UVG_2026.pdf
