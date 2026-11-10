# Fase 7: algoritmo genético

Script: `python src/optimizacion/genetico.py` (necesita antes `src/calibracion/calibrar.py`). Prueba corta: `--prueba`. Pruebas sin simulación: `python -m unittest discover tests`. Salidas: `resultados/optimizacion/` y `resultados/optimizacion_escala_por_juego/`.

## Diseño

| Elemento | Decisión |
|---|---|
| Cromosoma | Enteros `[tragamonedas, blackjack, ruleta, dados]` |
| Restricción de área | Área total = 142, la del piso base (máquina 1, blackjack 6, ruleta 8, dados 10). Las máquinas llenan exactamente el área que dejan las mesas, así que todo individuo es una redistribución, no una ampliación |
| Mínimo | Al menos 1 unidad por juego (el casino sigue ofreciendo los cuatro; además la demanda por juego es fija) |
| Reparación | Si las mesas no dejan espacio para el mínimo de máquinas, se quita una mesa al azar con probabilidad proporcional al área que ocupa |
| Selección | Torneo de tamaño 3 |
| Cruce | Un punto sobre los genes de mesas, probabilidad 0.9 |
| Mutación | ±1 por gen de mesa, probabilidad 0.3 (alta porque solo hay 3 genes libres) |
| Elitismo | 2 |
| Población / generaciones | 20 / 30 máximo, parada a las 8 generaciones sin mejora |
| Fitness | Ingreso medio en 10 réplicas − 10 × ingreso base × max(0, abandono − 10%) |
| Números aleatorios comunes | Las mismas semillas (5001–5010) para todos los individuos, con `flujos_por_cliente=True` |
| Caché | Mismo cromosoma y mismas semillas dan el mismo resultado, así que no se repiten simulaciones |
| Ruido | Al final se re-evalúan la base y los 5 mejores con 30 semillas nuevas (6001–6030) y se elige el mejor factible en esa re-evaluación, para no quedarse con un individuo que solo tuvo suerte con las semillas del fitness |

La comprobación por código (`factible`) verifica área exacta y mínimos para la solución y para las 57 configuraciones evaluadas. Las pruebas de `tests/test_genetico.py` verifican que la reparación y los operadores siempre producen individuos factibles (2,000 y 500 casos al azar) y que el GA encuentra un óptimo conocido con una función de prueba.

## Resultado (escala única calibrada, k = 18.01)

Paró en la generación 10 por estancamiento: 57 configuraciones, 750 simulaciones, 195 s con 8 procesos.

| Piso | Máquinas | Blackjack | Ruleta | Dados | Ingreso diario (30 réplicas nuevas) | Abandono | Espera |
|---|---|---|---|---|---|---|---|
| Base | 100 | 4 | 1 | 1 | 931,569 ± 173,560 | 8.78% | 0.43 min |
| **Mejorada** | **84** | **5** | **1** | **2** | **983,000 ± 178,615** | **9.36%** | 0.56 min |

- Diferencia pareada (mismas semillas): **+51,431 (+5.5%), IC95 [+11,616, +91,246]**. Es significativa.
- La mejora cambia 16 máquinas por 1 mesa de blackjack y 1 de dados. Utilización: máquinas 39% → 44%, blackjack 58% → 51%, dados 58% → 39%. Las máquinas estaban subutilizadas y sobraban; el área se pasa a mesas, que con la calibración ganan más por unidad de área.
- El abandono sube a 9.36%, dentro del límite. Con las semillas del fitness daba 9.94%: el óptimo está pegado a la restricción, como se espera.
- Otros candidatos cercanos (90/4/1/2, 96/3/1/2, 82/4/2/2) quedan entre 966k y 974k: el patrón común es **una segunda mesa de dados a cambio de máquinas**.

## Sensibilidad a la calibración (escala por juego)

En la Fase 6 el modelo sobreestima la rentabilidad de dados (+99%) y ruleta (+56%) y subestima la de blackjack (−31%). Para ver si eso decide el resultado, se corrió el GA con la calibración alternativa (blackjack 26.2, ruleta 12.3, dados 9.7), que reproduce el win por unidad relativo de cada mesa en Nevada 2023.

| Piso | Ingreso (30 réplicas nuevas) | Abandono |
|---|---|---|
| Base 100/4/1/1 | 869,295 | 8.78% |
| Mejorada **84/5/1/2** | 910,304 | 9.36% |

- **El GA llega al mismo reparto** (84 / 5 / 1 / 2). La recomendación no depende del error de calibración por juego.
- La mejora es menor: +41,009 (+4.7%), IC95 [−13,665, +95,682]. Con 30 réplicas **no es significativa** bajo esta calibración. La Fase 8 debería usar más réplicas (por ejemplo 100) para esta comparación.

## Sensibilidad al área por unidad

El área de cada mesa en máquinas (blackjack 6, ruleta 8, dados 10) es una estimación sin fuente y define el trade-off que optimiza el GA. Se volvió a correr el GA completo con mesas 25 % más chicas y 25 % más grandes (redondeado a enteros). El área total es la del mismo piso base con esas áreas. Script de comparación: `src/experimentos/sensibilidad_area.py` (100 réplicas pareadas, semillas 7001–7100, reutiliza las de la Fase 8).

| Áreas BJ/ruleta/dados | Área total | Reparto del GA | Mejora de ingreso (100 réplicas) | Abandono | ¿Cabe 84/5/1/2? |
|---|---|---|---|---|---|
| 5/6/8 (−25 %) | 134 | 76/6/2/2 | +7.6 %, IC95 [+5.2, +10.1] | 9.82 % | Sí (131) |
| 6/8/10 (modelo) | 142 | 84/5/1/2 | +5.8 %, IC95 [+3.4, +8.2] | 9.67 % | Sí (142) |
| 8/10/13 (+25 %) | 155 | 95/3/1/2 | +3.3 %, IC95 [+0.8, +5.9] | 10.13 % | No (160) |

- **Lo robusto:** en los tres escenarios el GA pone una segunda mesa de dados y la mejora es significativa.
- **Lo que depende del área:** cuántas mesas de blackjack y ruleta. Con mesas más chicas conviene más mesas (6 blackjack, 2 ruletas); con más grandes, menos (3 blackjack).
- Con mesas 25 % más grandes el reparto elegido queda en 10.13 % de abandono con 100 réplicas, apenas sobre el límite; en la re-evaluación de 30 réplicas del GA era 9.96 %. El óptimo está pegado a la restricción.
- Si las mesas fueran 25 % más grandes, 84/5/1/2 no cabría (ocuparía 160 de 155).
- `genetico.py` acepta `--area blackjack=…,ruleta=…,dados=…` (enteros) y guarda cada simulación en `cache_simulaciones.jsonl` de su carpeta, así que una corrida interrumpida se retoma con el mismo comando. Con las áreas por defecto el resultado es idéntico al de antes (verificado con `--prueba`).

## Limitaciones a declarar

- **Fitness ruidoso:** 10 réplicas por individuo. Se mitiga con números aleatorios comunes, caché y re-evaluación con semillas nuevas, pero el GA puede descartar por ruido configuraciones cercanas al óptimo.
- **Óptimo pegado a la restricción de abandono**, que no tiene referencia real (es un supuesto con paciencia de 8 min). Si la paciencia o la llegada cambian, el reparto puede cambiar: lo prueba la sensibilidad de la Fase 8.
- **Válido solo en el rango calibrado:** demanda por juego fija (proporcional al piso base), 3 sesiones por visitante, áreas por unidad estimadas (probadas con ±25 %, ver arriba).
- **El espacio es pequeño** (3 genes libres; unas pocas centenas de configuraciones con sentido). El GA se justifica porque cada evaluación es cara y ruidosa, y porque la misma implementación escala a más juegos o restricciones.

## Archivos de salida

| Archivo | Contenido |
|---|---|
| `historial.csv` | Una fila por generación: mejor y media del fitness, diversidad, mejor cromosoma (gráfica de convergencia) |
| `evaluaciones.csv` | Las 57 configuraciones evaluadas con fitness, ingreso, abandono, espera y utilización |
| `resultado.json` | Parámetros del GA, semillas, re-evaluación, base vs mejorada, diferencia pareada con IC95 y comprobación de restricciones |
| `consola.log` | Salida de la corrida |
