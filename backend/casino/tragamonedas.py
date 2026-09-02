import random

SIMBOLOS = ["🍒", "🍋", "🔔", "⭐", "7️⃣"]
PESOS = [35, 30, 20, 10, 5]  # 7️⃣ es el símbolo más raro


def girar_reel():
    return random.choices(SIMBOLOS, weights=PESOS, k=1)[0]


def jugar(apuesta):
    """
    3 iguales con 7️⃣: paga x10
    3 iguales (otro símbolo): paga x5
    2 iguales: paga x2
    sin coincidencias: pierde
    Devuelve (reels, gano, ganancia_neta).
    """
    reels = [girar_reel() for _ in range(3)]
    multiplicador = 0

    if reels[0] == reels[1] == reels[2]:
        multiplicador = 10 if reels[0] == "7️⃣" else 5
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        multiplicador = 2

    gano = multiplicador > 0
    ganancia_neta = apuesta * multiplicador if gano else -apuesta
    return reels, gano, ganancia_neta
