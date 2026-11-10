# Fases 8 y 9: experimentos y gráficas

Scripts: `python src/experimentos/correr.py` (unos 5 minutos con 4 procesos; se puede correr por grupos con `--grupos` y retomar, porque cada réplica se guarda al terminar) y `python src/visualizacion/graficas.py` (solo lee `resultados/`). Salidas en `resultados/experimentos/` y `resultados/graficas/`.

## Diseño experimental

| Grupo | Condición | Réplicas por piso | Semillas |
|---|---|---|---|
| principal | Parámetros calibrados con 2023 | 100 | 7001–7100 |
| llegadas | Factor de llegadas 0.8, 1.2 (+20 %) y 1.4 | 30 | 7001–7030 |
| paciencia | Paciencia media 4 min (50 %) y 12 min (150 %) | 30 | 7001–7030 |
| calibracion | Calibración alternativa, una escala por mesa | 100 | 7001–7100 |

- Cada condición corre los dos pisos: **base** 100/4/1/1 (máquinas/blackjack/ruleta/dados) y **mejorada** 84/5/1/2, la salida del GA. Misma área (142).
- Las dos configuraciones usan las mismas semillas con `flujos_por_cliente=True`, así que reciben los mismos clientes con la misma suerte. La mejora se mide con la **diferencia pareada** por semilla, no con la diferencia de medias.
- Las semillas 7001 en adelante no se cruzan con calibración (1001-), validación (2001-), llegadas (3001-), fitness del GA (5001-) ni re-evaluación (6001-).
- Total: 700 días simulados.

## Resultados

| Condición | Piso | Ingreso (u.m./día, media ± desv.) | IC 95 % | Abandono | Espera (min) |
|---|---|---|---|---|---|
| Calibrada | Base | 968,881 ± 174,229 | 934,732 – 1,003,030 | 9.11 % | 0.45 |
| Calibrada | Mejorada | 1,025,346 ± 181,666 | 989,739 – 1,060,952 | 9.67 % | 0.58 |
| Llegadas ×0.8 | Base / Mejorada | 817,482 / 855,134 | | 5.21 % / 4.48 % | 0.23 / 0.24 |
| Llegadas ×1.2 | Base / Mejorada | 1,085,836 / 1,119,478 | | 14.23 % / 15.43 % | 0.79 / 0.98 |
| Llegadas ×1.4 | Base / Mejorada | 1,169,584 / 1,235,082 | | 18.99 % / 20.38 % | 1.12 / 1.31 |
| Paciencia 4 min | Base / Mejorada | 954,501 / 1,009,620 | | 9.38 % / 10.13 % | 0.19 / 0.27 |
| Paciencia 12 min | Base / Mejorada | 974,138 / 1,040,877 | | 8.74 % / 9.42 % | 0.71 / 0.90 |
| Calibración por juego | Base / Mejorada | 916,163 / 945,953 | | 9.11 % / 9.67 % | 0.45 / 0.58 |

Diferencia pareada, mejorada menos base:

| Condición | n | Δ ingreso | % | IC 95 % del % | Δ abandono | Mejorada ≤ 10 % |
|---|---|---|---|---|---|---|
| Calibrada | 100 | +56,465 | +5.8 % | +3.4 a +8.2 | +0.56 pp | Sí |
| Llegadas ×0.8 | 30 | +37,652 | +4.6 % | +0.6 a +8.6 | −0.73 pp | Sí |
| Llegadas ×1.2 | 30 | +33,642 | +3.1 % | −2.1 a +8.3 | +1.20 pp | No (base tampoco) |
| Llegadas ×1.4 | 30 | +65,498 | +5.6 % | +1.7 a +9.5 | +1.38 pp | No (base tampoco) |
| Paciencia 4 min | 30 | +55,119 | +5.8 % | +1.6 a +10.0 | +0.75 pp | No (10.13 %) |
| Paciencia 12 min | 30 | +66,739 | +6.9 % | +3.5 a +10.2 | +0.68 pp | Sí |
| Calibración por juego | 100 | +29,790 | +3.3 % | +0.1 a +6.4 | +0.56 pp | Sí |

## Lectura

- **¿Qué mejoró y cuánto?** Con la demanda calibrada, cambiar 16 máquinas por una mesa de blackjack y una de dados sube el ingreso diario simulado 5.8 % (IC 95 % +3.4 a +8.2 %), con el abandono dentro del límite (9.67 %). Con 100 réplicas pareadas la mejora es significativa.
- **Con la calibración alternativa** la mejora baja a +3.3 % pero sigue siendo significativa con 100 réplicas (en la Fase 7, con 30, no lo era). La recomendación no depende del error de calibración entre mesas.
- **Con más llegadas** (+20 % y +40 %) la mejorada sigue ganando más, pero **ningún piso cumple el límite de 10 %**: con esa demanda haría falta más área. 2024 tuvo 16 % más visitantes que 2023, así que esta condición es plausible. Con +20 % el IC de la mejora incluye 0 (30 réplicas).
- **Con paciencia de 4 min** la mejorada queda en 10.13 %, apenas sobre el límite: el óptimo está pegado a la restricción, como ya se veía en el GA. La conclusión depende de un supuesto sin dato real.
- **Consistencia:** en los 700 días atendidos + abandonos = llegadas, y la ley de Little cuadra con error relativo máximo de 1.85 %.
- Toda mejora es **simulada**, no observada en un casino.

## Sensibilidad al área por unidad

`src/experimentos/sensibilidad_area.py`, salida `resultados/experimentos/sensibilidad_area.json`. El GA se corrió de nuevo con mesas 25 % más chicas (5/6/8) y 25 % más grandes (8/10/13); cada reparto elegido se compara con la base con las mismas 100 semillas.

| Áreas BJ/ruleta/dados | Reparto del GA | Mejora de ingreso | IC 95 % | Abandono | ¿Cabe 84/5/1/2? |
|---|---|---|---|---|---|
| 5/6/8 | 76/6/2/2 | +7.6 % | +5.2 a +10.1 | 9.82 % | Sí |
| 6/8/10 | 84/5/1/2 | +5.8 % | +3.4 a +8.2 | 9.67 % | Sí |
| 8/10/13 | 95/3/1/2 | +3.3 % | +0.8 a +5.9 | 10.13 % | No |

La segunda mesa de dados aparece siempre y la mejora es significativa en los tres casos. El número de mesas de blackjack y ruleta sí depende del área supuesta; con mesas más grandes el reparto elegido queda 0.13 pp sobre el límite de abandono.

## Comparación con la referencia real (`comparacion_real.json`)

Tabla Real / Base / Mejorada con datos de 2024 (no usados para calibrar), 100 réplicas por piso. MAE de la base: mezcla implícita 2.58 pp (4 filas), win por mesa relativo a máquina 8.49 veces (3 filas), hold de tragamonedas 0.05 pp. Las filas de abandono, espera e ingreso van como **estimado**, sin referencia real.

## Gráficas (`resultados/graficas/`)

| Archivo | Qué muestra |
|---|---|
| `1_llegadas_dia_semana.png` | Factor del día: GKL 2023, GKL 2024 y simulado |
| `2_comparacion_real.png` | Mezcla implícita y win por unidad: Nevada 2024, base y mejorada |
| `3_convergencia_ga.png` | Mejor fitness acumulado y media de la población por generación |
| `4_base_vs_mejorada.png` | Ingreso y abandono con IC 95 %, utilización por recurso |
| `5_sensibilidad.png` | Ingreso y abandono ante llegadas y paciencia, con bandas IC 95 % |
| `6_diferencias_pareadas.png` | Mejora porcentual por condición con IC 95 % |
| `7_sensibilidad_area.png` | Reparto del GA, mejora y abandono con mesas ±25 % |

Todas tienen título, ejes con unidades y leyenda. Las mismas gráficas se ven en vivo en el panel (pestañas Datos reales, Optimización y Escenarios) con su tabla numérica al lado.

## Archivos

| Archivo | Contenido |
|---|---|
| `replicas.jsonl` | Una línea por condición, piso y semilla con todas las métricas (incluye ingreso y apostado por juego) |
| `replicas.csv` | Las mismas réplicas en plano |
| `escenarios.json` | Resumen por condición, diferencias pareadas, series de sensibilidad y consistencia (lo lee la pestaña Escenarios) |
| `comparacion_real.json` | Tabla Real / Base / Mejorada y MAE (lo lee la pestaña Datos reales) |
