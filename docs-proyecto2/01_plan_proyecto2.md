# Proyecto 2: plan del proyecto según el documento de entrega

CC3074 Modelización y Simulación, UVG 2026. Proyecto grupal de 50 puntos, presentación de 15 minutos.

## Título

**Asignación óptima de mesas y máquinas en el piso de un casino bajo demanda calibrada con datos públicos.**

Pregunta de investigación: con la misma área total de piso, ¿qué reparto de tragamonedas, blackjack, ruleta y dados maximiza el ingreso diario sin que el abandono por espera pase de 10%?

- **Métrica principal:** ingreso diario del casino, se maximiza.
- **Restricción:** probabilidad de abandono menor o igual a 10%.
- **Métricas secundarias:** espera promedio, utilización por recurso y win por unidad.

## Decisión de enfoque

Se elige la opción B, optimización del piso, con datos reales de apoyo. La opción A, calibración de juegos con livecasinodata, se descartó como eje del proyecto porque exige modelos nuevos de juegos en vivo y el problema se parece menos a un sistema con recursos limitados.

## Datos de referencia

| Fuente | Qué trae | Qué calibra o valida | Estado |
|---|---|---|---|
| Nevada Gaming Control Board, informe mensual de ingresos | Por juego: locales, unidades promedio, win en miles de dólares, cambio porcentual y win percent | Mezcla de ingreso, win por unidad, configuración de recursos y hold de tragamonedas | Verificado con el informe de septiembre 2021, viene en PDF |
| Grand Korea Leisure, visitantes diarios | 119,670 filas de 2015 a junio 2026, por sucursal, género, país y edad | Tasa de llegadas diaria y patrón por día de semana | Metadatos verificados, falta abrir el CSV |
| Kangwon Land, usuarios por tipo de juego | Usuarios diarios por tipo de juego | Mezcla tragamonedas contra mesas | No verificado, la página no devolvió contenido |
| Mendeley, VIG Live Blackjack | 720 zapatos de blackjack en vivo, CC BY 4.0 | Distribución de cartas del zapato | Opcional |

Cifras de Nevada, septiembre 2021, todos los locales no restringidos:

| Juego | Unidades | Win del mes en miles de dólares | Win por unidad al mes en miles de dólares | Win percent |
|---|---|---|---|---|
| Twenty One | 1,933 | 92,180 | 47.7 | 15.30 |
| Roulette | 508 | 42,574 | 83.8 | 18.97 |
| Craps | 328 | 37,684 | 114.9 | 16.39 |
| Slots, total | 122,446 | 780,520 | 6.4 | 7.32 |

- Las tragamonedas son 67.4% del win de la tabla y las mesas 32.6%.
- Unidades por local: unas 16.8 mesas de blackjack, 5.3 de ruleta, 3.3 de craps y unas 380 máquinas.
- En tragamonedas el win percent es win entre dinero jugado, comparable con `ingreso / apostado`. En mesas se calcula sobre el drop, no es el mismo hold que mide el simulador.
- Los datos son estatales y agregados. Hay un PDF por mes, lo que permite calibrar con un periodo y validar con otro.

Grand Korea Leisure: no trae hora, solo día. El perfil horario de llegadas sigue siendo supuesto. Es un casino solo para extranjeros y 2020 a 2021 tiene cierres por COVID, así que esos años se excluyen o se tratan aparte. Las columnas de edad vienen como texto y hay que confirmar si son conteos.

## Parte 1: selección y delimitación del problema

- **Contexto:** piso de un casino con clientes, juegos y colas.
- **Actores:** clientes y casino.
- **Entradas:** llegadas, mezcla de juegos y asignación de recursos.
- **Salidas:** ingreso, espera y abandono.
- **Fuera de alcance:** apuestas deportivas, juegos en línea, comportamiento individual de jugadores y costos laborales.
- **Fuente verificable:** el informe mensual del Nevada Gaming Control Board.

## Parte 2: investigación técnica

Técnica adicional: algoritmo genético con restricciones, implementado a mano sin bibliotecas.

- **Representación:** vector de enteros con mesas de blackjack, ruleta y dados, y número de máquinas.
- **Restricción:** área total fija, igual a la configuración base. Es una redistribución, no una ampliación, y no requiere costos que no tienen.
- **Operadores:** selección por torneo, cruce, mutación y reparación para que todo individuo respete el área.
- **Terminación:** número máximo de generaciones o estancamiento.
- **Limitaciones a declarar:** fitness ruidoso porque viene de una simulación estocástica, y óptimos que solo valen para el rango de demanda calibrado.
- **Fuentes técnicas:** se necesitan tres. Pueden ser un libro de computación evolutiva, el trabajo clásico de Holland y un artículo o documentación sobre manejo de restricciones.

## Parte 3: formulación del modelo y simulación

Es el piso de P1 (`piso.py`) con recursos y pesos parametrizables.

- Diagrama del sistema, variables de estado, parámetros con su procedencia y pseudocódigo del flujo de eventos.
- Carpetas separadas para modelo, simulación, optimización y visualización.
- **Escala:** Nevada reporta unas 380 máquinas por local. Se usa un piso proporcional más pequeño y se compara por unidad, por ejemplo win por máquina o mesa al mes, que no depende del tamaño.
- Documentar cómo se reproduce una ejecución desde un entorno limpio.

## Parte 4: implementación de la mejora

- Función objetivo: ingreso menos penalización por abandono sobre 10%.
- Integración con la simulación mediante números aleatorios comunes.
- Una comprobación en código verifica que la solución final respeta el área y los límites.
- Se conserva el escenario base sin optimizar.
- Parámetros del GA con valor y justificación: tamaño de población, generaciones, probabilidad de cruce y mutación, tamaño del torneo.

## Parte 5: experimentación, verificación y validación

- **Tres condiciones como mínimo:** base (`RECURSOS` actual), mejorada (resultado del GA) y sensibilidad (llegadas +20%).
- **Réplicas:** 30 o más por condición, con semillas guardadas, promedio, desviación e intervalo de confianza.
- **Consistencia interna:** ley de Little, conservación (atendidos más abandonos igual a llegadas) y pruebas del generador.
- **Sensibilidad adicional:** paciencia de los clientes, pesos de juego y área disponible.
- **Incertidumbre y limitaciones:** explicar el riesgo de extrapolar fuera de las condiciones probadas.

## Parte 6: comparación con un escenario de la vida real

La tabla exigida es Real, Base y Mejorada para las mismas métricas.

| Métrica | Referencia | Fuente |
|---|---|---|
| Llegadas diarias y variación por día de semana | Real | Grand Korea Leisure |
| Mezcla de ingreso tragamonedas y mesas (67.4 / 32.6%) | Real | Nevada |
| Win por unidad al mes por juego | Real | Nevada |
| Hold de tragamonedas (7.32%) | Real | Nevada |
| Espera y abandono | Sin referencia real, estimado | Supuesto del modelo |

- Describir fuente, fecha, periodo, tamaño de muestra y condiciones de los datos.
- Calcular error absoluto, MAE y cambio porcentual entre base y mejorada.
- Explicar el nivel de correspondencia entre el modelo base y la referencia antes de interpretar la mejora.
- Distinguir mejora simulada de mejora observada. La mejora es una predicción, no algo medido en un casino real.

## Qué hacer con espera y abandono

No hay referencia real para estas métricas.

- **No se ponen** como filas validadas en la tabla Real, Base y Mejorada.
- **Sí se mantienen** en el modelo, porque son el mecanismo que limita al GA. Sin una restricción de congestión, el GA llenaría el piso con el juego de mayor win por unidad.
- Se reportan como salidas del modelo etiquetadas como estimadas, con los parámetros justificados como supuestos.
- Se les hace análisis de sensibilidad, por ejemplo paciencia media variando entre 50% y 150% del valor base.
- En las conclusiones se dice que el reparto recomendado depende de ese supuesto y que lo validado contra datos reales es la capa de llegadas, mezcla e ingreso.
- Alternativa: sustituir la restricción de abandono por una de utilización máxima por recurso, por ejemplo 85%, defendible como regla de planeación. Se puede reportar la utilización como métrica de apoyo.

## Parte 7: resultados, discusión y conclusiones

Visualizaciones mínimas:

1. Llegadas simuladas contra reales por día de semana.
2. Comparación base contra mejorada.
3. Sensibilidad con barras de error.

Adicionales: convergencia del GA y utilización por recurso. Cada gráfica con título, ejes, unidades, leyenda y explicación. Tablas numéricas, no solo imágenes.

Responder explícitamente: qué mejoró, cuánto, bajo qué condiciones, qué tan confiable es la comparación y qué limitaciones permanecen. Cerrar con una conclusión respaldada por los experimentos y una recomendación concreta de reparto.

## Entregables

- **Informe técnico PDF:** portada, problema, objetivos, fuentes, técnica investigada, modelo, implementación, diseño experimental, validación, comparación real, resultados, limitaciones, conclusiones, referencias y contribuciones por integrante.
- **Repositorio GitHub:** código, README con instrucciones reproducibles, `requirements.txt`, datos autorizados o procedimiento para obtenerlos y estructura organizada.
- **Evidencia experimental:** resultados tabulados, parámetros, semillas, gráficas y métricas.
- **Presentación de 15 minutos** con demostración funcional, y todos los integrantes participan.
- **Citas:** todos los datasets, herramientas y usos de inteligencia artificial.

## Riesgos principales

- **Sin referencia real para espera y abandono.** Se mitiga etiquetándolos como estimados y concentrando la validación en llegadas, mezcla e ingreso.
- **Tiempo de simulación.** Un día simulado tarda unos 0.6 s. Un GA con población 20, 30 generaciones y 10 réplicas son unas 6,000 corridas, cerca de una hora, o unos 15 minutos en paralelo. Con el piso reducido es manejable.
- **Aprobación del tema.** El documento dice que el tema está sujeto a viabilidad y aprobación del docente. Conviene presentárselo antes de invertir tiempo.
- **Datos coreanos y nevadenses de contextos distintos.** Se comparan proporciones y patrones, no montos absolutos.
- **Datos de Nevada en PDF.** Hay que escribir un script para extraerlos, el texto sale en líneas con formato regular.

## Fuentes consultadas

- Nevada Gaming Control Board, Monthly Revenue Report, septiembre 2021: https://gaming.nv.gov/uploadedFiles/gamingnvgov/content/about/gaming-revenue/2021Sep-gri.pdf
- Grand Korea Leisure, Daily visitor information: https://www.data.go.kr/data/15116743/fileData.do
- Kangwon Land, Casino Customer Status by Game Type: https://www.data.go.kr/dcat/metadata/15121887
- VIG Live Blackjack Hand Totals, Mendeley Data: https://data.mendeley.com/datasets/43x8637vfg/1
