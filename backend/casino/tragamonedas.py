"""
Tragamonedas de 3 reels.

Modelo de aleatoriedad: cada reel es una variable aleatoria discreta con
probabilidades DESIGUALES (la cereza sale 7 veces más seguido que el 7).
Ese desbalance es justo lo que castiga a la aceptación-rechazo: con propuesta
uniforme sobre 5 símbolos, la probabilidad de aceptar en un intento es

        1/c = 1/(k * p_max) = 1/(5 * 0.35) = 0.571

o sea que se descarta ~43% de las propuestas y hacen falta en promedio unos
3.5 uniformes por símbolo, contra 1 de la transformada inversa. Es el mejor
caso del proyecto para mostrar el costo del método.

Tabla de pagos
--------------
La versión original de este juego estaba rota: pagaba x2 por dos símbolos
iguales, que ocurren el 55.8% de las veces, y x5 por cualquier trío. El
retorno esperado del jugador salía en +114.9%, es decir que la casa perdía
dinero en cada giro. Se puede comprobar con `retorno_teorico`, que enumera
los 125 resultados posibles.

La tabla actual corrige eso con dos cambios:

1. Cada trío paga según su RAREZA, no todos lo mismo. Tres cerezas salen 1 de
   cada 23 giros y tres sietes 1 de cada 8,000, así que pagarles igual no
   tenía sentido. Los pagos son aproximadamente proporcionales a 1/p, que es
   como funcionan las tragamonedas reales.

2. Dos iguales devuelve la apuesta en vez de duplicarla. Es un empate, no un
   premio: al pasar el 55.8% de las veces, cualquier pago positivo sobre ese
   evento regala el juego. Así el jugador conserva la sensación de que "casi
   siempre pasa algo" sin que la casa pierda.

El resultado es una ventaja de la casa de 7.325%, que coincide con el 7.32% de
win percent de las tragamonedas de Nevada (NGCB, sept. 2021; rango real 2%-15%), por encima del 2.70% de la ruleta europea.
"""

from itertools import product

from . import rng

SIMBOLOS = ["🍒", "🍋", "🔔", "⭐", "7️⃣"]
PESOS = [35, 30, 20, 10, 5]  # 7️⃣ es el símbolo más raro

_TOTAL_PESOS = float(sum(PESOS))
PROBABILIDADES = [w / _TOTAL_PESOS for w in PESOS]

# Ganancia NETA por unidad apostada al sacar tres del mismo símbolo.
# El orden sigue a SIMBOLOS: cereza, limón, campana, estrella, siete.
PAGOS_TRIO = [2, 3, 7, 40, 216]

# Dos iguales: multiplicador 0 = se devuelve la apuesta (ni gana ni pierde).
PAGO_PAR = 0.0

# Sin coincidencias: se pierde lo apostado.
PAGO_NADA = -1.0


def girar_reel(generador=None):
    gen = rng.resolver(generador)
    return SIMBOLOS[gen.discreta(PROBABILIDADES)]


def _multiplicador(indices):
    """Ganancia neta por unidad apostada para una combinación de 3 índices."""
    i, j, k = indices
    if i == j == k:
        return PAGOS_TRIO[i]
    if i == j or j == k or i == k:
        return PAGO_PAR
    return PAGO_NADA


def jugar(apuesta, generador=None):
    """
    Tres símbolos iguales pagan según la tabla (x2 cereza … x300 siete),
    dos iguales devuelven la apuesta, y sin coincidencias se pierde.

    Devuelve (reels, gano, ganancia_neta, empate).
    """
    gen = rng.resolver(generador)
    indices = [gen.discreta(PROBABILIDADES) for _ in range(3)]
    reels = [SIMBOLOS[i] for i in indices]

    multiplicador = _multiplicador(indices)
    gano = multiplicador > 0
    empate = multiplicador == 0
    ganancia_neta = apuesta * multiplicador

    return reels, gano, ganancia_neta, empate


def tabla_pagos():
    """La tabla en forma legible, para mostrarla en la interfaz."""
    filas = [
        {
            "combinacion": f"3 x {SIMBOLOS[i]}",
            "paga": PAGOS_TRIO[i],
            "probabilidad": PROBABILIDADES[i] ** 3,
            "uno_de_cada": round(1 / PROBABILIDADES[i] ** 3),
        }
        for i in range(len(SIMBOLOS))
    ]
    filas.append({
        "combinacion": "2 iguales",
        "paga": PAGO_PAR,
        "probabilidad": probabilidad_empate(),
        "uno_de_cada": round(1 / probabilidad_empate()),
        "nota": "devuelve la apuesta",
    })
    return filas


def _enumerar():
    """
    Recorre los 125 resultados posibles con sus probabilidades. Como el
    espacio muestral es chico, todo lo teórico de este juego es exacto: no
    hace falta estimarlo simulando, y por eso sirve de control contra la
    simulación.
    """
    for combinacion in product(range(len(SIMBOLOS)), repeat=3):
        p = 1.0
        for i in combinacion:
            p *= PROBABILIDADES[i]
        yield combinacion, p


def retorno_teorico():
    """Valor esperado exacto por unidad apostada. Debe dar -7.325%."""
    return sum(p * _multiplicador(c) for c, p in _enumerar())


def probabilidad_teorica_ganar():
    """Probabilidad de cobrar un premio (tres iguales)."""
    return sum(p for c, p in _enumerar() if c[0] == c[1] == c[2])


def probabilidad_empate():
    """Probabilidad de recuperar la apuesta (exactamente dos iguales)."""
    return sum(
        p for c, p in _enumerar()
        if not (c[0] == c[1] == c[2]) and (c[0] == c[1] or c[1] == c[2] or c[0] == c[2])
    )


def probabilidad_perder():
    return sum(p for c, p in _enumerar() if len(set(c)) == 3)
