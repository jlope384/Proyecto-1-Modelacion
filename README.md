# Casino - Modelación y Simulación

Simulación de un casino con seis juegos (ruleta, dados, tragamonedas,
blackjack, carrera de caballos y Texas Hold'em), un modo interactivo para
jugar manualmente y un modo de simulación Monte Carlo para analizar el
comportamiento del sistema a largo plazo.

Toda la aleatoriedad se genera con métodos implementados en el proyecto: un
generador congruencial lineal propio como fuente uniforme, y dos métodos de
generación de variables aleatorias construidos sobre él (**transformada
inversa** y **aceptación-rechazo**), que se validan estadísticamente y se
comparan entre sí.

Backend en Python (Flask, solo API) + frontend en React (Vite).

## Modelo

### Fuentes de aleatoriedad

| Fuente | Variable aleatoria | Distribución | Justificación |
|---|---|---|---|
| Ruleta | Casilla que sale | Discreta uniforme sobre 37 valores | La rueda es simétrica: ninguna casilla tiene por qué salir más que otra. |
| Dados | Cara de cada dado | Discreta uniforme sobre 6 valores | Dado equilibrado. La suma **no** se genera directamente: emerge de sumar dos dados independientes, y su distribución triangular se valida contra la teórica. |
| Tragamonedas | Símbolo de cada reel | Discreta con pesos 35/30/20/10/5 | Los reels reales tienen símbolos desbalanceados; el 7 es el más raro. Es el caso discreto desbalanceado del proyecto. |
| Blackjack | Rango de la carta | Discreta sobre 13 rangos, **sin reemplazo** | Las cartas salen de un zapato de 6 barajas: la probabilidad de cada rango cambia después de cada extracción. |
| Póker | Carta del mazo | Discreta sobre 52 cartas, **sin reemplazo** | Un mazo de 52 por mano; misma idea que el zapato de blackjack, pero además importa el palo (color) y no solo el rango. |
| Póker | Decisión del bot (fold/call/raise) | Umbral sobre una equity estimada por Monte Carlo, con ruido Uniforme | Los bots no siguen una tabla fija: completan al azar las cartas que faltan `m` veces para estimar su probabilidad de ganar, la misma idea que usa `carreras.py` para ponerle precio a una carrera simulándola. |
| Carreras | Velocidad base del caballo | Triangular(3.6, 4.0, 4.8) | La mayoría de los caballos son del montón y pocos destacan. Es el caso **continuo** del proyecto. |
| Carreras | Forma del día | Triangular(0.55, 1, 1.45), por carrera | Absorbe lo que el modelo no representa aparte: jinete, estado de la pista, la partida, el tráfico. |
| Carreras | Ruido de cada tranco | Triangular(0.8, 1, 1.2) | Le da textura a la carrera (adelantamientos, remontadas) sin decidir el resultado. |
| Llegadas | Tiempo entre llegadas de jugadores | Exponencial / proceso de Poisson no homogéneo | Los clientes llegan de forma independiente y no simultánea; la tasa λ(t) depende de la hora (el pico es de 21:00 a 01:00). |

### Métodos de generación

Los dos métodos consumen **la misma fuente uniforme**, así que al compararlos
la única diferencia es el método de transformación.

- **Transformada inversa.** Se recorre la acumulada F(i) (o se aplica F⁻¹ en
  forma cerrada, en el caso continuo). Cuesta exactamente 1 uniforme por
  variable, pero recorrer la acumulada es O(k) y hay que rearmarla cuando la
  distribución cambia (el caso del zapato de blackjack).
- **Aceptación-rechazo.** Se propone un valor de una distribución fácil y se
  acepta con probabilidad f(x)/(c·q(x)). No necesita invertir nada, pero gasta
  2 uniformes por intento y descarta propuestas. La constante de mayoración es
  c = k·p_max en el caso discreto y c = 2 para cualquier triangular.
- Para el proceso de llegadas, los mismos dos métodos aparecen como
  **inversión de Λ(t)** y **adelgazamiento (thinning)**, que es literalmente
  aceptación-rechazo aplicado a un proceso puntual.

## Estructura

```
backend/
  app.py                # servidor Flask con la API (/api/...)
  casino/
    rng.py              # LCG propio + transformada inversa + aceptación-rechazo
    estadistica.py      # chi-cuadrado, KS, rachas, autocorrelación y sus p-valores
    validacion.py       # validación de generadores y comparación de métodos
    ruleta.py           # ruleta europea (0-36)
    dados.py            # dos dados, suma o par/impar
    tragamonedas.py     # 3 reels con símbolos de peso desigual
    blackjack.py        # zapato, manos, estrategias y mesa interactiva
    poker.py            # Texas Hold'em: mazo, evaluador de manos, side pots,
                        # bots por equity Monte Carlo y mesa interactiva
    carreras.py         # caballos, cuotas por Monte Carlo, sobornos, hipódromo
    llegadas.py         # proceso de Poisson de llegadas de jugadores
    simulacion.py       # motor Monte Carlo
  requirements.txt
frontend/
  src/
    App.jsx, api.js, components/...
  vite.config.js        # proxy de /api hacia el backend (localhost:5000)
```

`estadistica.py` implementa a mano la gamma incompleta, la normal acumulada y
la serie de Kolmogorov, así que **no hace falta scipy ni numpy**: el proyecto
sigue corriendo solo con Flask.

## Cómo correrlo

Se necesitan **dos terminales** (backend y frontend corren por separado).

**Terminal 1 - backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # en Windows
pip install -r requirements.txt
python app.py
```
Levanta la API en `http://127.0.0.1:5000`.

**Terminal 2 - frontend:**
```bash
cd frontend
npm install
npm run dev
```
Levanta React en `http://localhost:5173`.

## API

### Estado y generador

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/estado` | Saldo y descripción del generador activo |
| POST | `/api/reiniciar` | Devuelve el saldo a 1000 y reinicia mesa, hipódromo y mesa de póker |
| GET/POST | `/api/generador` | Consulta o cambia el método (`inversa` / `aceptacion_rechazo`) y la semilla |

### Juegos

| Método | Ruta | Cuerpo |
|---|---|---|
| POST | `/api/ruleta/jugar` | `{apuesta, tipo, valor}` |
| POST | `/api/dados/jugar` | `{apuesta, tipo, valor}` |
| POST | `/api/tragamonedas/jugar` | `{apuesta}` |
| GET | `/api/tragamonedas/tabla` | Tabla de pagos y valores teóricos exactos |
| GET | `/api/blackjack/estado` | — |
| POST | `/api/blackjack/nueva` | `{apuesta}` |
| POST | `/api/blackjack/pedir` \| `/doblar` \| `/plantarse` | — |

El blackjack mantiene estado entre peticiones porque una mano son varias
decisiones: `nueva` → (`pedir` \| `doblar`)* → `plantarse`. Mientras la mano
está viva, la segunda carta del dealer viaja como `"?"`.

### Póker (Texas Hold'em)

| Método | Ruta | Cuerpo |
|---|---|---|
| GET | `/api/poker/estado` | — |
| POST | `/api/poker/comprar` | `{monto}` — sentarse o comprar más fichas |
| POST | `/api/poker/nueva` | — reparte la siguiente mano |
| POST | `/api/poker/accion` | `{accion, monto}` — `accion` es `fold`/`check`/`call`/`raise`; `monto` solo aplica a `raise` y es la apuesta TOTAL de la calle, no el incremento |
| POST | `/api/poker/retirarse` | — cash out: el stack vuelve al saldo del casino |

Mesa de 4 asientos: el humano (asiento 0) contra 3 bots que deciden con
equity por Monte Carlo (ver la tabla de fuentes de aleatoriedad). El flujo es
`comprar` → `nueva` → (`accion`)* → showdown, y se repite con `nueva` para la
siguiente mano. Como en blackjack, la mesa resuelve sola los turnos de los
bots entre una llamada y la siguiente; la petición solo se detiene cuando le
toca decidir al humano. Los bots mantienen su stack entre manos y se
recargan solos si quedan muy cortos (son la banca de la casa, no dinero real
del usuario), así que siempre se puede seguir probando escenarios de all-in
y side pot.

### Carrera de caballos

| Método | Ruta | Cuerpo |
|---|---|---|
| GET | `/api/carreras/estado` | — |
| POST | `/api/carreras/nueva` | — (genera el lote y le pone precio) |
| POST | `/api/carreras/soborno/dato` | — (cuesta 200) |
| POST | `/api/carreras/soborno/redbull` | `{caballo}` (cuesta 500) |
| POST | `/api/carreras/apostar` | `{caballo, apuesta}` |
| POST | `/api/carreras/correr` | — (devuelve el historial para animar) |
| POST | `/api/carreras/soborno/analisis` | `{repeticiones, apuesta}` |
| POST | `/api/carreras/precision-cuotas` | `{lotes, m_referencia}` |
| GET/POST | `/api/carreras/validacion` | `{n}` — chi-cuadrado y KS de la triangular |

El flujo es `nueva` → (`dato` \| `redbull`)* → `apostar` → `correr`. La
velocidad y la energía reales de cada caballo **no se revelan** hasta que la
carrera termina: antes solo se ve la cuota.

### Simulación y validación

| Método | Ruta | Cuerpo |
|---|---|---|
| POST | `/api/simulacion` | `{juego, rondas, apuesta, tipo, valor, metodo, semilla}` |
| POST | `/api/simulacion/blackjack/estrategias` | `{rondas, apuesta, metodo, semilla}` |
| GET/POST | `/api/validacion/uniforme` | `{n, semilla}` — pruebas del LCG contra el Mersenne Twister |
| POST | `/api/validacion/juego` | `{juego, n, metodo, semilla}` |
| POST | `/api/comparacion` | `{juego\|"todos", n, semilla}` — inversa vs aceptación-rechazo |
| POST | `/api/llegadas` \| `/api/llegadas/validacion` | `{horas, metodo, semilla}` |
| GET/POST | `/api/reporte` | Todo el paquete de validación en una sola llamada |

## Resultados

### El LCG propio es utilizable

`x_(n+1) = (1664525·x_n + 1013904223) mod 2^32`. Cumple Hull-Dobell, así que
tiene periodo completo 2^32. Pasa las seis pruebas (media/varianza,
chi-cuadrado de uniformidad, Kolmogorov-Smirnov, rachas y autocorrelación a
retardos 1 y 5), y el Mersenne Twister corriendo las mismas pruebas no queda
mejor parado.

### Los dos métodos son exactos; lo que cambia es el costo

| Variable | k | p_max | c teórico | Inversa | Aceptación-rechazo |
|---|---|---|---|---|---|
| Ruleta | 37 | 0.027 | 1.00 | 1.00 u, 1.46 µs | 2.00 u, 1.54 µs, 0% rechazo |
| Dados (por cara) | 6 | 0.167 | 1.00 | 1.00 u, 0.80 µs | 2.00 u, 1.22 µs, 0% rechazo |
| Blackjack (zapato completo) | 13 | 0.077 | 1.00 | 1.00 u, 0.84 µs | 2.00 u, 1.12 µs, 0% rechazo |
| Tragamonedas | 5 | 0.350 | 1.75 | 1.00 u, 0.67 µs | 3.50 u, 1.64 µs, **42.8% rechazo** |
| Carreras (triangular, continua) | — | — | **2.00** | 1.00 u, 0.49 µs | 3.99 u, 1.42 µs, **49.9% rechazo** |

Los valores observados coinciden con la teoría (2c uniformes por variable,
tasa de rechazo 1 − 1/c). La transformada inversa gana salvo cuando el número
de categorías es grande: en la ruleta, con 37 casillas, recorrer la acumulada
casi anula su ventaja.

La triangular es el caso más limpio de todos, porque su constante de
mayoración sale exacta y no depende de los parámetros: con propuesta uniforme,
c = f(moda)/q = (2/(b−a))/(1/(b−a)) = **2 siempre**. La predicción es que
acepta la mitad de las propuestas y gasta 4 uniformes por variable; lo medido
fue 49.9% y 3.99.

### La validación hay que hacerla por réplicas, no con una prueba

Una sola prueba chi-cuadrado rechaza H0 el 5% de las veces aunque el generador
esté perfecto. `validacion.validar_replicado` repite la prueba con muchas
semillas y verifica que la tasa de rechazo ronde el 5% y que los p-valores se
distribuyan uniformemente (bajo H0, el p-valor *es* U(0,1)). Las ocho
combinaciones juego × método pasan ese criterio.

### El chi-cuadrado no aplica al zapato de blackjack

Las cartas salen sin reemplazo, así que los conteos quedan más parejos que
bajo muestreo multinomial, el estadístico sale demasiado chico y los p-valores
se van a ~0.99. La prueba es **conservadora**: no detectaría un generador
malo. Por eso la validación por defecto usa el modo `iid` (un zapato recién
barajado por carta), donde el supuesto sí se cumple.

### El costo de aceptación-rechazo depende del estado del sistema

En blackjack, con el zapato recién barajado los 13 rangos son equiprobables y
no hay rechazo. Conforme se reparte, unos rangos se agotan antes que otros,
p_max sube y la tasa de rechazo con ella: de 5.5% al inicio a 34.3% al final
del zapato. Lo mismo en las llegadas: con λ(t) entre 4 y 90 por hora, el
adelgazamiento descarta el 64% de sus propuestas (eficiencia teórica
λ_media/λ_max = 0.374) y gasta 5.6 uniformes por llegada contra 1 de la
inversión de Λ(t).

### Ventaja de la casa

Con 100,000 rondas, lo simulado coincide con lo teórico donde hay forma
cerrada:

| Juego | Apuesta | Simulado | Teórico |
|---|---|---|---|
| Ruleta | color | −2.80% | −2.70% |
| Ruleta | número | −2.44% | −2.70% |
| Dados | suma 7 | −0.05% | 0.00% |
| Tragamonedas | — | −4.57% ± 0.24% | −4.475% |

En blackjack no hay forma cerrada (depende de la estrategia y de las reglas),
así que la simulación *es* la manera de estimarlo: estrategia básica ≈ −1.3%,
imitar al dealer ≈ −6.1%, umbral 19 ≈ −18.1%. Está por debajo del −0.5% de un
blackjack real porque esta versión no parte pares y usa una tabla de doblez
simplificada.

### La tragamonedas estaba rota y se arregló

La versión original pagaba x2 por dos símbolos iguales, que salen el **55.8%**
de las veces, y x5 por cualquier trío. El retorno esperado del jugador era
**+114.9%**: la casa perdía dinero en cada giro. Se comprueba enumerando los
125 resultados posibles, sin simular nada.

La tabla nueva corrige dos cosas:

1. **Cada trío paga según su rareza.** Tres cerezas salen 1 de cada 23 giros y
   tres sietes 1 de cada 8,000; pagarles igual no tenía sentido. Los pagos son
   aproximadamente proporcionales a 1/p, como en las tragamonedas reales.
2. **Dos iguales devuelve la apuesta** en vez de duplicarla. Es un empate, no
   un premio: al pasar el 55.8% de las veces, cualquier pago positivo sobre
   ese evento regala el juego.

| Combinación | Paga | Sale 1 de cada |
|---|---|---|
| 3 x 🍒 | x2 | 23 |
| 3 x 🍋 | x3 | 37 |
| 3 x 🔔 | x8 | 125 |
| 3 x ⭐ | x50 | 1,000 |
| 3 x 7️⃣ | x300 | 8,000 |
| 2 iguales | devuelve la apuesta | 2 |

Retorno esperado: **−4.475%**, del orden de una tragamonedas real (2% a 15%) y
comparable al −2.70% de la ruleta.

### La carrera original era determinista

En el script original cada caballo avanzaba exactamente su velocidad en cada
paso, así que el ganador quedaba decidido en el instante en que se generaban
los caballos: correr la carrera era ejecutar una fórmula, no simular nada.

Agregar ruido tranco a tranco **no alcanza para arreglarlo**, y la razón es
cuantitativa: ese ruido se promedia. Con una desviación de 0.14 por tranco
sobre 18 pasos, la distancia total varía apenas 0.14/√18 = 3.4%, muy poco
frente al 30-40% en que difieren las velocidades. Por eso el modelo incluye la
**forma del día**, que se sortea una vez por carrera y por lo tanto no se
promedia: su desviación de 14% entra completa y es lo que vuelve competitiva
la prueba.

### Las cuotas se fijan simulando, y ahí aparece la maldición del ganador

El pago original era 1:1 con 10 caballos, o sea un retorno de **−80%** para el
jugador. Ahora la casa estima P(gana) de cada caballo corriendo la carrera m
veces y fija la cuota decimal como

    cuota_i = (1 − margen) / p_i

con lo que el retorno esperado es **−margen para cualquier caballo**, igual que
en la ruleta europea toda apuesta rinde −2.70%. El overround medido es 0.0526,
que es exactamente margen/(1−margen).

Pero la casa pone precio con p **estimada**, no verdadera, y eso introduce un
sesgo que no es obvio. El favorito no es un caballo cualquiera: es el que
quedó con la p estimada **más alta**, así que se lo selecciona junto con su
error de estimación. En promedio p_estimada > p_verdadera para el favorito, y
su cuota queda demasiado corta. Al tapado le pasa lo contrario.

Sesgo medido (p que usa la casa menos p de referencia, del caballo elegido):

| m | Favorito | Tapado | Azar |
|---|---|---|---|
| 25 | +0.092 | −0.061 | −0.003 |
| 50 | +0.044 | −0.024 | −0.020 |
| 100 | +0.011 | −0.014 | +0.006 |
| 250 | +0.006 | −0.009 | +0.001 |
| 500 | +0.010 | −0.003 | +0.001 |

Apostar **al azar** no tiene sesgo, porque ahí no hay selección: ésa es la
estrategia que rinde el −margen nominal, y sirve de control. Los otros dos
sesgos se encogen al crecer m, lo que responde a una pregunta concreta de
diseño: la casa necesita simular del orden de 250 a 500 carreras antes de
abrir la ventanilla para que el sesgo quede chico frente al margen que quiere
cobrar.

### El soborno del dato no sirve; el del redbull sí

Con 800 carreras y apuesta de 100 (los retornos vienen con intervalo de
confianza al 95%, porque apostar a cuotas altas tiene una desviación de varias
veces la apuesta en cada carrera):

| Escenario | Costo | P(gana) | Retorno | IC 95% | ¿Difiere del nominal? |
|---|---|---|---|---|---|
| favorito | 0 | 0.265 | −2.6% | [−14.1%, +8.9%] | no |
| tapado | 0 | 0.043 | +31.3% | [−20.1%, +82.8%] | no |
| azar | 0 | 0.119 | +1.5% | [−24.1%, +27.0%] | no |
| dato | 200 | 0.270 | −196.1% | [−208.4%, −183.8%] | **sí** |
| redbull al favorito | 500 | 0.629 | −363.9% | [−377.0%, −350.8%] | **sí** |
| redbull al tapado | 500 | 0.338 | **+480.0%** | [+347.6%, +612.4%] | **sí** |

Pagar 200 por saber cuáles son los tres caballos más rápidos **empeora el
resultado en exactamente el costo del dato**: esa información la casa ya la
usó para poner el precio, así que no vale nada. El redbull sí es rentable, y
no porque dé información sino porque **cambia la carrera después de que el
precio quedó fijo**: es el único de los tres sobornos que rompe el supuesto
sobre el que la casa calculó las cuotas. Aplicado al tapado da una ventaja de
9.8 por unidad apostada, así que conviene a partir de una apuesta de 51
créditos.

Nótese que el +31.3% del tapado sin sobornar **no es una estrategia ganadora**:
su intervalo de confianza va de −20% a +83% y contiene el −5% nominal. Es
justo el tipo de conclusión falsa que se saca al mirar una media sin su
incertidumbre.

## Pendiente

El frontend todavía no tiene pestaña de blackjack, de carreras, de póker ni de
validación: la API ya está lista para las cuatro, falta el componente de
React.
