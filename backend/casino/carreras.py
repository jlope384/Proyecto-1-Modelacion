"""
Carrera de caballos.

Adaptado del script de consola original (`Horse Race.py`), que dibujaba la
pista en ASCII con `os.system('clear')` y pedía las apuestas con `input()`.
Aquí es un módulo sin efectos de consola: devuelve estados y resultados, y el
frontend se encarga de dibujar.

Dos cambios de MODELO respecto al original, ambos necesarios para que la
carrera sirva como sistema simulado:

1. La carrera original era DETERMINISTA. Cada caballo avanzaba exactamente su
   velocidad en cada paso (la mitad al quedarse sin energía), así que el
   ganador quedaba decidido en el instante en que se generaban los caballos:
   correr la carrera no era más que ejecutar una fórmula. Aquí cada tranco
   lleva un factor de ruido aleatorio, de modo que un caballo rápido puede
   perder y la probabilidad de ganar de cada uno solo se puede estimar
   simulando.

2. El pago original era 1:1 con 10 caballos, o sea un retorno esperado de
   -80% para el jugador. Aquí las cuotas se calculan por Monte Carlo a partir
   de la probabilidad estimada de cada caballo, con un margen de casa
   configurable. Ver `calcular_cuotas`.

Fuentes de aleatoriedad
-----------------------
    Velocidad base del caballo ~ Triangular(3, 4, 6)
        Se sortea una vez, al armar el lote, y define qué tan bueno es el
        caballo. La mayoría son del montón y pocos son muy rápidos, que es
        justo la forma de la triangular. El original usaba una uniforme,
        donde un caballo excepcional es tan común como uno mediocre.

    Energía (trancos a fondo) ~ Uniforme(8, 20)
        Se conserva la idea del original. Al agotarse, el caballo baja a la
        mitad de su velocidad.

    Forma del día ~ Triangular(0.65, 1, 1.35), por caballo y POR CARRERA
        Multiplica la velocidad durante toda la carrera. Es la fuente de
        incertidumbre que de verdad hace competitiva la prueba, y hay una
        razón matemática para que exista, no es adorno: el ruido tranco a
        tranco se promedia. Sobre 18 pasos, un ruido con desviación 0.14 por
        tranco deja una desviación de solo 0.14/sqrt(18) = 3.4% en la
        distancia total, muy poco frente al 30-40% en que difieren las
        velocidades, así que el caballo más rápido ganaría siempre y las
        cuotas serían absurdas. La forma del día se sortea UNA vez y por eso
        no se promedia: su desviación de 14% entra completa.

    Ruido de cada tranco ~ Triangular(0.8, 1, 1.2)
        Multiplica el avance de cada paso. Es simétrica y de media
        exactamente 1, así que no sesga la velocidad promedio: le da textura
        a la carrera (adelantamientos, remontadas) sin decidir el resultado.

La triangular es el mejor caso continuo del proyecto para comparar los dos
métodos de generación, porque el costo teórico de aceptación-rechazo sale
exacto: la constante de mayoración con propuesta uniforme es c = 2 siempre,
sin importar dónde esté la moda (ver `rng.triangular`).
"""

import math
import time

from . import estadistica, rng

# --- parámetros del modelo -------------------------------------------------

N_CABALLOS = 8
LARGO_PISTA = 80.0

# Los caballos de una misma carrera están parejos a propósito: si el rango de
# velocidades fuera ancho, el mejor ganaría casi siempre, varios caballos
# tendrían probabilidad prácticamente cero y la casa no podría ponerles precio
# con una muestra finita (ver `analisis_precision_cuotas`).
VELOCIDAD_MIN, VELOCIDAD_MODA, VELOCIDAD_MAX = 3.6, 4.0, 4.8
ENERGIA_MIN, ENERGIA_MAX = 14.0, 22.0
FACTOR_CANSANCIO = 0.5

# Forma del día: se sortea por caballo en CADA carrera y no se promedia. Es
# amplia porque absorbe todo lo que el modelo no representa por separado
# (jinete, estado de la pista, la partida, el tráfico en la curva).
FORMA = 0.45
# Ruido de cada tranco: se promedia sobre los pasos, así que se deja chico.
RUIDO = 0.20

MAX_PASOS = 500  # blindaje contra una carrera que no termine nunca

# --- parámetros de la casa -------------------------------------------------

MARGEN_CASA = 0.05          # ventaja de la casa objetivo: 5%
# Carreras que corre la casa para fijar las cuotas. No es un número arbitrario:
# con pocas, la maldición del ganador deja al favorito con la cuota corta y al
# tapado con la cuota larga, y ese sesgo compite con el margen del 5% que la
# casa quiere cobrar. Ver `analisis_precision_cuotas`.
SIMULACIONES_CUOTA = 500
CUOTA_MAXIMA = 100.0        # tope para un caballo que nunca gana en la muestra

COSTO_DATO = 200.0          # soborno: los 3 caballos más rápidos
COSTO_REDBULL = 500.0       # soborno: acelerar un caballo
# El original sumaba +5 a una velocidad de 2 a 7, o sea que volvía al caballo
# imbatible (gana el 100% de las veces) y el análisis del soborno perdía
# gracia. Con +1.0 sobre una base de 3.6 a 4.8 el impulso pesa como una muy
# buena forma del día: cambia mucho las probabilidades sin volverlas certeza.
IMPULSO_REDBULL = 1.0

ESTRATEGIAS = ("favorito", "tapado", "azar", "fijo")


# ---------------------------------------------------------------------------
# Caballos y carrera
# ---------------------------------------------------------------------------


class Caballo:
    """Un caballo. `velocidad` y `energia` son información de la casa: el
    jugador solo ve el número y la cuota."""

    __slots__ = ("numero", "velocidad", "energia")

    def __init__(self, numero, velocidad, energia):
        self.numero = numero
        self.velocidad = velocidad
        self.energia = energia

    def publico(self):
        return {"numero": self.numero}

    def interno(self):
        return {
            "numero": self.numero,
            "velocidad": self.velocidad,
            "energia": self.energia,
        }


def generar_caballos(n=N_CABALLOS, generador=None):
    """Genera el lote de caballos de una carrera."""
    gen = rng.resolver(generador)
    return [
        Caballo(
            numero=i + 1,
            velocidad=gen.triangular(VELOCIDAD_MIN, VELOCIDAD_MODA, VELOCIDAD_MAX),
            energia=gen.uniforme_continua(ENERGIA_MIN, ENERGIA_MAX),
        )
        for i in range(n)
    ]


def correr(caballos, generador=None, largo=LARGO_PISTA, ruido=RUIDO,
           forma=FORMA, con_historial=False):
    """
    Corre una carrera paso a paso.

    Al arrancar, cada caballo recibe su forma del día (una triangular
    centrada en 1 que multiplica su velocidad toda la carrera). Después, en
    cada paso avanza `velocidad * forma * ruido`, con el ruido sorteado de
    nuevo cada tranco. Mientras le quede energía corre a fondo; al agotarse
    baja a `FACTOR_CANSANCIO` de su velocidad.

    Gana el que quede más adelante en el paso en que alguno cruza la meta
    (el equivalente a la foto de llegada; los empates exactos tienen
    probabilidad cero al ser posiciones continuas).
    """
    gen = rng.resolver(generador)
    triangular = gen.triangular  # se enlaza local: es el bucle caliente
    bajo, alto = 1.0 - ruido, 1.0 + ruido

    n = len(caballos)
    posiciones = [0.0] * n
    energias = [c.energia for c in caballos]
    # la forma del día se sortea una sola vez, aquí, y por eso no se promedia
    velocidades = [
        c.velocidad * triangular(1.0 - forma, 1.0, 1.0 + forma) for c in caballos
    ]

    historial = [list(posiciones)] if con_historial else None
    pasos = 0

    while pasos < MAX_PASOS:
        pasos += 1
        for i in range(n):
            if energias[i] > 0:
                velocidad = velocidades[i]
                energias[i] -= 1
            else:
                velocidad = velocidades[i] * FACTOR_CANSANCIO
            posiciones[i] += velocidad * triangular(bajo, 1.0, alto)
        if con_historial:
            historial.append(list(posiciones))
        if max(posiciones) >= largo:
            break

    indice_ganador = max(range(n), key=lambda i: posiciones[i])
    orden = sorted(range(n), key=lambda i: posiciones[i], reverse=True)

    resultado = {
        "ganador": caballos[indice_ganador].numero,
        "indice_ganador": indice_ganador,
        "pasos": pasos,
        "posiciones_finales": posiciones,
        "orden_llegada": [caballos[i].numero for i in orden],
        "largo_pista": largo,
    }
    if con_historial:
        resultado["historial"] = historial
    return resultado


# ---------------------------------------------------------------------------
# Cuotas: la simulación como mecanismo de precios
# ---------------------------------------------------------------------------


def estimar_probabilidades(caballos, generador=None, m=SIMULACIONES_CUOTA,
                           largo=LARGO_PISTA):
    """
    P(gana) de cada caballo, estimada corriendo `m` veces la misma carrera.

    No hay forma cerrada: la probabilidad depende de la velocidad, de la
    energía, del ruido acumulado y de contra quién corre. Estimarla por
    Monte Carlo ES el modelo de precios de la casa.
    """
    gen = rng.resolver(generador)
    victorias = [0] * len(caballos)
    for _ in range(m):
        victorias[correr(caballos, gen, largo)["indice_ganador"]] += 1
    return [v / m for v in victorias], victorias


def calcular_cuotas(probabilidades, margen=MARGEN_CASA, m=SIMULACIONES_CUOTA):
    """
    Cuota decimal (estilo europeo: lo que se cobra en total por cada unidad
    apostada, incluyendo la apuesta):

        cuota_i = (1 - margen) / p_i

    Con esa fórmula el retorno esperado del jugador es

        E[ganancia]/apuesta = p*(cuota - 1) - (1-p) = p*cuota - 1 = -margen

    o sea EXACTAMENTE -margen, sin importar a qué caballo le apueste. Ésa es
    la propiedad que hace justa la comparación entre estrategias de apuesta:
    si la simulación estimó bien las probabilidades, apostar al favorito y
    apostar al tapado deben rendir lo mismo a la larga.

    Un caballo que no ganó ninguna de las m carreras tendría cuota infinita.
    En vez de suavizar todas las probabilidades (lo que encogería a los
    favoritos hacia 1/n y les regalaría cuota de más), solo se le pone un piso
    de 1/(2m) a los que no ganaron nunca, y se topa la cuota en CUOTA_MAXIMA.
    """
    cuotas = []
    for p in probabilidades:
        p_efectiva = p if p > 0 else 1.0 / (2.0 * m)
        cuotas.append(min(CUOTA_MAXIMA, (1.0 - margen) / p_efectiva))
    return cuotas


def overround(cuotas):
    """
    Suma de las probabilidades implícitas menos 1. Es como los corredores de
    apuestas reales miden su margen: con cuotas justas suma 1, y aquí debe
    dar aproximadamente margen/(1-margen).
    """
    return sum(1.0 / c for c in cuotas) - 1.0


def abrir_carrera(generador=None, n=N_CABALLOS, margen=MARGEN_CASA,
                  m=SIMULACIONES_CUOTA, largo=LARGO_PISTA):
    """Genera el lote de caballos y le pone precio. Devuelve todo el contexto."""
    gen = rng.resolver(generador)
    caballos = generar_caballos(n, gen)
    probabilidades, victorias = estimar_probabilidades(caballos, gen, m, largo)
    cuotas = calcular_cuotas(probabilidades, margen, m)
    return {
        "caballos": caballos,
        "probabilidades": probabilidades,
        "victorias_simuladas": victorias,
        "cuotas": cuotas,
        "margen": margen,
        "simulaciones_cuota": m,
        "overround": overround(cuotas),
        "largo_pista": largo,
    }


# ---------------------------------------------------------------------------
# Apuestas
# ---------------------------------------------------------------------------


def elegir_caballo(carrera, estrategia="favorito", valor=None, generador=None):
    """Índice del caballo al que apuesta una estrategia automática."""
    cuotas = carrera["cuotas"]
    if estrategia == "favorito":
        return min(range(len(cuotas)), key=lambda i: cuotas[i])
    if estrategia == "tapado":
        return max(range(len(cuotas)), key=lambda i: cuotas[i])
    if estrategia == "azar":
        gen = rng.resolver(generador)
        return gen.entero(0, len(cuotas) - 1)
    if estrategia == "fijo":
        numero = int(valor) if valor not in (None, "") else 1
        return max(0, min(len(cuotas) - 1, numero - 1))
    raise ValueError(f"Estrategia inválida: {estrategia!r}")


def liquidar(apuesta, cuota, gano):
    """Ganancia NETA de la apuesta (negativa si perdió)."""
    return apuesta * (cuota - 1.0) if gano else -apuesta


def jugar(apuesta, tipo="favorito", valor=None, generador=None,
          margen=MARGEN_CASA, m=SIMULACIONES_CUOTA):
    """
    Misma forma que ruleta.jugar / dados.jugar / blackjack.jugar, para que la
    simulación trate a los cinco juegos igual.

    `tipo` es la estrategia de apuesta y `valor` el número de caballo cuando
    la estrategia es "fijo". Devuelve (detalle, gano, ganancia_neta).

    Ojo con el costo: cada llamada genera un lote de caballos, corre `m`
    carreras para ponerles precio y luego corre la carrera de verdad. Es el
    juego más caro del casino por mucho, y por eso las simulaciones largas
    usan menos rondas que en ruleta o dados.
    """
    gen = rng.resolver(generador)
    estrategia = tipo if tipo in ESTRATEGIAS else "favorito"
    carrera = abrir_carrera(gen, margen=margen, m=m)

    indice = elegir_caballo(carrera, estrategia, valor, gen)
    cuota = carrera["cuotas"][indice]
    resultado = correr(carrera["caballos"], gen, carrera["largo_pista"])
    gano = resultado["indice_ganador"] == indice
    ganancia = liquidar(apuesta, cuota, gano)

    detalle = {
        "estrategia": estrategia,
        "caballo_apostado": carrera["caballos"][indice].numero,
        "cuota": cuota,
        "prob_estimada": carrera["probabilidades"][indice],
        "ganador": resultado["ganador"],
        "orden_llegada": resultado["orden_llegada"],
        "pasos": resultado["pasos"],
        "gano": gano,
        "ganancia": ganancia,
        "apuesta": apuesta,
        "overround": carrera["overround"],
    }
    return detalle, gano, ganancia


def retorno_teorico(margen=MARGEN_CASA):
    """
    Con cuotas fijadas como (1-margen)/p, el retorno esperado es -margen para
    cualquier caballo. Es el valor contra el que se contrasta la simulación.
    """
    return -margen


# ---------------------------------------------------------------------------
# ¿Conviene sobornar al trabajador?
# ---------------------------------------------------------------------------


def tres_mas_rapidos(caballos):
    """Lo que delata el trabajador por 200 créditos."""
    orden = sorted(range(len(caballos)), key=lambda i: caballos[i].velocidad,
                   reverse=True)
    return orden[:3]


class _Acumulador:
    """
    Media, desviación y error estándar en una sola pasada (Welford), para
    poder reportar intervalos de confianza.

    Sin intervalos, estos números engañan: apostar a un tapado con cuota 30
    tiene una desviación por carrera de varias veces la apuesta, así que en
    unos cientos de carreras el retorno observado puede salir muy positivo o
    muy negativo por pura suerte. Reportar la media sin su incertidumbre
    llevaría a concluir que hay una estrategia ganadora donde no la hay.
    """

    __slots__ = ("n", "media", "m2", "victorias")

    def __init__(self):
        self.n = 0
        self.media = 0.0
        self.m2 = 0.0
        self.victorias = 0

    def agregar(self, x, gano=False):
        self.n += 1
        delta = x - self.media
        self.media += delta / self.n
        self.m2 += delta * (x - self.media)
        if gano:
            self.victorias += 1

    @property
    def desviacion(self):
        return math.sqrt(self.m2 / (self.n - 1)) if self.n > 1 else 0.0

    @property
    def error_estandar(self):
        return self.desviacion / math.sqrt(self.n) if self.n else 0.0

    def resumen(self, escala=1.0):
        ee = self.error_estandar
        return {
            "n": self.n,
            "media": self.media / escala,
            "desviacion": self.desviacion / escala,
            "error_estandar": ee / escala,
            "ic95_bajo": (self.media - 1.96 * ee) / escala,
            "ic95_alto": (self.media + 1.96 * ee) / escala,
            "prob_ganar": self.victorias / self.n if self.n else 0.0,
        }


def analisis_soborno(repeticiones=400, apuesta=100.0, margen=MARGEN_CASA,
                     m=SIMULACIONES_CUOTA, semilla=31337,
                     costo_dato=COSTO_DATO, costo_redbull=COSTO_REDBULL):
    """
    ¿Vale la pena sobornar? Es una decisión bajo incertidumbre, y se contesta
    con Monte Carlo en vez de con intuición.

    Cada réplica genera UN lote de caballos, le pone precio una sola vez y
    evalúa todos los escenarios sobre ese mismo lote (números aleatorios
    comunes), para que la comparación no dependa de que a un escenario le
    haya tocado un lote más fácil.

    Los escenarios:

        favorito / tapado / azar
            Apostar sin sobornar. Los tres deben rendir -margen, porque las
            cuotas ya incorporan la calidad de cada caballo.

        dato
            Pagar `costo_dato` para saber cuáles son los 3 caballos más
            rápidos y apostarle al más rápido de ellos. La hipótesis es que
            NO sirve: la casa fijó las cuotas simulando la carrera, así que
            la velocidad ya está en el precio. La información solo tiene
            valor si la casa no la tiene, y aquí sí la tiene.

        redbull
            Pagar `costo_redbull` para acelerar un caballo DESPUÉS de que las
            cuotas quedaron fijadas. Aquí sí hay ventaja, porque el precio
            quedó viejo respecto a la carrera que de verdad se va a correr.
            Se prueban dos variantes: acelerar al favorito (gana casi seguro
            pero paga poco) y acelerar al tapado (paga mucho y el impulso
            puede alcanzarle).
    """
    gen = rng.Generador(metodo="inversa", semilla=semilla)
    escenarios = ["favorito", "tapado", "azar", "dato",
                  "redbull_favorito", "redbull_tapado"]
    # se acumulan dos cosas por escenario: el neto CON el costo del soborno
    # (lo que de verdad le queda al jugador) y la ganancia SIN ese costo (que
    # es la que dice si el soborno cambió la carrera o no)
    acumulado = {e: _Acumulador() for e in escenarios}
    sin_costo = {e: _Acumulador() for e in escenarios}

    for _ in range(repeticiones):
        carrera = abrir_carrera(gen, margen=margen, m=m)
        caballos = carrera["caballos"]
        cuotas = carrera["cuotas"]

        for escenario in escenarios:
            costo = 0.0
            if escenario in ("favorito", "tapado", "azar"):
                indice = elegir_caballo(carrera, escenario, generador=gen)
                corredores = caballos
            elif escenario == "dato":
                costo = costo_dato
                indice = tres_mas_rapidos(caballos)[0]
                corredores = caballos
            else:
                costo = costo_redbull
                objetivo = ("favorito" if escenario == "redbull_favorito"
                            else "tapado")
                indice = elegir_caballo(carrera, objetivo)
                # el impulso se aplica DESPUÉS de fijadas las cuotas
                corredores = [
                    Caballo(c.numero,
                            c.velocidad + (IMPULSO_REDBULL if i == indice else 0.0),
                            c.energia)
                    for i, c in enumerate(caballos)
                ]

            resultado = correr(corredores, gen, carrera["largo_pista"])
            gano = resultado["indice_ganador"] == indice
            bruto = liquidar(apuesta, cuotas[indice], gano)

            acumulado[escenario].agregar(bruto - costo, gano)
            sin_costo[escenario].agregar(bruto, gano)

    filas = []
    for escenario in escenarios:
        resumen = acumulado[escenario].resumen()
        costo = (costo_dato if escenario == "dato"
                 else costo_redbull if escenario.startswith("redbull") else 0.0)
        filas.append({
            "escenario": escenario,
            "costo_soborno": costo,
            "prob_ganar": resumen["prob_ganar"],
            "neto_por_carrera": resumen["media"],
            "ic95_neto": [resumen["ic95_bajo"], resumen["ic95_alto"]],
            "error_estandar": resumen["error_estandar"],
            "desviacion_por_carrera": resumen["desviacion"],
            "retorno_sobre_apuesta": resumen["media"] / apuesta,
            "ic95_retorno": [resumen["ic95_bajo"] / apuesta,
                             resumen["ic95_alto"] / apuesta],
            "retorno_sin_contar_soborno": sin_costo[escenario].resumen()["media"] / apuesta,
            # ¿el intervalo excluye el -margen nominal? si no, no hay evidencia
            # de que este escenario se comporte distinto a apostar y ya
            "difiere_del_nominal": not (
                resumen["ic95_bajo"] / apuesta <= -margen <= resumen["ic95_alto"] / apuesta
            ),
        })

    return {
        "repeticiones": repeticiones,
        "apuesta": apuesta,
        "margen_nominal": margen,
        "retorno_esperado_sin_soborno": -margen,
        "resultados": filas,
        "punto_equilibrio": _punto_equilibrio(filas, apuesta, costo_redbull, margen),
        "nota_estadistica": (
            "Cada retorno viene con su intervalo de confianza al 95%. Sin él "
            "estos números engañan: apostar a un tapado con cuota alta tiene "
            "una desviación de varias veces la apuesta en cada carrera, así "
            "que en unos cientos de carreras el retorno observado se mueve "
            "decenas de puntos por pura suerte. La columna 'difiere_del_nominal' "
            "dice si el intervalo excluye el -margen teórico; cuando no lo "
            "excluye, no hay evidencia de que la estrategia sea distinta a "
            "apostar sin más."
        ),
        "lectura": (
            "Apostar al favorito, al tapado o al azar rinden prácticamente lo "
            "mismo, y ese mismo valor es -margen: las cuotas ya incorporan la "
            "calidad de cada caballo, así que elegir mejor no ayuda. Pagar por "
            "el dato de los 3 más rápidos empeora el resultado en exactamente "
            "el costo del dato, porque esa información la casa ya la usó para "
            "poner el precio. El redbull sí puede ser rentable, y no porque dé "
            "información sino porque CAMBIA la carrera después de que el precio "
            "quedó fijo: es el único de los tres que rompe el supuesto sobre el "
            "que la casa calculó las cuotas."
        ),
    }


def _punto_equilibrio(filas, apuesta, costo_redbull, margen):
    """
    A partir de qué tamaño de apuesta conviene el redbull. El impulso da una
    ventaja proporcional a lo apostado, mientras el soborno cuesta fijo, así
    que existe un umbral: apuesta > costo / ventaja_por_unidad.
    """
    equilibrios = {}
    for fila in filas:
        if not fila["escenario"].startswith("redbull"):
            continue
        # ventaja por unidad apostada, ya sin el costo fijo del soborno
        ventaja = (fila["neto_por_carrera"] + costo_redbull) / apuesta
        if ventaja > 0:
            equilibrios[fila["escenario"]] = {
                "ventaja_por_unidad_apostada": ventaja,
                "apuesta_minima_para_que_convenga": costo_redbull / ventaja,
            }
        else:
            equilibrios[fila["escenario"]] = {
                "ventaja_por_unidad_apostada": ventaja,
                "apuesta_minima_para_que_convenga": None,
                "nota": "El impulso no alcanza a dar ventaja: no conviene nunca.",
            }
    return equilibrios


# ---------------------------------------------------------------------------
# ¿Cuántas simulaciones necesita la casa para poner precio?
# ---------------------------------------------------------------------------


def analisis_precision_cuotas(valores_m=(25, 50, 100, 250, 500),
                              lotes=80, m_referencia=3000,
                              margen=MARGEN_CASA, semilla=8080):
    """
    ¿Cuántas carreras tiene que simular la casa antes de abrir la ventanilla?

    La casa fija las cuotas con p ESTIMADA, no con p verdadera, y ahí aparece
    un sesgo que no es obvio: la maldición del ganador.

    El favorito no es un caballo cualquiera, es el que quedó con la p estimada
    más ALTA. Al seleccionarlo por su estimación se lo selecciona junto con su
    error: los caballos que tuvieron suerte en la simulación de precios son
    justo los que suben al primer puesto. Entonces, en promedio,

        p_estimada(favorito) > p_verdadera(favorito)

    y su cuota, que es (1-margen)/p_estimada, queda DEMASIADO CORTA. Al tapado
    le pasa lo contrario: se elige por tener la p estimada más baja, así que
    su cuota queda demasiado larga y el jugador obtiene mejor precio del que
    le corresponde.

    Consecuencia práctica: apostar al azar rinde exactamente -margen (no hay
    selección, no hay sesgo), pero apostar siempre al favorito rinde peor y
    apostar siempre al tapado rinde mejor, y ninguna de las dos cosas tiene
    que ver con que unos caballos sean mejor apuesta que otros. Es puro
    artefacto de estimar con una muestra finita.

    Este análisis mide el sesgo directamente, comparando la p con la que la
    casa puso precio contra una p de referencia calculada con `m_referencia`
    carreras. Medirlo así es mucho menos ruidoso que medirlo por el retorno
    realizado, que necesitaría decenas de miles de carreras para distinguir
    el sesgo del azar.
    """
    filas = []
    for m in valores_m:
        gen = rng.Generador(metodo="inversa", semilla=semilla)
        acumuladores = {
            "favorito": _Acumulador(), "tapado": _Acumulador(), "azar": _Acumulador(),
        }
        inicio = time.perf_counter()
        for _ in range(lotes):
            caballos = generar_caballos(N_CABALLOS, gen)
            p_casa, _ = estimar_probabilidades(caballos, gen, m)
            p_real, _ = estimar_probabilidades(caballos, gen, m_referencia)
            elecciones = {
                "favorito": max(range(len(caballos)), key=lambda i: p_casa[i]),
                "tapado": min(range(len(caballos)), key=lambda i: p_casa[i]),
                "azar": gen.entero(0, len(caballos) - 1),
            }
            for nombre, indice in elecciones.items():
                acumuladores[nombre].agregar(p_casa[indice] - p_real[indice])
        transcurrido = time.perf_counter() - inicio

        fila = {"m": m, "segundos": transcurrido, "lotes": lotes}
        for nombre, acumulador in acumuladores.items():
            resumen = acumulador.resumen()
            fila[nombre] = {
                "sesgo_p": resumen["media"],
                "ic95": [resumen["ic95_bajo"], resumen["ic95_alto"]],
                "sesgo_significativo": not (
                    resumen["ic95_bajo"] <= 0.0 <= resumen["ic95_alto"]
                ),
            }
        filas.append(fila)

    return {
        "lotes_por_m": lotes,
        "m_referencia": m_referencia,
        "margen_nominal": margen,
        "retorno_nominal": -margen,
        "metrica": "p estimada por la casa menos p de referencia, para el caballo elegido",
        "resultados": filas,
        "lectura": (
            "El sesgo del favorito es positivo (la casa le asigna más "
            "probabilidad de la que tiene, así que su cuota queda corta) y el "
            "del tapado es negativo (cuota larga). Apostando al azar el sesgo "
            "es cero: ahí no hay selección. Los dos sesgos se encogen al "
            "crecer m, que es la respuesta a cuántas carreras necesita simular "
            "la casa: con m = 25 el favorito viene sobrevalorado en varios "
            "puntos de probabilidad, y a partir de unas 250-500 carreras el "
            "sesgo ya es chico frente al margen del 5% que la casa quiere "
            "cobrar."
        ),
    }


# ---------------------------------------------------------------------------
# Validación de las distribuciones del modelo
# ---------------------------------------------------------------------------


def validar_velocidad(n=50000, metodo="inversa", semilla=24680):
    """Chi-cuadrado y KS de la velocidad generada contra la triangular teórica."""
    gen = rng.Generador(metodo=metodo, semilla=semilla)
    gen.reiniciar_contadores()
    inicio = time.perf_counter()
    muestra = [gen.triangular(VELOCIDAD_MIN, VELOCIDAD_MODA, VELOCIDAD_MAX)
               for _ in range(n)]
    transcurrido = time.perf_counter() - inicio

    nombre = f"Triangular({VELOCIDAD_MIN}, {VELOCIDAD_MODA}, {VELOCIDAD_MAX})"
    metricas = gen.metricas()
    metricas["segundos"] = transcurrido
    metricas["microsegundos_por_variable"] = transcurrido / n * 1e6

    media = sum(muestra) / n
    return {
        "variable": "velocidad base del caballo",
        "distribucion": nombre,
        "metodo": metodo,
        "etiqueta_metodo": rng.ETIQUETAS_METODO[metodo],
        "n": n,
        "media_observada": media,
        "media_teorica": rng.media_triangular(VELOCIDAD_MIN, VELOCIDAD_MODA, VELOCIDAD_MAX),
        "varianza_observada": sum((x - media) ** 2 for x in muestra) / (n - 1),
        "varianza_teorica": rng.varianza_triangular(VELOCIDAD_MIN, VELOCIDAD_MODA, VELOCIDAD_MAX),
        "chi2": estadistica.prueba_chi2_continua(
            muestra,
            lambda u: rng.inversa_triangular(u, VELOCIDAD_MIN, VELOCIDAD_MODA, VELOCIDAD_MAX),
            n_intervalos=12, nombre=nombre,
        ),
        "ks": estadistica.prueba_ks_continua(
            muestra,
            lambda x: rng.acumulada_triangular(x, VELOCIDAD_MIN, VELOCIDAD_MODA, VELOCIDAD_MAX),
            nombre=nombre,
        ),
        "metricas": metricas,
        "costo_teorico_aceptacion_rechazo": {
            "constante_mayoracion": 2.0,
            "prob_aceptar_por_intento": 0.5,
            "uniformes_esperados_por_variable": 4.0,
            "tasa_rechazo_esperada": 0.5,
            "nota": (
                "Para la triangular con propuesta uniforme, c = f(moda)/q = "
                "(2/(b-a))/(1/(b-a)) = 2 exactamente, sin importar dónde esté "
                "la moda."
            ),
        },
    }


def comparar_metodos(n=50000, semilla=24680):
    """La misma validación con los dos métodos, lado a lado."""
    filas = [validar_velocidad(n, metodo, semilla) for metodo in rng.METODOS]
    inversa, ar = filas
    return {
        "variable": "velocidad base del caballo",
        "n": n,
        "semilla": semilla,
        "resultados": filas,
        "veredicto": {
            "ambos_pasan_chi2": not (inversa["chi2"]["rechaza_h0"] or ar["chi2"]["rechaza_h0"]),
            "ambos_pasan_ks": not (inversa["ks"]["rechaza_h0"] or ar["ks"]["rechaza_h0"]),
            "razon_uniformes": (
                ar["metricas"]["uniformes_por_variable"]
                / inversa["metricas"]["uniformes_por_variable"]
            ),
            "razon_tiempo": (
                ar["metricas"]["segundos"] / inversa["metricas"]["segundos"]
                if inversa["metricas"]["segundos"] else 0.0
            ),
            "nota": (
                "La triangular tiene inversa en forma cerrada, así que la "
                "transformada inversa gana sin discusión: 1 uniforme contra 4. "
                "Aceptación-rechazo se justificaría si la densidad no se "
                "pudiera integrar o invertir, que no es el caso aquí."
            ),
        },
    }


# ---------------------------------------------------------------------------
# Hipódromo interactivo (el usuario apuesta desde el frontend)
# ---------------------------------------------------------------------------


class Hipodromo:
    """
    Estado de una carrera interactiva: abrir la carrera (genera y pone precio),
    sobornar, apostar y correr. Vive en memoria del servidor, igual que la
    mesa de blackjack.
    """

    def __init__(self, generador=None, n_caballos=N_CABALLOS,
                 margen=MARGEN_CASA, m=SIMULACIONES_CUOTA):
        self.gen = rng.resolver(generador)
        self.n_caballos = n_caballos
        self.margen = margen
        self.m = m
        self.carrera = None
        self.reiniciar()

    def reiniciar(self):
        self.apuesta = 0.0
        self.caballo_apostado = None
        self.gasto_sobornos = 0.0
        self.dato_comprado = None
        self.redbull_usado = None
        self.resultado = None
        self.ganancia = 0.0
        self.corrida = False
        self.mensaje = "Abre una carrera para ver los caballos y sus cuotas."

    # -- acciones -----------------------------------------------------------

    def nueva_carrera(self):
        self.carrera = abrir_carrera(self.gen, self.n_caballos, self.margen, self.m)
        self.reiniciar()
        self.mensaje = (
            f"Carrera lista: {self.n_caballos} caballos. Las cuotas salieron de "
            f"simular {self.m} veces esta misma carrera."
        )
        return self.estado()

    def comprar_dato(self):
        """Soborno de 200: el trabajador delata los 3 caballos más rápidos."""
        self._exigir_carrera()
        if self.dato_comprado is not None:
            raise ValueError("Ya compraste el dato para esta carrera.")
        if self.corrida:
            raise ValueError("La carrera ya se corrió.")
        indices = tres_mas_rapidos(self.carrera["caballos"])
        self.dato_comprado = [self.carrera["caballos"][i].numero for i in indices]
        self.gasto_sobornos += COSTO_DATO
        self.mensaje = (
            f"El trabajador te pasa un papel con los números "
            f"{self.dato_comprado}. Ojo: la casa fijó las cuotas simulando la "
            f"carrera, así que esa velocidad ya está en el precio."
        )
        return self.estado()

    def dar_redbull(self, numero_caballo):
        """Soborno de 500: acelerar un caballo, ya con las cuotas publicadas."""
        self._exigir_carrera()
        if self.redbull_usado is not None:
            raise ValueError("Ya usaste el redbull en esta carrera.")
        if self.corrida:
            raise ValueError("La carrera ya se corrió.")
        indice = self._indice_de(numero_caballo)
        self.carrera["caballos"][indice].velocidad += IMPULSO_REDBULL
        self.redbull_usado = numero_caballo
        self.gasto_sobornos += COSTO_REDBULL
        self.mensaje = (
            f"El caballo {numero_caballo} se tomó el redbull. Su cuota sigue "
            f"siendo la de antes, que es justo donde está la ventaja."
        )
        return self.estado()

    def apostar(self, numero_caballo, monto):
        self._exigir_carrera()
        if self.corrida:
            raise ValueError("La carrera ya se corrió.")
        if self.apuesta:
            raise ValueError("Ya tienes una apuesta en esta carrera.")
        indice = self._indice_de(numero_caballo)
        self.caballo_apostado = numero_caballo
        self.apuesta = float(monto)
        cuota = self.carrera["cuotas"][indice]
        self.mensaje = (
            f"Apuesta registrada: {monto} al caballo {numero_caballo} "
            f"(cuota {cuota:.2f})."
        )
        return self.estado()

    def correr_carrera(self):
        self._exigir_carrera()
        if self.corrida:
            raise ValueError("La carrera ya se corrió.")
        resultado = correr(self.carrera["caballos"], self.gen,
                           self.carrera["largo_pista"], con_historial=True)
        self.corrida = True
        self.resultado = resultado

        if self.caballo_apostado is None:
            self.ganancia = 0.0
            self.mensaje = f"Ganó el caballo {resultado['ganador']}. No apostaste."
        else:
            indice = self._indice_de(self.caballo_apostado)
            gano = resultado["indice_ganador"] == indice
            self.ganancia = liquidar(self.apuesta, self.carrera["cuotas"][indice], gano)
            if gano:
                self.mensaje = (
                    f"¡Ganó tu caballo {self.caballo_apostado}! Cobras "
                    f"{self.ganancia + self.apuesta:.2f} "
                    f"({self.ganancia:+.2f} netos)."
                )
            else:
                self.mensaje = (
                    f"Ganó el caballo {resultado['ganador']}. Tu "
                    f"{self.caballo_apostado} no llegó."
                )
        return self.estado()

    # -- estado -------------------------------------------------------------

    def _exigir_carrera(self):
        if self.carrera is None:
            raise ValueError("No hay una carrera abierta.")

    def _indice_de(self, numero):
        for i, c in enumerate(self.carrera["caballos"]):
            if c.numero == int(numero):
                return i
        raise ValueError(f"No existe el caballo {numero}.")

    def estado(self):
        if self.carrera is None:
            return {"hay_carrera": False, "mensaje": self.mensaje}

        publico = []
        for i, caballo in enumerate(self.carrera["caballos"]):
            fila = {
                "numero": caballo.numero,
                "cuota": round(self.carrera["cuotas"][i], 2),
                "prob_implicita": 1.0 / self.carrera["cuotas"][i],
            }
            if self.corrida:
                # la velocidad real solo se revela al terminar
                fila["velocidad"] = caballo.velocidad
                fila["energia"] = caballo.energia
                fila["prob_estimada_casa"] = self.carrera["probabilidades"][i]
            publico.append(fila)

        estado = {
            "hay_carrera": True,
            "caballos": publico,
            "overround": self.carrera["overround"],
            "margen_casa": self.carrera["margen"],
            "simulaciones_cuota": self.carrera["simulaciones_cuota"],
            "largo_pista": self.carrera["largo_pista"],
            "apuesta": self.apuesta,
            "caballo_apostado": self.caballo_apostado,
            "gasto_sobornos": self.gasto_sobornos,
            "dato_comprado": self.dato_comprado,
            "redbull_usado": self.redbull_usado,
            "corrida": self.corrida,
            "ganancia": self.ganancia,
            "mensaje": self.mensaje,
            "costos": {"dato": COSTO_DATO, "redbull": COSTO_REDBULL},
        }
        if self.corrida:
            estado["ganador"] = self.resultado["ganador"]
            estado["orden_llegada"] = self.resultado["orden_llegada"]
            estado["pasos"] = self.resultado["pasos"]
            # historial para que el frontend anime la pista
            estado["historial"] = [
                [round(p, 2) for p in paso] for paso in self.resultado["historial"]
            ]
        return estado
