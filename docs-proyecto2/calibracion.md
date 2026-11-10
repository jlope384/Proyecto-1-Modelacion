# Fase 6: calibración y validación

Script: `python src/calibracion/calibrar.py` (100 réplicas, ~1.5 min con 8 procesos). Escenario compartido: `src/modelo/escenario.py`. Salidas: `resultados/calibracion/`.

Periodo de calibración: **2023**. Periodo de validación (hold-out): **2024**. Las semillas de calibración (1001–1100) y de validación (2001–2100) son distintas.

## Qué viene de datos, qué es supuesto y qué se calibra

| Elemento | Valor | Procedencia |
|---|---|---|
| Piso base | 100 tragamonedas, 4 blackjack, 1 ruleta, 1 dados | Dato público de referencia: unidades por local de Nevada 2023 / 4 |
| Área por unidad | máquina 1, blackjack 6, ruleta 8, dados 10 (área base 142) | Estimación del equipo: puestos + espacio del crupier |
| Puestos por mesa | blackjack 5, ruleta 7, dados 8 | Supuesto (Proyecto 1) |
| Demanda por juego | proporcional a los puestos del piso base (74.1 / 14.8 / 5.2 / 5.9 %) | Supuesto: el operador dimensionó el piso según su demanda |
| Nivel de llegadas | 776.9 visitantes/día por sucursal | Dato real observado: GKL 2023 (2,330.6 / 3 sucursales) |
| Sesiones por visitante | 3 → 2,331 sesiones/día (`factor_llegadas` 2.884) | Supuesto (ver abajo) |
| Factores por día de la semana | GKL 2023 | Dato real observado |
| Perfil por hora | `llegadas.TASA_POR_HORA` | Supuesto (GKL no trae horas) |
| **`escala_bankroll_mesas`** | **18.01** | **Calibrado** contra la mezcla de Nevada 2023 |

**Sesiones por visitante.** Un cliente del simulador es una sesión en un juego; un visitante juega varias. Con 1 sesión por visitante el piso base casi no tiene cola (abandono 0.5%) y no habría reparto que optimizar. Con 3 el piso base queda en 9.2% de abandono, cerca del límite de 10%. No hay dato: se declara como supuesto del escenario y se cubre con la sensibilidad de llegadas (+20%) de la Fase 8.

## Hallazgo: las "unidades por local" de Nevada no describen un mismo piso

En Nevada 2023 las tragamonedas están en ~310 locales y las mesas en ~100 (muchos locales solo tienen máquinas). Por eso las unidades por local (401 máquinas, 17.8 blackjack, 4.4 ruleta, 3.1 dados) dan 22 máquinas por mesa de blackjack, mientras que la composición estatal da **62** (y 289 por ruleta, 392 por dados). La mezcla de ingreso de Nevada corresponde a la composición estatal.

Consecuencia: la mezcla del piso simulado (más mesas por máquina que el estado) no se compara directamente. Se compara la **mezcla implícita**: win por unidad simulado de cada juego × unidades estatales de Nevada del mismo año. Se agregó la métrica `unidades_estatales` a `datos/procesados/nevada_referencia.csv` (`src/datos/nevada_referencia.py`).

## Parámetro calibrado

Las mesas del simulador ganaban muy poco frente a las máquinas: con escala 1 la mezcla implícita de tragamonedas era 96%, contra 82.0% en Nevada. `escala_bankroll_mesas` multiplica el bankroll (y por lo tanto la apuesta) de quien se sienta en una mesa. Representa lo que el modelo no tiene: mínimos de mesa más altos, presupuestos mayores de jugadores de mesa.

- **Indicador único:** mezcla implícita de tragamonedas, Nevada 2023 = 82.03%.
- Con números aleatorios comunes el ingreso de mesas es proporcional a la escala (la congestión no cambia), así que se resuelve en forma cerrada y converge en una iteración: **k = 18.01**.

## Validación (100 réplicas con semillas nuevas)

| Métrica | Juego | Nevada 2023 | Nevada 2024 | Simulado | Error rel. 2024 |
|---|---|---|---|---|---|
| Win por mesa / win por máquina | Blackjack | 8.05 | 8.04 | 5.53 | −31% |
| | Ruleta | 12.94 | 12.21 | 19.01 | +56% |
| | Dados | 17.81 | 16.67 | 33.10 | +99% |
| Mezcla implícita (%) | Tragamonedas | 82.03 (calibrado) | 82.50 | 80.79 | −2.1% |
| | Blackjack | 10.57 | 10.52 | 7.08 | −33% |
| | Ruleta | 3.67 | 3.45 | 5.27 | +53% |
| | Dados | 3.73 | 3.53 | 6.87 | +95% |
| Hold de tragamonedas (%) | | 7.17 | 7.21 | 7.47 | +3.5% |
| Factor por día (MAE, 7 días) | | | | | 0.037 (3.5%) |
| Nivel de sesiones/día | | | 2,702 | 2,336 | −13.5% |

MAE (solo filas de validación): mezcla 2.6 pp (2024), win por unidad relativo 8.6 veces (2024), hold 0.25 pp, factores por día 0.037.

Lectura:

- **Bien reproducido:** la mezcla total máquinas/mesas (82%), el hold de tragamonedas (error < 5%, sin haberlo ajustado: la tabla de pagos se fijó con septiembre 2021) y el patrón semanal de llegadas (error medio 3.5%; sábado y domingo algo altos porque 2024 fue menos marcado que 2023).
- **Mal reproducido:** el reparto entre mesas. El simulador sobreestima dados (≈ 2×) y ruleta (+50%) y subestima blackjack (−30%). Viene de las reglas de cada juego en el modelo: la apuesta `field` de dados tiene 5.6% de ventaja y la de ruleta 2.7%, contra 0.9% de blackjack con estrategia básica; en la realidad el blackjack retiene más por errores de los jugadores y apuestas laterales.
- **Nivel de llegadas:** 2024 tuvo 16% más visitantes que 2023. El modelo calibrado con 2023 queda 13.5% abajo; la sensibilidad +20% de la Fase 8 cubre ese crecimiento.

**Implicación para el GA:** como el modelo hace a dados y ruleta más rentables por mesa que en la realidad, un GA calibrado con una sola escala tenderá a favorecerlos. Por eso se guarda una **calibración alternativa por juego** (`alternativa_escala_por_juego` en `parametros.json`: blackjack 26.2, ruleta 12.3, dados 9.7), que reproduce exactamente el win por unidad relativo de 2023 en cada mesa. Son 3 parámetros para 3 indicadores (no tiene validación propia salvo 2024), así que no es la calibración principal; se usa para comprobar si el reparto recomendado depende de este error (ver `genetico.md`).

## Salidas estimadas del piso base (sin referencia real)

Abandono 9.2% (IC95 9.0–9.4%), espera promedio 0.46 min, utilización: máquinas 39%, blackjack 58%, ruleta 56%, dados 57%. Ingreso diario 968,470 (desviación 168,406) en unidades del modelo: **no se compara con dólares**, solo se usan proporciones.

## Consistencia interna

En las 100 réplicas: atendidos + abandonos = llegadas en todas, y la ley de Little cuadra con error relativo máximo de 1.2%.

## Cambios al motor (`backend/casino/piso.py`)

Los dos son opcionales y con los valores por defecto `simular_dia(24, semilla=1)` sigue idéntico a `linea_base_p2.json` (comprobado):

- `escala_bankroll_mesas=1.0`: número o dict por mesa.
- `flujos_por_cliente=False`: con True, el flujo de la semilla solo genera llegadas y elección de juego; cada cliente (bankroll, paciencia, sesión) y cada zapato tiene su flujo derivado. Así dos pisos con la misma semilla reciben los mismos clientes con la misma suerte. Medido con 30 semillas entre el piso base y un vecino (−10 máquinas, +1 dados): la desviación de la diferencia de ingreso baja de 226,485 a 67,147 (varianza ~11 veces menor). Todo el código del Proyecto 2 (`escenario.py`) lo usa activado, incluida la calibración.

## Archivos de salida

| Archivo | Contenido |
|---|---|
| `parametros.json` | Parámetros que leen el GA y los experimentos, con procedencia e iteraciones de calibración |
| `validacion.csv` | Real contra simulado, rol (calibrado o validación), error absoluto y relativo |
| `llegadas_dia_semana.csv` | Datos para la gráfica de llegadas simuladas contra reales por día |
| `replicas_calibracion.csv` | Una fila por semilla de validación |
| `resumen.json` | MAE por grupo, salidas estimadas, chequeos de consistencia |
