"""
Blackjack como juego del casino.

Antes este archivo era un script de consola independiente (con input() y
print()). Ahora es un módulo sin efectos de consola: la lógica devuelve
estados y resultados, el servidor Flask los expone y el frontend los muestra,
igual que ruleta, dados y tragamonedas.

Modelo de aleatoriedad
----------------------
La única fuente de azar es la carta que sale del zapato. Se modela como una
variable aleatoria discreta sobre los 13 rangos, con probabilidades
proporcionales a las cartas que QUEDAN en el zapato:

        P(rango r) = restantes[r] / total_restantes

Es decir, muestreo sin reemplazo: la distribución cambia después de cada
carta. Eso es lo que hace al blackjack el juego más interesante del proyecto
para comparar métodos de generación:

    - Transformada inversa: 1 uniforme por carta, pero hay que recorrer la
      acumulada de 13 rangos, y como las probabilidades cambian en cada
      extracción, la acumulada no se puede precalcular ni reutilizar.

    - Aceptación-rechazo: no necesita la acumulada (solo el máximo), pero
      gasta 2 uniformes por intento y descarta parte de las propuestas.

El zapato se baraja de nuevo al pasar la marca de penetración, tal como en un
casino real, lo que devuelve la distribución a su estado inicial.
"""

from . import rng

RANGOS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

VALORES = {
    "A": 11, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
    "8": 8, "9": 9, "10": 10, "J": 10, "Q": 10, "K": 10,
}

PAGO_BLACKJACK = 1.5   # el 21 natural paga 3:2
BARAJAS_POR_DEFECTO = 6
PENETRACION_POR_DEFECTO = 0.75  # se rebaraja tras consumir el 75% del zapato

ESTRATEGIAS = ("basica", "umbral", "dealer")


# ---------------------------------------------------------------------------
# Valor de una mano
# ---------------------------------------------------------------------------


def total(mano):
    """
    Total de la mano contando los ases como 11 y bajándolos a 1 mientras se
    pase de 21 (un as "blando" vale 11 solo si cabe).
    """
    suma = 0
    ases = 0
    for carta in mano:
        suma += VALORES[carta]
        if carta == "A":
            ases += 1
    while suma > 21 and ases:
        suma -= 10
        ases -= 1
    return suma


def es_blanda(mano):
    """True si algún as sigue valiendo 11 (la mano no se puede pasar al pedir)."""
    suma = sum(VALORES[c] for c in mano)
    ases = sum(1 for c in mano if c == "A")
    while suma > 21 and ases:
        suma -= 10
        ases -= 1
    return ases > 0 and suma <= 21


def es_blackjack(mano):
    return len(mano) == 2 and total(mano) == 21


def se_paso(mano):
    return total(mano) > 21


# ---------------------------------------------------------------------------
# Zapato: la variable aleatoria del juego
# ---------------------------------------------------------------------------


class Zapato:
    """
    Zapato de n barajas con muestreo sin reemplazo.

    Guarda cuántas cartas quedan de cada rango y arma en cada extracción el
    vector de probabilidades que le entrega al generador. Se rebaraja al
    cruzar la marca de penetración.
    """

    def __init__(self, generador=None, n_barajas=BARAJAS_POR_DEFECTO,
                 penetracion=PENETRACION_POR_DEFECTO):
        self.gen = rng.resolver(generador)
        self.n_barajas = n_barajas
        self.penetracion = penetracion
        self.n_barajadas = 0
        self.cartas_repartidas = 0
        self.barajar()

    def barajar(self):
        por_rango = 4 * self.n_barajas
        self.restantes = {r: por_rango for r in RANGOS}
        self.total_restantes = 52 * self.n_barajas
        self.corte = int(52 * self.n_barajas * (1.0 - self.penetracion))
        self.n_barajadas += 1

    def necesita_barajar(self):
        return self.total_restantes <= self.corte

    def barajar_si_toca(self):
        """Se llama al inicio de cada mano, nunca a media mano."""
        if self.necesita_barajar():
            self.barajar()
            return True
        return False

    def probabilidades(self):
        t = self.total_restantes
        return [self.restantes[r] / t for r in RANGOS]

    def sacar(self):
        """Una carta, generada con el método configurado en el generador."""
        if self.total_restantes <= 0:
            self.barajar()
        indice = self.gen.discreta(self.probabilidades())
        rango = RANGOS[indice]
        self.restantes[rango] -= 1
        self.total_restantes -= 1
        self.cartas_repartidas += 1
        return rango

    def composicion(self):
        return {
            "barajas": self.n_barajas,
            "cartas_restantes": self.total_restantes,
            "restantes_por_rango": dict(self.restantes),
            "cartas_repartidas": self.cartas_repartidas,
            "veces_barajado": self.n_barajadas,
        }


# ---------------------------------------------------------------------------
# Estrategias automáticas (para la simulación)
# ---------------------------------------------------------------------------


def _valor_carta_visible(carta):
    return VALORES[carta]


def decidir(mano, carta_visible_dealer, estrategia="basica", umbral=17,
            puede_doblar=False):
    """
    Decisión del jugador simulado: "pedir", "plantarse" o "doblar".

    - "basica": estrategia básica simplificada (sin partir pares), que
      distingue manos duras y blandas y toma en cuenta la carta visible del
      dealer. Es la que deja la ventaja de la casa más baja.
    - "umbral": pedir mientras el total sea menor al umbral. Sirve para
      barrer umbrales de 12 a 20 y ver cómo cambia el retorno.
    - "dealer": imitar al dealer (pedir con menos de 17). Es el jugador
      ingenuo, y su retorno es notablemente peor.
    """
    t = total(mano)
    if t >= 21:
        return "plantarse"

    if estrategia == "umbral":
        return "pedir" if t < umbral else "plantarse"

    if estrategia == "dealer":
        return "pedir" if t < 17 else "plantarse"

    # estrategia básica simplificada
    visible = _valor_carta_visible(carta_visible_dealer)
    dealer_debil = 2 <= visible <= 6

    if puede_doblar and len(mano) == 2:
        if not es_blanda(mano):
            if t == 11:
                return "doblar"
            if t == 10 and visible <= 9:
                return "doblar"
            if t == 9 and 3 <= visible <= 6:
                return "doblar"
        else:
            if 13 <= t <= 18 and 4 <= visible <= 6:
                return "doblar"

    if es_blanda(mano):
        if t >= 19:
            return "plantarse"
        if t == 18:
            return "plantarse" if visible <= 8 else "pedir"
        return "pedir"

    if t >= 17:
        return "plantarse"
    if t >= 13:
        return "plantarse" if dealer_debil else "pedir"
    if t == 12:
        return "plantarse" if 4 <= visible <= 6 else "pedir"
    return "pedir"


def jugar_dealer(mano, zapato, planta_en_blanda_17=True):
    """
    El dealer no decide nada: pide con menos de 17 y se planta en 17 o más.
    Con `planta_en_blanda_17=False` pide también con 17 blando (regla H17).
    """
    while True:
        t = total(mano)
        if t < 17:
            mano.append(zapato.sacar())
            continue
        if t == 17 and es_blanda(mano) and not planta_en_blanda_17:
            mano.append(zapato.sacar())
            continue
        return mano


# ---------------------------------------------------------------------------
# Una mano completa (para la simulación automática)
# ---------------------------------------------------------------------------


def jugar_mano(apuesta, zapato, estrategia="basica", umbral=17,
               permitir_doblar=True):
    """
    Reparte y resuelve una mano completa contra el dealer.

    Devuelve un dict con la mano del jugador, la del dealer, el desenlace
    ("blackjack", "gana", "pierde", "empate", "se_paso", "dealer_se_paso") y
    la ganancia NETA respecto a la apuesta (negativa si perdió).
    """
    zapato.barajar_si_toca()

    mano_jugador = [zapato.sacar(), zapato.sacar()]
    mano_dealer = [zapato.sacar(), zapato.sacar()]
    apuesta_final = apuesta
    dobló = False

    bj_jugador = es_blackjack(mano_jugador)
    bj_dealer = es_blackjack(mano_dealer)

    if bj_jugador or bj_dealer:
        if bj_jugador and bj_dealer:
            resultado, ganancia = "empate", 0.0
        elif bj_jugador:
            resultado, ganancia = "blackjack", apuesta * PAGO_BLACKJACK
        else:
            resultado, ganancia = "pierde", -apuesta
        return _resumen(mano_jugador, mano_dealer, resultado, ganancia,
                        apuesta_final, dobló)

    # turno del jugador
    while True:
        accion = decidir(
            mano_jugador, mano_dealer[0], estrategia, umbral,
            puede_doblar=permitir_doblar and not dobló,
        )
        if accion == "doblar":
            apuesta_final = apuesta * 2
            dobló = True
            mano_jugador.append(zapato.sacar())
            break
        if accion == "pedir":
            mano_jugador.append(zapato.sacar())
            if se_paso(mano_jugador):
                return _resumen(mano_jugador, mano_dealer, "se_paso",
                                -apuesta_final, apuesta_final, dobló)
            continue
        break

    if se_paso(mano_jugador):
        return _resumen(mano_jugador, mano_dealer, "se_paso", -apuesta_final,
                        apuesta_final, dobló)

    # turno del dealer
    jugar_dealer(mano_dealer, zapato)
    return _resolver(mano_jugador, mano_dealer, apuesta_final, dobló)


def _resolver(mano_jugador, mano_dealer, apuesta, dobló):
    tj = total(mano_jugador)
    td = total(mano_dealer)
    if td > 21:
        return _resumen(mano_jugador, mano_dealer, "dealer_se_paso", apuesta, apuesta, dobló)
    if tj > td:
        return _resumen(mano_jugador, mano_dealer, "gana", apuesta, apuesta, dobló)
    if tj < td:
        return _resumen(mano_jugador, mano_dealer, "pierde", -apuesta, apuesta, dobló)
    return _resumen(mano_jugador, mano_dealer, "empate", 0.0, apuesta, dobló)


def _resumen(mano_jugador, mano_dealer, resultado, ganancia, apuesta, dobló):
    return {
        "mano_jugador": list(mano_jugador),
        "mano_dealer": list(mano_dealer),
        "total_jugador": total(mano_jugador),
        "total_dealer": total(mano_dealer),
        "resultado": resultado,
        "gano": ganancia > 0,
        "empate": ganancia == 0,
        "ganancia": ganancia,
        "apuesta": apuesta,
        "doblo": dobló,
        "cartas_usadas": len(mano_jugador) + len(mano_dealer),
    }


# ---------------------------------------------------------------------------
# Interfaz compatible con los otros juegos
# ---------------------------------------------------------------------------

_ZAPATO_AUTOMATICO = None


def jugar(apuesta, tipo="basica", valor=17, generador=None, zapato=None):
    """
    Misma forma que ruleta.jugar / dados.jugar / tragamonedas.jugar, para que
    la simulación pueda tratar a los cuatro juegos igual.

    `tipo` es la estrategia y `valor` el umbral (cuando la estrategia lo usa).
    Devuelve (detalle, gano, ganancia_neta).
    """
    global _ZAPATO_AUTOMATICO
    if zapato is None:
        if _ZAPATO_AUTOMATICO is None:
            _ZAPATO_AUTOMATICO = Zapato(generador)
        zapato = _ZAPATO_AUTOMATICO

    estrategia = tipo if tipo in ESTRATEGIAS else "basica"
    umbral = int(valor) if valor not in (None, "") else 17
    detalle = jugar_mano(apuesta, zapato, estrategia, umbral)
    return detalle, detalle["gano"], detalle["ganancia"]


# ---------------------------------------------------------------------------
# Mesa interactiva (el usuario decide desde el frontend)
# ---------------------------------------------------------------------------


class Mesa:
    """
    Estado de una partida interactiva: reparte, deja pedir/plantarse/doblar y
    liquida. Vive en memoria del servidor, igual que el saldo del jugador.
    """

    def __init__(self, generador=None, n_barajas=BARAJAS_POR_DEFECTO):
        self.zapato = Zapato(generador, n_barajas=n_barajas)
        self.reiniciar()

    def reiniciar(self):
        self.mano_jugador = []
        self.mano_dealer = []
        self.apuesta = 0.0
        self.en_juego = False
        self.doblo = False
        self.resultado = None
        self.ganancia = 0.0
        self.mensaje = "Haz tu apuesta para repartir."

    # -- acciones -----------------------------------------------------------

    def nueva_mano(self, apuesta):
        rebarajo = self.zapato.barajar_si_toca()
        self.mano_jugador = [self.zapato.sacar(), self.zapato.sacar()]
        self.mano_dealer = [self.zapato.sacar(), self.zapato.sacar()]
        self.apuesta = float(apuesta)
        self.en_juego = True
        self.doblo = False
        self.resultado = None
        self.ganancia = 0.0
        self.mensaje = "Zapato rebarajado. " if rebarajo else ""

        bj_jugador = es_blackjack(self.mano_jugador)
        bj_dealer = es_blackjack(self.mano_dealer)
        if bj_jugador or bj_dealer:
            if bj_jugador and bj_dealer:
                self._terminar("empate", 0.0, "Blackjack de ambos: empate.")
            elif bj_jugador:
                self._terminar("blackjack", self.apuesta * PAGO_BLACKJACK,
                               "¡Blackjack! Paga 3:2.")
            else:
                self._terminar("pierde", -self.apuesta,
                               "El dealer tiene blackjack.")
        else:
            self.mensaje += "Tu turno: pedir, plantarte o doblar."
        return self.estado()

    def pedir(self):
        if not self.en_juego:
            raise ValueError("No hay una mano en curso.")
        self.mano_jugador.append(self.zapato.sacar())
        if se_paso(self.mano_jugador):
            self._terminar("se_paso", -self.apuesta,
                           f"Te pasaste con {total(self.mano_jugador)}.")
        elif total(self.mano_jugador) == 21:
            return self.plantarse()
        else:
            self.mensaje = f"Llevas {total(self.mano_jugador)}."
        return self.estado()

    def doblar(self):
        if not self.en_juego:
            raise ValueError("No hay una mano en curso.")
        if len(self.mano_jugador) != 2:
            raise ValueError("Solo se puede doblar con las dos primeras cartas.")
        self.apuesta *= 2
        self.doblo = True
        self.mano_jugador.append(self.zapato.sacar())
        if se_paso(self.mano_jugador):
            self._terminar("se_paso", -self.apuesta,
                           f"Doblaste y te pasaste con {total(self.mano_jugador)}.")
            return self.estado()
        return self.plantarse()

    def plantarse(self):
        if not self.en_juego:
            raise ValueError("No hay una mano en curso.")
        jugar_dealer(self.mano_dealer, self.zapato)
        resumen = _resolver(self.mano_jugador, self.mano_dealer, self.apuesta, self.doblo)
        self._terminar(resumen["resultado"], resumen["ganancia"],
                       _mensaje_final(resumen))
        return self.estado()

    # -- estado -------------------------------------------------------------

    def _terminar(self, resultado, ganancia, mensaje):
        self.en_juego = False
        self.resultado = resultado
        self.ganancia = ganancia
        self.mensaje = (self.mensaje or "") + mensaje

    def estado(self):
        oculta = self.en_juego and len(self.mano_dealer) >= 2
        return {
            "en_juego": self.en_juego,
            "apuesta": self.apuesta,
            "mano_jugador": list(self.mano_jugador),
            "total_jugador": total(self.mano_jugador) if self.mano_jugador else 0,
            "mano_jugador_blanda": es_blanda(self.mano_jugador) if self.mano_jugador else False,
            # mientras la mano está viva solo se ve la primera carta del dealer
            "mano_dealer": [self.mano_dealer[0], "?"] if oculta else list(self.mano_dealer),
            "total_dealer": (
                VALORES[self.mano_dealer[0]] if oculta
                else (total(self.mano_dealer) if self.mano_dealer else 0)
            ),
            "carta_dealer_oculta": oculta,
            "puede_doblar": self.en_juego and len(self.mano_jugador) == 2,
            "resultado": self.resultado,
            "ganancia": self.ganancia,
            "doblo": self.doblo,
            "mensaje": self.mensaje,
            "zapato": self.zapato.composicion(),
        }


def _mensaje_final(resumen):
    tj, td = resumen["total_jugador"], resumen["total_dealer"]
    if resumen["resultado"] == "dealer_se_paso":
        return f"El dealer se pasó con {td}. ¡Ganaste!"
    if resumen["resultado"] == "gana":
        return f"{tj} contra {td}. ¡Ganaste!"
    if resumen["resultado"] == "pierde":
        return f"{tj} contra {td}. Perdiste."
    return f"{tj} contra {td}. Empate."
