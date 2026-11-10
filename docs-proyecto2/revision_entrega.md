# Revisión contra el documento de entrega

Revisión del repositorio (branch `proyecto-2`) contra `Proyecto_2_Modelizacion_y_Simulacion_UVG_2026.pdf`, después de las Fases 0 a 9 y la UI nueva. Leyenda: **Listo**, **Parcial**, **Falta**.

## Resumen

El trabajo técnico (modelo, datos, calibración, GA, experimentos, validación, gráficas y panel) cubre lo que pide el documento. Lo que falta es casi todo de entrega y redacción: README, informe PDF, presentación, diagrama del sistema, fuentes técnicas del GA y contribuciones. La sensibilidad al área por unidad ya está hecha: la segunda mesa de dados se mantiene con mesas ±25 %, el número de mesas de blackjack y ruleta cambia.

## Instrucciones generales

| Requisito | Estado | Dónde está o qué falta |
|---|---|---|
| Escenario real delimitado y objetivo cuantificable | Listo | `01_plan_proyecto2.md`: ingreso diario con abandono ≤ 10 % y área fija |
| Técnica vista en clase + técnica adicional | Listo | Simulación de eventos discretos, Poisson no homogéneo, transformada inversa y aceptación-rechazo (P1); GA con restricciones (`src/optimizacion/genetico.py`) |
| Escenario base y con mejora, métricas comparables | Listo | `resultados/experimentos/escenarios.json`, mismas semillas |
| Citar fuentes, datasets, herramientas e IA | Parcial | Datasets citados en `datos/README.md` y en la pestaña Fuentes. Falta: fuentes técnicas del GA, herramientas (Flask, React, Chart.js, matplotlib, poppler) y quién revisó lo hecho con IA |
| Código ejecutable, datos, dependencias, instrucciones | Parcial | Código, datos y `requirements.txt` listos. **El `README.md` todavía describe el Proyecto 1** |
| Distinguir real, público, estimado y sintético | Listo | `datos/README.md`, `calibracion.md`, etiquetas en el panel |
| Misma definición de métricas y restricciones | Listo | `src/modelo/escenario.py` es la única definición del escenario |
| 15 minutos, todos participan | Falta | Presentación por hacer |

## Parte 1: problema

| Requisito | Estado | Nota |
|---|---|---|
| Contexto, actores, entradas y salidas | Parcial | Está en `01_plan_proyecto2.md`; falta pasarlo al informe |
| Pregunta de investigación | Listo | |
| Métrica principal con unidades y sentido | Parcial | El ingreso está en u.m. (el modelo no tiene moneda). Hay que justificarlo en el informe: se compara por proporciones y win por unidad |
| Alcance, restricciones, supuestos, exclusiones | Parcial | Repartido en `calibracion.md`, `genetico.md` y Fuentes; falta una sección única |
| Fuente verificable del escenario | Listo | Nevada GCB y Grand Korea Leisure |

## Parte 2: investigación técnica

| Requisito | Estado | Nota |
|---|---|---|
| Objetivo, representación, parámetros, búsqueda, terminación | Listo | `genetico.md` |
| Al menos 3 fuentes técnicas, una académica | **Falta** | No hay ninguna cita del GA en el repo. Sugerencia: Holland (1975), Goldberg (1989), Eiben y Smith (2015), y un artículo de manejo de restricciones (por ejemplo Coello Coello, 2002) o de optimización por simulación con ruido |
| Por qué es mejor que otras alternativas | Parcial | `genetico.md` lo menciona (evaluación cara y ruidosa); falta comparar explícitamente con búsqueda exhaustiva, hill climbing o recocido simulado. Nota: el espacio es pequeño (cientos de configuraciones); conviene decirlo y, si se puede, verificar el óptimo con búsqueda exhaustiva sobre ese espacio |
| Dos limitaciones | Listo | `genetico.md` |
| Qué hace la biblioteca y qué el equipo | Listo | El GA es propio, sin bibliotecas; decirlo en el informe |

## Parte 3: modelo y simulación

| Requisito | Estado | Nota |
|---|---|---|
| **Diagrama del sistema** | **Falta** | No existe en el repo |
| Variables de estado, parámetros, entradas, salidas, distribuciones, eventos | Parcial | Disperso entre el README de P1, `piso.py` y `parametros.json`. Falta una tabla única en el informe |
| Reglas, fórmulas o pseudocódigo | Parcial | Docstrings de `piso.py`; falta pseudocódigo del motor de eventos en el informe |
| Procedencia y unidad de cada parámetro | Listo | `parametros.json` (`procedencia`) y `calibracion.md` |
| Separación modelo, simulación, técnica, visualización | Listo | `backend/casino/`, `src/modelo/`, `src/optimizacion/`, `src/experimentos/`, `src/visualizacion/`, `frontend/` |
| Reproducir desde un entorno limpio | Parcial | Comandos en la pestaña Fuentes y en `datos/README.md`; falta en el README y probarlo en una carpeta nueva |

## Parte 4: mejora

| Requisito | Estado |
|---|---|
| Función objetivo y restricciones formales | Listo (`genetico.md`); escribir la fórmula en el informe |
| Integración con la simulación | Listo |
| Parámetros del método con valor y justificación | Listo |
| Comprobación por código de las restricciones | Listo (`comprobacion_restricciones` en `resultado.json`) |
| Alternativa base sin mejora | Listo |

## Parte 5: experimentación

| Requisito | Estado | Nota |
|---|---|---|
| Base, mejorada y sensibilidad | Listo | 7 condiciones |
| Registro de entradas, parámetros, resultados | Listo | `replicas.jsonl`, `parametros.json`, `resultado.json` |
| ≥ 30 réplicas con semillas, promedio y dispersión | Listo | 30 a 100 por condición |
| Propiedad interna | Listo | Little, conservación, pruebas del generador, hold |
| Comparación con referencia y métrica | Listo | MAE en `comparacion_real.json` |
| Sensibilidad explicada | Listo | Llegadas, paciencia, calibración de mesas y área por unidad (GA con mesas ±25 %, `genetico.md`) |
| Incertidumbre, limitaciones, riesgo de extrapolar | Parcial | Está en `experimentos.md`, `calibracion.md` y `genetico.md`; juntarlo en el informe |

## Parte 6: comparación real

| Requisito | Estado |
|---|---|
| Fuente, fecha, periodo, tamaño de muestra | Listo (`datos/README.md`) |
| Tabla Real / Base / Mejorada | Listo (`comparacion_real.json`, pestaña Datos reales) |
| Correspondencia del modelo base antes de la mejora | Listo (`calibracion.md`): bien en mezcla total, hold y patrón semanal; mal en el reparto entre mesas |
| Cambio absoluto y porcentual | Listo |
| Mejora simulada contra observada | Listo |

## Parte 7: resultados

| Requisito | Estado |
|---|---|
| ≥ 3 visualizaciones con título, ejes, unidades, leyenda | Listo (6 PNG y el panel) |
| Tablas numéricas | Listo |
| Qué, cuánto, bajo qué condiciones, confiabilidad, limitaciones | Listo en `experimentos.md`; pasar al informe |
| Conclusión y recomendación concreta | Parcial: falta redactarla como recomendación al operador |

## Entregables

| Entregable | Estado | Qué falta |
|---|---|---|
| Informe técnico PDF | **Falta** | Todo: portada, problema, objetivos, fuentes, técnica, modelo, implementación, diseño experimental, validación, comparación real, resultados, limitaciones, conclusiones, referencias y contribuciones |
| Repositorio GitHub | Parcial | Reescribir `README.md`; hacer commit y push (los cambios de esta sesión no están commiteados) |
| Evidencia experimental | Listo | `resultados/` |
| Presentación | **Falta** | Diapositivas. La demostración ya existe (panel con guion sugerido en la Fase U9 de `03_instrucciones_ui.md`) |

## Detalles de código encontrados en la revisión

- **Código heredado sin uso en P2:** `blackjack.Mesa`, `blackjack.jugar` interactivo, `simulacion.comparar_estrategias_blackjack` y varias funciones de `validacion.py` ya no las llama la API. No rompen nada; se pueden borrar o mencionar en el README como parte del P1.
- **Dos `requirements.txt`:** `backend/requirements.txt` (Flask) y el de la raíz (Flask y matplotlib). Dejar uno o explicar en el README cuál usar. Falta declarar `pdftotext` (poppler) como dependencia del sistema en el README.
- **`backend/casino/__init__.py`** está ignorado por git (regla `__init__.py` del `.gitignore`), así que cada clon tiene el suyo o ninguno. Funciona como namespace package sin él; convendría quitar esa regla del `.gitignore` y versionar un `__init__.py` vacío para que no haya diferencias entre máquinas.
- **Fotos del panel** (`frontend/src/assets/`): el handoff dice que eran capturas de referencia. Confirmar el derecho de uso o reemplazarlas antes de entregar.
- **Pestaña Fuentes:** completar quién revisó lo generado con IA.
- **Pruebas automáticas:** solo `tests/test_genetico.py`. Los autochequeos de `piso.py`, `calibrar.py` y `correr.py` cubren el resto con `assert`; opcional agregar una prueba rápida de la API.

## Orden sugerido

1. Opcional: búsqueda exhaustiva para confirmar el óptimo del GA.
2. Diagrama del sistema y tabla de variables y parámetros.
3. `README.md` nuevo y commit.
4. Informe PDF con las fuentes técnicas del GA y las contribuciones.
5. Presentación y ensayo de la demostración.
