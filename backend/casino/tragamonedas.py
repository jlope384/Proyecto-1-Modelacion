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
"""

from . import rng

SIMBOLOS = ["🍒", "🍋", "🔔", "⭐", "7️⃣"]
PESOS = [35, 30, 20, 10, 5]  # 7️⃣ es el símbolo más raro

_TOTAL_PESOS = float(sum(PESOS))
PROBABILIDADES = [w / _TOTAL_PESOS for w in PESOS]


def girar_reel(generador=None):
    gen = rng.resolver(generador)
    return SIMBOLOS[gen.discreta(PROBABILIDADES)]


def jugar(apuesta, generador=None):
    """
    3 iguales con 7️⃣: paga x10
    3 iguales (otro símbolo): paga x5
    2 iguales: paga x2
    sin coincidencias: pierde
    Devuelve (reels, gano, ganancia_neta).
    """
    reels = [girar_reel(generador) for _ in range(3)]
    multiplicador = 0

    if reels[0] == reels[1] == reels[2]:
        multiplicador = 10 if reels[0] == "7️⃣" else 5
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        multiplicador = 2

    gano = multiplicador > 0
    ganancia_neta = apuesta * multiplicador if gano else -apuesta
    return reels, gano, ganancia_neta


def retorno_teorico():
    """
    Valor esperado exacto por unidad apostada, enumerando los 125 resultados
    posibles con sus probabilidades. Es la referencia contra la cual se
    compara lo que arroja la simulación.
    """
    esperado = 0.0
    for i, pi in enumerate(PROBABILIDADES):
        for j, pj in enumerate(PROBABILIDADES):
            for k, pk in enumerate(PROBABILIDADES):
                p = pi * pj * pk
                if i == j == k:
                    mult = 10 if SIMBOLOS[i] == "7️⃣" else 5
                elif i == j or j == k or i == k:
                    mult = 2
                else:
                    mult = -1
                esperado += p * mult
    return esperado


def probabilidad_teorica_ganar():
    """Probabilidad de que salgan al menos dos símbolos iguales."""
    p_todos_distintos = 0.0
    for i, pi in enumerate(PROBABILIDADES):
        for j, pj in enumerate(PROBABILIDADES):
            for k, pk in enumerate(PROBABILIDADES):
                if i != j and j != k and i != k:
                    p_todos_distintos += pi * pj * pk
    return 1.0 - p_todos_distintos
