import random

# Pago aproximado según la probabilidad real de cada suma con 2 dados,
# para que el juego sea razonablemente "justo" (misma idea que la ruleta por número).
PAGOS_SUMA = {
    2: 35, 3: 17, 4: 11, 5: 8, 6: 6.5, 7: 5,
    8: 6.5, 9: 8, 10: 11, 11: 17, 12: 35,
}


def tirar():
    d1, d2 = random.randint(1, 6), random.randint(1, 6)
    return d1, d2, d1 + d2


def jugar(apuesta, tipo, valor):
    """
    tipo "suma": valor 2-12, paga según PAGOS_SUMA
    tipo "par_impar": valor "par"/"impar", paga 1:1
    Devuelve (dado1, dado2, suma, gano, ganancia_neta).
    """
    d1, d2, suma = tirar()
    gano = False
    multiplicador = 0

    if tipo == "suma":
        gano = suma == int(valor)
        multiplicador = PAGOS_SUMA.get(suma, 0)
    elif tipo == "par_impar":
        es_par = suma % 2 == 0
        gano = (es_par and valor == "par") or (not es_par and valor == "impar")
        multiplicador = 1
    else:
        raise ValueError("Tipo de apuesta inválido")

    ganancia_neta = apuesta * multiplicador if gano else -apuesta
    return d1, d2, suma, gano, ganancia_neta
