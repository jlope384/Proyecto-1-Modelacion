"""
Generación de variables aleatorias del casino.

Toda la aleatoriedad del proyecto pasa por este módulo, en dos capas:

    Capa 1 - Fuente uniforme U(0,1)
        Un generador congruencial lineal (LCG) implementado en el proyecto.
        No se usa `random` de Python en la lógica de los juegos: el LCG es
        reproducible (semilla), auditable y validable estadísticamente.

    Capa 2 - Métodos de generación de variables no uniformes
        A partir de esa fuente uniforme se construyen las variables que los
        juegos necesitan (carta, número de ruleta, cara de dado, símbolo de
        reel, tiempo entre llegadas) usando DOS métodos distintos:

            - Transformada inversa
            - Aceptación-rechazo

        Los dos métodos consumen la MISMA fuente uniforme, así que al
        compararlos la única diferencia es el método de transformación y la
        comparación es limpia.

Convención de la fuente: `uniforme()` devuelve u en [0, 1).
"""

import math
import time

# ---------------------------------------------------------------------------
# Capa 1: fuente uniforme
# ---------------------------------------------------------------------------


class LCG:
    """
    Generador congruencial lineal:   x_{n+1} = (a * x_n + c) mod m

    Parámetros por defecto (Numerical Recipes): a = 1664525, c = 1013904223,
    m = 2^32. Cumplen las condiciones de Hull-Dobell (c y m coprimos,
    a-1 divisible por todo factor primo de m, a-1 múltiplo de 4 porque m lo
    es), así que el generador tiene periodo completo m = 4,294,967,296.
    """

    def __init__(self, semilla=None, a=1664525, c=1013904223, m=2 ** 32):
        self.a = a
        self.c = c
        self.m = m
        self.semilla = semilla if semilla is not None else time.time_ns() % m
        self.estado = self.semilla
        self.n_uniformes = 0

    def uniforme(self):
        """Un valor u ~ U(0,1)."""
        self.estado = (self.a * self.estado + self.c) % self.m
        self.n_uniformes += 1
        return self.estado / self.m

    def uniformes(self, n):
        return [self.uniforme() for _ in range(n)]

    def reiniciar(self, semilla=None):
        self.semilla = semilla if semilla is not None else self.semilla
        self.estado = self.semilla
        self.n_uniformes = 0

    @property
    def periodo_teorico(self):
        return self.m

    def describir(self):
        return {
            "nombre": "LCG propio",
            "a": self.a,
            "c": self.c,
            "m": self.m,
            "semilla": self.semilla,
            "periodo_teorico": self.m,
            "uniformes_generados": self.n_uniformes,
        }


class FuentePython:
    """
    Fuente uniforme alternativa (Mersenne Twister de la librería estándar).
    Se usa solo como referencia de contraste al validar el LCG propio; los
    juegos no dependen de ella.
    """

    def __init__(self, semilla=None):
        import random as _random

        self._rng = _random.Random(semilla)
        self.semilla = semilla
        self.n_uniformes = 0

    def uniforme(self):
        self.n_uniformes += 1
        return self._rng.random()

    def uniformes(self, n):
        return [self.uniforme() for _ in range(n)]

    def reiniciar(self, semilla=None):
        import random as _random

        self._rng = _random.Random(semilla if semilla is not None else self.semilla)
        self.n_uniformes = 0

    def describir(self):
        # El periodo va como texto a propósito: 2^19937-1 tiene 6002 dígitos y
        # el serializador JSON de Python se niega a convertir enteros tan
        # grandes a cadena.
        return {
            "nombre": "Mersenne Twister (random de Python)",
            "semilla": self.semilla,
            "periodo_teorico": "2^19937 - 1",
            "uniformes_generados": self.n_uniformes,
        }


# ---------------------------------------------------------------------------
# Capa 2: métodos de generación
# ---------------------------------------------------------------------------

METODOS = ("inversa", "aceptacion_rechazo")

ETIQUETAS_METODO = {
    "inversa": "Transformada inversa",
    "aceptacion_rechazo": "Aceptación-rechazo",
}


# -- densidad y acumulada de la triangular, para generar y para validar -----


def densidad_triangular(x, a, moda, b):
    """f(x) de la Triangular(a, moda, b)."""
    if x < a or x > b:
        return 0.0
    if x < moda:
        return 2.0 * (x - a) / ((b - a) * (moda - a))
    if x > moda:
        return 2.0 * (b - x) / ((b - a) * (b - moda))
    return 2.0 / (b - a)


def acumulada_triangular(x, a, moda, b):
    """F(x) de la Triangular(a, moda, b)."""
    if x <= a:
        return 0.0
    if x >= b:
        return 1.0
    if x <= moda:
        return (x - a) ** 2 / ((b - a) * (moda - a))
    return 1.0 - (b - x) ** 2 / ((b - a) * (b - moda))


def inversa_triangular(u, a, moda, b):
    """F^-1(u) de la Triangular(a, moda, b), usada también por las pruebas."""
    corte = (moda - a) / (b - a)
    if u < corte:
        return a + math.sqrt(u * (b - a) * (moda - a))
    return b - math.sqrt((1.0 - u) * (b - a) * (b - moda))


def media_triangular(a, moda, b):
    return (a + moda + b) / 3.0


def varianza_triangular(a, moda, b):
    return (a * a + moda * moda + b * b - a * moda - a * b - moda * b) / 18.0


class Generador:
    """
    Fachada que envuelve una fuente uniforme y genera las variables aleatorias
    del casino con el método elegido.

    Lleva contadores (`n_variables`, `n_propuestas`, `n_rechazos`) que son la
    evidencia cuantitativa para comparar los dos métodos: cuántos uniformes
    cuesta cada variable generada y qué fracción de propuestas se descarta.
    """

    def __init__(self, metodo="inversa", semilla=None, fuente=None):
        if metodo not in METODOS:
            raise ValueError(f"Método inválido: {metodo!r}. Use uno de {METODOS}.")
        self.metodo = metodo
        self.fuente = fuente if fuente is not None else LCG(semilla)
        self.n_variables = 0     # variables no uniformes entregadas
        self.n_propuestas = 0    # propuestas evaluadas (solo aceptación-rechazo)
        self.n_rechazos = 0      # propuestas descartadas

    # -- utilidades ---------------------------------------------------------

    def uniforme(self):
        return self.fuente.uniforme()

    def reiniciar_contadores(self):
        self.n_variables = 0
        self.n_propuestas = 0
        self.n_rechazos = 0
        self.fuente.n_uniformes = 0

    def metricas(self):
        """Costo observado del método, para la comparación."""
        return {
            "metodo": self.metodo,
            "etiqueta": ETIQUETAS_METODO[self.metodo],
            "variables_generadas": self.n_variables,
            "uniformes_consumidos": self.fuente.n_uniformes,
            "uniformes_por_variable": (
                self.fuente.n_uniformes / self.n_variables if self.n_variables else 0.0
            ),
            "propuestas": self.n_propuestas,
            "rechazos": self.n_rechazos,
            "tasa_rechazo": (
                self.n_rechazos / self.n_propuestas if self.n_propuestas else 0.0
            ),
        }

    # -- variables discretas ------------------------------------------------

    def discreta(self, probabilidades):
        """
        Índice i con P(i) = probabilidades[i]. Es la variable base del casino:
        toda carta, número de ruleta, cara de dado y símbolo de reel se reduce
        a esto.
        """
        self.n_variables += 1
        if self.metodo == "inversa":
            return self._discreta_inversa(probabilidades)
        return self._discreta_aceptacion_rechazo(probabilidades)

    def _discreta_inversa(self, p):
        """
        Transformada inversa para una discreta: se recorre la acumulada
        F(i) = p_0 + ... + p_i y se devuelve el primer i con u < F(i).

        Costo: exactamente 1 uniforme por variable, pero hay que recorrer la
        acumulada (O(k) en el peor caso, y O(k) siempre que la distribución
        cambie entre extracciones, como pasa en el zapato de blackjack).
        """
        u = self.fuente.uniforme()
        acumulada = 0.0
        for i, pi in enumerate(p):
            acumulada += pi
            if u < acumulada:
                return i
        return len(p) - 1  # blindaje ante error de redondeo en la acumulada

    def _discreta_aceptacion_rechazo(self, p):
        """
        Aceptación-rechazo con propuesta uniforme discreta q(j) = 1/k:

            1. Proponer j ~ U{0, ..., k-1}
            2. Aceptar j con probabilidad p_j / p_max

        La constante de mayoración es c = k * p_max (porque p_j <= c * q_j),
        y la probabilidad de aceptar en un intento es 1/c. Costo: 2 uniformes
        por intento, pero NO necesita la acumulada, así que cada intento es
        O(1) sin importar cómo cambie la distribución.

        El precio es la eficiencia: mientras más desbalanceada la
        distribución (p_max grande frente al promedio), más se rechaza.
        """
        k = len(p)
        p_max = max(p)
        if p_max <= 0:
            raise ValueError("La distribución no tiene masa positiva.")
        while True:
            u1 = self.fuente.uniforme()
            j = int(u1 * k)
            if j >= k:  # solo si u1 llegara a 1.0 por redondeo
                j = k - 1
            u2 = self.fuente.uniforme()
            self.n_propuestas += 1
            if u2 * p_max <= p[j]:
                return j
            self.n_rechazos += 1

    def entero(self, a, b):
        """Entero uniforme en [a, b] (ambos inclusive)."""
        k = b - a + 1
        return a + self.discreta([1.0 / k] * k)

    def elegir(self, elementos, pesos=None):
        """Un elemento de la lista, con pesos opcionales (no normalizados)."""
        if pesos is None:
            probs = [1.0 / len(elementos)] * len(elementos)
        else:
            total = float(sum(pesos))
            probs = [w / total for w in pesos]
        return elementos[self.discreta(probs)]

    # -- variables continuas ------------------------------------------------

    def exponencial(self, tasa):
        """
        Tiempo entre eventos ~ Exp(tasa). Se usa para las llegadas de
        jugadores al casino (proceso de Poisson).
        """
        if tasa <= 0:
            raise ValueError("La tasa debe ser positiva.")
        self.n_variables += 1
        if self.metodo == "inversa":
            return self._exponencial_inversa(tasa)
        return self._exponencial_aceptacion_rechazo(tasa)

    def _exponencial_inversa(self, tasa):
        """
        F(x) = 1 - e^{-tasa*x}  =>  x = -ln(1-u)/tasa

        Se usa (1-u) y no u para evitar ln(0) cuando el LCG devuelve 0.
        Exacta y con costo fijo de 1 uniforme.
        """
        u = self.fuente.uniforme()
        return -math.log(1.0 - u) / tasa

    def uniforme_continua(self, a, b):
        """X ~ U(a, b). Un uniforme escalado; los dos métodos coinciden."""
        self.n_variables += 1
        return a + (b - a) * self.fuente.uniforme()

    def triangular(self, a, moda, b):
        """
        X ~ Triangular(a, moda, b). En el piso se usa para bankroll, apuesta,
        duración de ronda y estadía de cada cliente.

        Es el mejor caso del proyecto para comparar los dos métodos en una
        variable CONTINUA, porque el costo teórico de aceptación-rechazo sale
        exacto y no depende de dónde esté la moda: la densidad máxima es
        f(moda) = 2/(b-a) y la propuesta uniforme tiene densidad 1/(b-a), así
        que la constante de mayoración es

            c = f_max / q = 2   siempre

        o sea que acepta exactamente la mitad de las propuestas y gasta 4
        uniformes por variable, contra 1 de la transformada inversa.
        """
        if not a <= moda <= b or a >= b:
            raise ValueError("Se requiere a <= moda <= b con a < b.")
        self.n_variables += 1
        if self.metodo == "inversa":
            return self._triangular_inversa(a, moda, b)
        return self._triangular_aceptacion_rechazo(a, moda, b)

    def _triangular_inversa(self, a, moda, b):
        """
        La acumulada de la triangular se invierte por tramos:

            u < (moda-a)/(b-a)  ->  x = a + sqrt(u (b-a)(moda-a))
            si no               ->  x = b - sqrt((1-u)(b-a)(b-moda))

        Exacta y con costo fijo de 1 uniforme.
        """
        u = self.fuente.uniforme()
        corte = (moda - a) / (b - a)
        if u < corte:
            return a + math.sqrt(u * (b - a) * (moda - a))
        return b - math.sqrt((1.0 - u) * (b - a) * (b - moda))

    def _triangular_aceptacion_rechazo(self, a, moda, b):
        """
        Propuesta uniforme en [a, b], aceptar con probabilidad f(x)/f(moda).
        No necesita invertir nada (útil cuando la acumulada no tiene forma
        cerrada), pero descarta la mitad de las propuestas.
        """
        altura = 2.0 / (b - a)  # f(moda), el máximo de la densidad
        while True:
            x = a + (b - a) * self.fuente.uniforme()
            u2 = self.fuente.uniforme()
            self.n_propuestas += 1
            if u2 * altura <= densidad_triangular(x, a, moda, b):
                return x
            self.n_rechazos += 1

    def _exponencial_aceptacion_rechazo(self, tasa, cola=12.0):
        """
        Aceptación-rechazo sobre la exponencial truncada en T = cola/tasa,
        con propuesta uniforme en [0, T]:

            proponer x ~ U(0, T), aceptar con probabilidad f(x)/f(0) = e^{-tasa*x}

        La truncación descarta una masa e^{-12} ≈ 6e-6, despreciable frente
        al ruido de la simulación. Sirve para mostrar que el mismo método de
        aceptación-rechazo aplica a variables continuas, aunque para la
        exponencial la inversa es claramente superior (existe forma cerrada y
        no hay rechazo). Ese contraste es parte de la comparación.
        """
        T = cola / tasa
        while True:
            u1 = self.fuente.uniforme()
            x = u1 * T
            u2 = self.fuente.uniforme()
            self.n_propuestas += 1
            if u2 <= math.exp(-tasa * x):
                return x
            self.n_rechazos += 1


# ---------------------------------------------------------------------------
# Generador global de la sesión interactiva
# ---------------------------------------------------------------------------
#
# Los juegos en modo interactivo (un jugador apostando desde el frontend)
# comparten este generador. Las simulaciones crean el suyo propio, con su
# semilla, para ser reproducibles y no interferir con la partida del usuario.

GENERADOR = Generador(metodo="inversa")


def generador_actual():
    return GENERADOR


def configurar_generador(metodo=None, semilla=None):
    """Cambia el método o la semilla del generador interactivo."""
    global GENERADOR
    metodo = metodo or GENERADOR.metodo
    GENERADOR = Generador(metodo=metodo, semilla=semilla)
    return GENERADOR


def resolver(gen):
    """Devuelve el generador recibido o el global si viene None."""
    return gen if gen is not None else GENERADOR
