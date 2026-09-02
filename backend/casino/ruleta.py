import random

NUMEROS_ROJOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}


def girar():
    return random.randint(0, 36)


def color_de(numero):
    if numero == 0:
        return "verde"
    return "rojo" if numero in NUMEROS_ROJOS else "negro"


def jugar(apuesta, tipo, valor):
    """
    tipo "color": valor "rojo"/"negro" (paga 1:1)
    tipo "paridad": valor "par"/"impar" (paga 1:1, el 0 siempre pierde)
    tipo "numero": valor 0-36 (paga 35:1)
    Devuelve (numero_salido, color, gano, ganancia_neta).
    """
    numero = girar()
    color = color_de(numero)
    gano = False
    multiplicador = 0

    if tipo == "color":
        gano = color == valor
        multiplicador = 1
    elif tipo == "paridad":
        if numero != 0:
            es_par = numero % 2 == 0
            gano = (es_par and valor == "par") or (not es_par and valor == "impar")
        multiplicador = 1
    elif tipo == "numero":
        gano = numero == int(valor)
        multiplicador = 35
    else:
        raise ValueError("Tipo de apuesta inválido")

    ganancia_neta = apuesta * multiplicador if gano else -apuesta
    return numero, color, gano, ganancia_neta
