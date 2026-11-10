"""
Dados (dos dados de seis caras).

Modelo de aleatoriedad: cada dado es una discreta uniforme sobre {1..6}, y se
generan de forma independiente. La suma NO se genera directamente: se obtiene
sumando los dos dados, así que su distribución triangular (2 con
probabilidad 1/36, 7 con 6/36) emerge del modelo en vez de estar cableada.
Eso permite validarla con chi-cuadrado contra la teórica.
"""

from . import rng

CARAS = 6
PROBABILIDADES_DADO = [1.0 / CARAS] * CARAS

# Pago aproximado según la probabilidad real de cada suma con 2 dados,
# para que el juego sea razonablemente "justo" (misma idea que la ruleta por número).
PAGOS_SUMA = {
    2: 35, 3: 17, 4: 11, 5: 8, 6: 6.5, 7: 5,
    8: 6.5, 9: 8, 10: 11, 11: 17, 12: 35,
}

# Distribución teórica de la suma de dos dados (índice = suma - 2).
PROBABILIDADES_SUMA = [
    1 / 36, 2 / 36, 3 / 36, 4 / 36, 5 / 36, 6 / 36,
    5 / 36, 4 / 36, 3 / 36, 2 / 36, 1 / 36,
]

# Apuesta "field" (tipo craps): sumas ganadoras de una sola tirada.
FIELD = (2, 3, 4, 9, 10, 11, 12)


def tirar(generador=None):
    gen = rng.resolver(generador)
    d1 = 1 + gen.discreta(PROBABILIDADES_DADO)
    d2 = 1 + gen.discreta(PROBABILIDADES_DADO)
    return d1, d2, d1 + d2


def jugar(apuesta, tipo, valor, generador=None):
    """
    tipo "suma": valor 2-12, paga según PAGOS_SUMA
    tipo "par_impar": valor "par"/"impar", paga 1:1
    tipo "field": (valor se ignora) gana con 2,3,4,9,10,11,12; paga 1:1,
        salvo 2 y 12 que pagan 2:1; pierde con 5,6,7,8. Ventaja de la casa 1/18.
    Devuelve (dado1, dado2, suma, gano, ganancia_neta).
    """
    d1, d2, suma = tirar(generador)
    gano = False
    multiplicador = 0

    if tipo == "suma":
        gano = suma == int(valor)
        multiplicador = PAGOS_SUMA.get(suma, 0)
    elif tipo == "par_impar":
        es_par = suma % 2 == 0
        gano = (es_par and valor == "par") or (not es_par and valor == "impar")
        multiplicador = 1
    elif tipo == "field":
        gano = suma in FIELD
        multiplicador = 2 if suma in (2, 12) else 1
    else:
        raise ValueError("Tipo de apuesta inválido")

    ganancia_neta = apuesta * multiplicador if gano else -apuesta
    return d1, d2, suma, gano, ganancia_neta


def probabilidad_teorica(tipo, valor):
    if tipo == "suma":
        return PROBABILIDADES_SUMA[int(valor) - 2]
    if tipo == "par_impar":
        return 0.5
    if tipo == "field":
        return 16 / 36
    raise ValueError("Tipo de apuesta inválido")


def retorno_teorico(tipo, valor):
    if tipo == "field":
        return (14 * 1 + 2 * 2 - 20) / 36
    p = probabilidad_teorica(tipo, valor)
    pago = PAGOS_SUMA[int(valor)] if tipo == "suma" else 1
    return p * pago - (1 - p)
