"""
Ruleta europea (0-36).

Modelo de aleatoriedad: el número que sale es una variable aleatoria discreta
uniforme sobre 37 valores, P(i) = 1/37 para todo i. Se genera con el método
configurado (transformada inversa o aceptación-rechazo) sobre el LCG propio.

Como la distribución es uniforme, la aceptación-rechazo con propuesta uniforme
acepta siempre (p_j / p_max = 1): es el caso donde los dos métodos coinciden
en calidad y solo se diferencian en el costo por uniforme. Sirve de control
en la comparación, frente a la tragamonedas y el blackjack, que sí tienen
distribuciones desbalanceadas.
"""

from . import rng

CASILLAS = 37  # 0 a 36
NUMEROS_ROJOS = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

PROBABILIDADES = [1.0 / CASILLAS] * CASILLAS


def girar(generador=None):
    """Número de la ruleta como discreta uniforme sobre {0, ..., 36}."""
    gen = rng.resolver(generador)
    return gen.discreta(PROBABILIDADES)


def color_de(numero):
    if numero == 0:
        return "verde"
    return "rojo" if numero in NUMEROS_ROJOS else "negro"


def jugar(apuesta, tipo, valor, generador=None):
    """
    tipo "color": valor "rojo"/"negro" (paga 1:1)
    tipo "paridad": valor "par"/"impar" (paga 1:1, el 0 siempre pierde)
    tipo "numero": valor 0-36 (paga 35:1)
    Devuelve (numero_salido, color, gano, ganancia_neta).
    """
    numero = girar(generador)
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


def probabilidad_teorica(tipo, valor):
    """Probabilidad exacta de ganar, para contrastar contra lo simulado."""
    if tipo == "color":
        return 18 / 37 if valor in ("rojo", "negro") else 0.0
    if tipo == "paridad":
        return 18 / 37
    if tipo == "numero":
        return 1 / 37
    raise ValueError("Tipo de apuesta inválido")


def retorno_teorico(tipo, valor):
    """
    Valor esperado por unidad apostada. En la ruleta europea es -1/37 =
    -2.70% para toda apuesta: esa es la ventaja de la casa.
    """
    p = probabilidad_teorica(tipo, valor)
    pago = 35 if tipo == "numero" else 1
    return p * pago - (1 - p)
