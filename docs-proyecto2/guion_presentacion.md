# Guion de la presentación sobre el panel (15 minutos, 4 personas)

Proyecto 2 · CC3074 Modelización y Simulación · UVG 2026.

La presentación es el panel (la UI de `frontend/`): no hay diapositivas aparte, cada persona narra mientras navega sus pestañas. El documento de entrega pide máximo 15 minutos con demostración y defensa técnica, y que **todos participen y puedan explicar el proyecto**. Este guion usa unos 13.5 minutos y deja 1.5 de margen.

El texto entre comillas es una guía para decir con sus palabras, no para leer. Las indicaciones en **negrita** son lo que se hace en pantalla.

## Reparto

| Persona | Tiempo | Tema | Pestañas | Partes del documento |
|---|---|---|---|---|
| 1 | 0:00 – 3:00 | Problema, pregunta y datos | El piso (encabezado) → Fuentes | Parte 1 y datos de la Parte 6 |
| 2 | 3:00 – 6:45 | Modelo, simulación y validación | El piso → Validación → Datos reales | Partes 3 y 6, verificación de la Parte 5 |
| 3 | 6:45 – 10:15 | Algoritmo genético | Armar piso → Optimización | Partes 2 y 4 |
| 4 | 10:15 – 13:30 | Experimentos, resultados y conclusiones | Escenarios → El piso (cierre) | Partes 5 y 7 |

## Preparación (antes de entrar al salón)

- Backend corriendo (`cd backend && python app.py`) y panel abierto (`cd frontend && npm run dev`) en el navegador, en pantalla completa, en la pestaña **El piso**, arriba del todo.
- Revisar que las 7 pestañas cargan. Si alguna dice "No se pudieron cargar los datos", falta un archivo de `resultados/`.
- Probar el zoom del navegador en el proyector: si las tablas se cortan, bajar a 90 %.
- En **El piso**, dejar la semilla en 42 y el factor de llegadas en 1. La primera simulación ya se corre sola al abrir la pestaña.
- Tener a mano las 7 PNG de `resultados/graficas/` por si falla el backend.
- Una sola persona maneja el mouse en cada bloque: la que habla, o la siguiente, pero acordado de antemano.
- Ensayar con cronómetro. Si alguien se pasa, recorta lo suyo, no lo del siguiente.

---

## Persona 1 · Problema, pregunta y datos (0:00 – 3:00)

**Pantalla: El piso, arriba, con el encabezado "EL PISO DEL CASINO" visible.**

**Presentación (0:00 – 0:20)**

> "Somos el grupo … [nombres]. Nuestro proyecto es este panel: una simulación del piso de un casino con un algoritmo genético que decide cómo repartir el espacio entre los juegos. Todo lo que van a ver se calcula en Python y el panel lo muestra en vivo."

**El problema (0:20 – 1:00)**

> "Un casino tiene un área fija. Si pone pocas mesas de un juego, se forman filas y los clientes se van sin jugar; si pone demasiadas, quedan vacías. Los actores son los clientes y el operador. Las entradas son las llegadas, el juego que elige cada cliente y cuántas mesas y máquinas hay; las salidas son ingreso, espera y abandono."

**Pregunta y métrica (1:00 – 1:40)**

> "La pregunta es: con la misma área total, ¿qué reparto de tragamonedas, blackjack, ruleta y dados maximiza el ingreso diario sin que el abandono pase de 10 %? La métrica principal es el ingreso diario, y se maximiza. Está en u.m., unidades monetarias del modelo, porque el modelo no tiene moneda real. Por eso con la realidad comparamos proporciones y no dólares. Dejamos fuera deportes, juegos en línea y costos de personal."

**Fuentes (1:40 – 3:00)**

**Clic en la pestaña Fuentes.** Señalar las dos tarjetas de datos.

> "Usamos dos fuentes reales. Del Nevada Gaming Control Board, los informes mensuales de 2023 y 2024: cuántas mesas y máquinas hay y cuánto gana cada juego. Con eso armamos el piso base: un local promedio de Nevada dividido entre cuatro, 100 máquinas, 4 mesas de blackjack, 1 de ruleta y 1 de dados. De Grand Korea Leisure, en el portal de datos abiertos de Corea, los visitantes de cada día de tres casinos. Con 2023 calibramos el modelo y 2024 lo guardamos para validar sin tocarlo."

**Bajar a la tabla Supuestos del modelo.**

> "El documento pide separar dato real de supuesto, y cada número del panel lleva su etiqueta: real observado, público de referencia, estimado o sintético. Lo más importante: no hay datos públicos de espera ni de abandono, así que esas métricas son estimadas y no las presentamos como validadas."

**Pase:** "[Persona 2] va a mostrar cómo funciona el modelo." **Clic en El piso.**

---

## Persona 2 · Modelo, simulación y validación (3:00 – 6:45)

**Pantalla: El piso.**

**Cómo funciona el modelo (3:00 – 4:00)**

Señalar la tarjeta Configuración mientras se explica.

> "Es una simulación de eventos discretos con tres eventos: llegada, fin de servicio y abandono de la cola. Los clientes llegan según un proceso de Poisson no homogéneo, con un pico en la noche. Cada uno elige un juego; si no hay puesto, espera, y si espera más que su paciencia, se va. Cuando se sienta juega rondas reales, con las reglas de cada juego, hasta que se queda sin dinero, llega a su meta o se le acaba el tiempo. Todo lo aleatorio sale de un generador congruencial propio y de los dos métodos que vimos en clase: transformada inversa y aceptación-rechazo."

**Simular un día (4:00 – 4:50)**

**Clic en SIMULAR UN DÍA** (tarda 1 a 2 segundos).

> "Este es un día con el piso base. Llegaron unas 2,300 sesiones." **Señalar Ingreso del día, Espera media y Abandono.** "Espera y abandono llevan la etiqueta de estimado." **Bajar a Cola y abandono.** "El abandono se concentra en el pico de la noche, que es justo cuando falta capacidad." **Señalar Hold por juego.** "Aquí está cuánto se queda la casa de lo apostado en cada juego."

**Bajar a Consistencia del día simulado.**

> "Cada día comprueba dos cosas: la ley de Little, que el número promedio de clientes sea llegadas por tiempo de permanencia, y que todo cliente que llega termina atendido o abandonando."

**Validación (4:50 – 5:40)**

**Clic en Validación.** Señalar las cuatro tarjetas de arriba y luego cada tabla.

> "Verificamos el modelo por dentro. El generador pasa sus seis pruebas. La distribución de cada juego se probó con 100 semillas: debe rechazar alrededor del 5 % de las veces por puro azar, y eso pasa. En 700 días simulados la ley de Little cuadra con error menor a 2 %. Y el hold que sale de la simulación es compatible con el teórico en los cuatro juegos."

**Datos reales (5:40 – 6:45)**

**Clic en Datos reales.** Señalar la tabla.

> "Calibramos un solo parámetro, la apuesta de los jugadores de mesa, para que la parte del ingreso que viene de máquinas sea la de Nevada 2023, 82 %. Después comparamos con 2024 sin ajustar nada. Esta tabla tiene la referencia real, la simulación base y la mejorada para las mismas métricas." **Señalar Hold de tragamonedas y Llegadas por día.** "El hold de tragamonedas queda a menos de 1 % del real y el patrón de la semana se reproduce bien." **Señalar Win por unidad.** "Lo que no reproducimos bien es el reparto entre mesas: el modelo cree que una mesa de dados gana el doble de lo real y subestima el blackjack. Es nuestra limitación principal, y más adelante mostramos que no cambia la recomendación."

**Pase:** "Con el modelo validado, [Persona 3] explica cómo buscamos el mejor reparto." **Clic en Armar piso.**

---

## Persona 3 · Algoritmo genético (6:45 – 10:15)

**Pantalla: Armar piso.**

**El trade-off (6:45 – 7:40)**

Señalar la barra de Ocupación del área.

> "El piso tiene un área fija de 142 unidades de área, u.a. Una tragamonedas ocupa 1; una mesa de blackjack 6, ruleta 8 y dados 10." **Subir el control de Blackjack dos o tres posiciones.** "Si agrego blackjack, las máquinas bajan solas: no se puede ganar en un juego sin sacrificar otro. Ese es el trade-off que optimiza el algoritmo." **Clic en GA** (arriba de la tarjeta) para cargar el reparto mejorado y mostrar que cabe exacto. **Clic en BASE** para regresar.

**Por qué un algoritmo genético (7:40 – 8:20)**

**Clic en Optimización. Clic en CORRER VERSIÓN MINI de inmediato** (tarda unos 30 segundos; se deja corriendo mientras se habla).

> "Investigamos algoritmos genéticos con restricciones. Cada evaluación es una simulación de varios días, cara y con ruido, y la solución son números enteros con una restricción de área. El algoritmo trabaja con una población, tolera el ruido y maneja la restricción con un operador de reparación. Una búsqueda local como hill climbing se quedaría en el primer óptimo que encuentre. Todo el algoritmo está escrito por nosotros, sin bibliotecas."

**Representación, fitness y parámetros (8:20 – 9:10)**

Señalar la tarjeta Parámetros del GA.

> "Cada individuo es un vector de cuatro enteros: máquinas, blackjack, ruleta y dados. Las máquinas llenan el área que dejan las mesas, así que todo individuo ocupa exactamente 142: es una redistribución, no una ampliación. El fitness es el ingreso medio de 10 días menos una penalización por cada punto de abandono sobre 10 %. Todos los individuos se evalúan con las mismas semillas y los mismos clientes, lo que se llama números aleatorios comunes, para que la comparación sea justa. Cada parámetro tiene su justificación aquí al lado."

**Resultado (9:10 – 10:15)**

**Señalar la gráfica Convergencia.**

> "El algoritmo evaluó 57 repartos y paró en la generación 10 porque dejó de mejorar."

**Señalar la tabla Base contra mejorada.**

> "Pasa de 100 máquinas, 4 blackjack, 1 ruleta y 1 dados a 84, 5, 1 y 2: cambia 16 máquinas por una mesa más de blackjack y una segunda de dados."

**Señalar Verificación de la restricción** y luego **Re-evaluación de candidatos.**

> "La restricción la comprueba el código al terminar, no esta pantalla. Y antes de elegir, los cinco mejores se vuelven a simular con 30 días nuevos, para no quedarnos con uno que solo tuvo suerte."

**Mostrar el resultado de la versión mini** (tarjeta de la izquierda): "la versión corta también encontró un reparto que cumple el área".

**Pase:** "[Persona 4] muestra si la mejora es real y bajo qué condiciones." **Clic en Escenarios.**

---

## Persona 4 · Experimentos, resultados y conclusiones (10:15 – 13:30)

**Pantalla: Escenarios.**

**Diseño experimental (10:15 – 10:45)**

Señalar la tabla Base, mejorada y sensibilidad.

> "Comparamos base contra mejorada en siete condiciones: las calibradas con 100 réplicas; llegadas 20 % menores, 20 % y 40 % mayores; paciencia de 4 y de 12 minutos, con 30 réplicas cada una; y una calibración alternativa por juego con 100. Las dos configuraciones usan las mismas semillas, registradas, así que medimos la diferencia por pares. Son 700 días simulados."

**Resultado principal (10:45 – 11:20)**

Señalar las cuatro tarjetas de arriba.

> "Con las condiciones calibradas, el ingreso sube 5.8 %, con intervalo de 95 % entre 3.4 y 8.2 %. El abandono pasa de 9.1 a 9.7 %, dentro del límite. En Optimización vieron 5.5 % porque allí eran 30 réplicas; aquí son 100."

**Bajo qué condiciones (11:20 – 12:20)**

Señalar Cambio respecto de la base.

> "La mejora aparece en las siete condiciones, y es significativa en seis." **En Sensibilidad, botón LLEGADAS.** "Pero con 20 % más llegadas ninguno de los dos pisos cumple el límite de abandono, y 2024 tuvo 16 % más visitantes que 2023: con esa demanda hace falta más área, no solo redistribuir." **Bajar a Sensibilidad al área por unidad.** "El área de cada mesa era un supuesto, así que corrimos el algoritmo otra vez con mesas 25 % más chicas y más grandes. Siempre agrega la segunda mesa de dados; lo que cambia es cuántas de blackjack."

**Respuestas que pide el documento y recomendación (12:20 – 13:30)**

**Clic en El piso. Clic en MEJORADA (GA) y en SIMULAR UN DÍA**, para cerrar con la propuesta en pantalla.

> "Respondiendo lo que pide el documento. **Qué mejoró:** el ingreso diario simulado. **Cuánto:** 5.8 %, entre 3.4 y 8.2 %. **Bajo qué condiciones:** con la demanda de 2023 o menor y paciencia de 8 minutos o más. **Qué tan confiable:** es significativo con 100 réplicas pareadas y se mantiene con la otra calibración y con otras áreas por mesa. **Qué limitaciones quedan:** espera y abandono no tienen dato real, el modelo no reproduce bien el reparto entre mesas y con la demanda de 2024 el piso ya se satura.
>
> Nuestra recomendación es cambiar unas 16 máquinas por una segunda mesa de dados y una de blackjack. Lo más robusto es la segunda mesa de dados, que aparece en todos los escenarios. Y es una mejora simulada: no se implementó en un casino. Gracias, quedamos atentos a sus preguntas."

---

## Defensa técnica: preguntas probables

Cada persona responde las de su parte. Si piden ver algo, se abre la pestaña indicada.

| Pregunta | Responde | Pestaña | Respuesta corta |
|---|---|---|---|
| ¿Por qué datos de Corea y Nevada y no de Guatemala? | 1 | Fuentes | No hay datos públicos de casinos en Guatemala. Se usan patrones y proporciones, no montos, y está declarado. |
| ¿Por qué el ingreso está en u.m.? | 1 | El piso | El modelo no reproduce el tamaño real de las apuestas. Se compara con Nevada por proporciones y win por unidad, que no dependen de la moneda. |
| ¿Cómo saben que espera y abandono son realistas? | 1 | Fuentes | No lo sabemos: no hay datos. Son "estimado" y se prueba la sensibilidad a la paciencia. |
| ¿Por qué 3 sesiones por visitante? | 2 | Fuentes | Un visitante juega varios juegos. Con 1 no hay congestión y no habría nada que optimizar. Es supuesto; la sensibilidad de llegadas lo cubre. |
| ¿Cómo validaron el generador? | 2 | Validación | Seis pruebas al generador y chi² de cada juego repetida con 100 semillas. |
| ¿Qué es la ley de Little? | 2 | El piso | L = λ · W: clientes promedio en el sistema = llegadas por hora × tiempo de permanencia. Si cuadra, el motor de eventos lleva bien la cuenta. |
| ¿Por qué falla el reparto entre mesas? | 2 | Datos reales | En el modelo dados y ruleta tienen más ventaja de la casa que el blackjack con estrategia básica; en la realidad el blackjack gana más por errores de jugadores. Con una calibración por juego el algoritmo eligió el mismo reparto. |
| ¿Por qué un GA si hay pocos repartos posibles? | 3 | Optimización | Son unos cientos, pero cada uno cuesta 10 días simulados con ruido. El GA evaluó 57 y encontró el óptimo en 10 generaciones, y escala a más juegos o restricciones. |
| ¿Qué son los números aleatorios comunes? | 3 | Optimización | Las mismas semillas y los mismos clientes para todos los repartos, para que la diferencia no sea ruido. Bajó unas 11 veces la varianza de la diferencia. |
| ¿Qué hace la penalización? | 3 | Optimización | Cada punto de abandono sobre 10 % cuesta 10 % del ingreso base, así que el algoritmo casi nunca elige un reparto fuera del límite. |
| ¿Qué parte usa bibliotecas? | 3 | — | Ni el modelo ni el algoritmo. Flask y React son la interfaz; matplotlib solo dibuja las gráficas del informe. |
| ¿Por qué con más llegadas no cumple? | 4 | Escenarios | Los dos pisos se congestionan; el mejorado gana más pero ninguno cumple. Hace falta más área. |
| ¿La mejora es real? | 4 | Escenarios | Es simulada. No se implementó ni se midió en un casino. |
| ¿Qué pasa si las mesas ocupan otra área? | 4 | Escenarios | Con mesas 25 % más chicas o más grandes siempre aparece la segunda mesa de dados; cambia cuántas de blackjack. |
| ¿Se puede probar otra configuración? | 3 o 4 | Armar piso | Mover los controles y **Simular esta configuración**: corre el modelo completo y la compara con la base. |
| ¿Cómo se reproduce todo? | 4 | Fuentes | Comandos en la tarjeta Reproducir desde cero y en el README, con semillas fijas. |
| ¿Cómo usaron inteligencia artificial? | Cualquiera | Fuentes | Lo declarado en la tarjeta Uso de inteligencia artificial y en el informe. |

## Lo que el panel todavía no muestra y el guion dice de palabra

El documento pide que algunas cosas se vean, y hoy el panel no las tiene en pantalla:

- **Portada con integrantes** y la pregunta de investigación escrita.
- **Diagrama del sistema** (llegadas → cola → mesa o máquina → salida). Persona 2 lo explica de palabra.
- **Fórmula del fitness y las tres fuentes técnicas del GA.** Persona 3 lo dice de palabra.
- **Conclusión y recomendación escritas.** Persona 4 las dice sobre El piso.

Agregar una pestaña de inicio con portada, pregunta y diagrama, y una tarjeta de conclusiones, cubriría eso dentro del panel.
