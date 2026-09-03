# Casino - Modelación y Simulación

Simulación de un casino con cuatro juegos (ruleta, dados, tragamonedas y
blackjack), un modo interactivo para jugar manualmente y un modo de simulación
Monte Carlo para analizar el comportamiento del sistema a largo plazo.

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
| Tragamonedas | Símbolo de cada reel | Discreta con pesos 35/30/20/10/5 | Los reels reales tienen símbolos desbalanceados; el 7 es el más raro. Es el caso desbalanceado del proyecto. |
| Blackjack | Rango de la carta | Discreta sobre 13 rangos, **sin reemplazo** | Las cartas salen de un zapato de 6 barajas: la probabilidad de cada rango cambia después de cada extracción, en función de lo que queda. |
| Llegadas | Tiempo entre llegadas de jugadores | Exponencial / proceso de Poisson no homogéneo | Los clientes llegan de forma independiente y no simultánea; la tasa λ(t) depende de la hora (el pico es de 21:00 a 01:00). |

### Métodos de generación

Los dos métodos consumen **la misma fuente uniforme**, así que al compararlos
la única diferencia es el método de transformación.

- **Transformada inversa.** Se recorre la acumulada F(i) y se devuelve el
  primer i con u < F(i). Cuesta exactamente 1 uniforme por variable, pero
  recorrer la acumulada es O(k) y hay que rearmarla cuando la distribución
  cambia (el caso del zapato de blackjack).
- **Aceptación-rechazo.** Se propone j uniforme sobre las k categorías y se
  acepta con probabilidad p_j / p_max. No necesita la acumulada, pero gasta 2
  uniformes por intento y descarta propuestas. La constante de mayoración es
  c = k · p_max, y el costo esperado es 2c uniformes por variable.
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
| POST | `/api/reiniciar` | Devuelve el saldo a 1000 y reinicia la mesa |
| GET/POST | `/api/generador` | Consulta o cambia el método (`inversa` / `aceptacion_rechazo`) y la semilla |

### Juegos

| Método | Ruta | Cuerpo |
|---|---|---|
| POST | `/api/ruleta/jugar` | `{apuesta, tipo, valor}` |
| POST | `/api/dados/jugar` | `{apuesta, tipo, valor}` |
| POST | `/api/tragamonedas/jugar` | `{apuesta}` |
| GET | `/api/blackjack/estado` | — |
| POST | `/api/blackjack/nueva` | `{apuesta}` |
| POST | `/api/blackjack/pedir` | — |
| POST | `/api/blackjack/doblar` | — |
| POST | `/api/blackjack/plantarse` | — |

El blackjack mantiene estado entre peticiones porque una mano son varias
decisiones: `nueva` → (`pedir` \| `doblar`)* → `plantarse`. Mientras la mano
está viva, la segunda carta del dealer viaja como `"?"`.

### Simulación, validación y comparación

| Método | Ruta | Cuerpo |
|---|---|---|
| POST | `/api/simulacion` | `{juego, rondas, apuesta, tipo, valor, metodo, semilla}` |
| POST | `/api/simulacion/blackjack/estrategias` | `{rondas, apuesta, metodo, semilla}` |
| GET/POST | `/api/validacion/uniforme` | `{n, semilla}` — pruebas del LCG contra el Mersenne Twister |
| POST | `/api/validacion/juego` | `{juego, n, metodo, semilla}` — chi-cuadrado del juego |
| POST | `/api/comparacion` | `{juego\|"todos", n, semilla}` — inversa vs aceptación-rechazo |
| POST | `/api/llegadas` | `{horas, metodo, semilla}` |
| POST | `/api/llegadas/validacion` | `{horas, repeticiones, metodo}` |
| GET/POST | `/api/reporte` | Todo el paquete de validación en una sola llamada |

## Resultados

### El LCG propio es utilizable

`x_(n+1) = (1664525·x_n + 1013904223) mod 2^32`. Cumple Hull-Dobell, así que
tiene periodo completo 2^32. Pasa las seis pruebas (media/varianza,
chi-cuadrado de uniformidad, Kolmogorov-Smirnov, rachas y autocorrelación a
retardos 1 y 5), y el Mersenne Twister corriendo las mismas pruebas no queda
mejor parado.

### Los dos métodos son exactos; lo que cambia es el costo

Con 25,000 variables por juego:

| Juego | k | p_max | c = k·p_max | Inversa | Aceptación-rechazo |
|---|---|---|---|---|---|
| Ruleta | 37 | 0.027 | 1.00 | 1.00 u, 1.46 µs | 2.00 u, 1.54 µs, 0% rechazo |
| Dados (por cara) | 6 | 0.167 | 1.00 | 1.00 u, 0.80 µs | 2.00 u, 1.22 µs, 0% rechazo |
| Blackjack (zapato completo) | 13 | 0.077 | 1.00 | 1.00 u, 0.84 µs | 2.00 u, 1.12 µs, 0% rechazo |
| Tragamonedas | 5 | 0.350 | 1.75 | 1.00 u, 0.67 µs | 3.50 u, 1.64 µs, **42.8% rechazo** |

Los valores observados coinciden con la teoría (2c uniformes por variable,
tasa de rechazo 1 - 1/c). La conclusión es que la transformada inversa gana
salvo cuando el número de categorías es grande: en la ruleta, con 37
casillas, recorrer la acumulada casi anula su ventaja.

### La validación hay que hacerla por réplicas, no con una prueba

Una sola prueba chi-cuadrado rechaza H0 el 5% de las veces aunque el
generador esté perfecto. `validacion.validar_replicado` repite la prueba con
muchas semillas y verifica dos cosas: que la tasa de rechazo ronde el 5% y
que los p-valores se distribuyan uniformemente (bajo H0, el p-valor *es*
U(0,1)). Las ocho combinaciones juego × método pasan ese criterio.

### El chi-cuadrado no aplica al zapato de blackjack

Las cartas salen sin reemplazo, así que los conteos quedan más parejos que
bajo muestreo multinomial, el estadístico sale demasiado chico y los
p-valores se van a ~0.99. La prueba es **conservadora**: no detectaría un
generador malo. Por eso la validación por defecto usa el modo `iid` (un
zapato recién barajado por carta), donde el supuesto sí se cumple y los
p-valores quedan bien calibrados. El modo `zapato` se conserva para mostrar
el efecto.

### El costo de aceptación-rechazo depende del estado del sistema

En blackjack, con el zapato recién barajado los 13 rangos son equiprobables y
no hay rechazo. Conforme se reparte, unos rangos se agotan antes que otros,
p_max sube y la tasa de rechazo con ella:

| Tramo del zapato | p_max | Tasa de rechazo |
|---|---|---|
| 0-16% | 0.081 | 5.5% |
| 33-50% | 0.094 | 17.1% |
| 66-83% | 0.106 | 27.3% |
| 83-100% | 0.116 | 34.3% |

Lo mismo pasa en las llegadas: con λ(t) entre 4 y 90 por hora, el
adelgazamiento descarta el 64% de sus propuestas (eficiencia teórica
λ_media/λ_max = 0.374) y gasta 5.6 uniformes por llegada contra 1 de la
inversión de Λ(t).

### Ventaja de la casa

Con 100,000 rondas, lo simulado coincide con lo teórico donde hay forma
cerrada:

| Juego | Apuesta | Simulado | Teórico |
|---|---|---|---|
| Ruleta | color | -2.80% | -2.70% |
| Ruleta | número | -2.44% | -2.70% |
| Dados | suma 7 | -0.05% | 0.00% |

En blackjack no hay forma cerrada (depende de la estrategia y de las reglas),
así que la simulación *es* la manera de estimarlo:

| Estrategia | Retorno sobre lo apostado |
|---|---|
| Básica simplificada | ≈ -1.3% |
| Imitar al dealer | ≈ -6.1% |
| Umbral 15 | ≈ -5.2% |
| Umbral 19 | ≈ -18.1% |

La estrategia básica reduce la ventaja de la casa pero no la elimina, que es
justo el resultado que se espera. Está por debajo del -0.5% de un blackjack
real porque esta versión no parte pares (eso solo vale alrededor de medio
punto) y usa una tabla de doblez simplificada.

## Pendiente

- **La tragamonedas tiene la tabla de pagos rota.** `retorno_teorico()`
  devuelve **+114.9%**: la casa pierde dinero en cada giro. La causa es que
  "2 iguales" paga x2 y ocurre el 55.8% de las veces, con solo 5 símbolos por
  reel. Una tabla que deja la ventaja de la casa en un -4.1% razonable es
  pagar únicamente con tres iguales: **x11 en general y x100 con tres 7**.
  El defecto viene del código original y se dejó sin tocar para no cambiar el
  juego sin decidirlo antes.
- El frontend todavía no tiene pestaña de blackjack ni de validación: la API
  ya está lista, falta el componente de React.
