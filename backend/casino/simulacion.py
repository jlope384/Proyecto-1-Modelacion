"""
Motor de simulación Monte Carlo del casino.

Corre N rondas de un juego con una apuesta fija y estima las cantidades de
interés: probabilidad de ganar, ganancia neta, retorno sobre lo apostado
(la ventaja de la casa) y la trayectoria del saldo.

Todo se genera con el módulo `rng`, así que cada corrida se puede hacer con
el método de generación que se quiera y con una semilla fija para que sea
reproducible.
"""

import time

from . import blackjack, dados, ruleta, rng, tragamonedas

MAX_PUNTOS_HISTORIAL = 300
JUEGOS = ("ruleta", "dados", "tragamonedas", "blackjack")


def simular(juego, rondas, apuesta, tipo=None, valor=None, saldo_inicial=1000,
            metodo="inversa", semilla=None):
    """
    Devuelve las estadísticas de la corrida más la trayectoria del saldo.

    `metodo` elige entre transformada inversa y aceptación-rechazo; el
    resultado estadístico debe ser el mismo (ambos generan de la misma
    distribución) y lo que cambia es el costo. Esa es justamente la
    comparación que pide el proyecto.
    """
    if juego not in JUEGOS:
        raise ValueError("Juego inválido")

    generador = rng.Generador(metodo=metodo, semilla=semilla)
    generador.reiniciar_contadores()

    saldo = saldo_inicial
    historial = [saldo]
    victorias = 0
    empates = 0
    total_apostado = 0.0
    zapato = blackjack.Zapato(generador) if juego == "blackjack" else None
    conteo_resultados = {}

    inicio = time.perf_counter()
    for _ in range(rondas):
        if juego == "ruleta":
            _, _, gano, ganancia = ruleta.jugar(apuesta, tipo, valor, generador)
            apostado = apuesta
            empate = False
        elif juego == "dados":
            _, _, _, gano, ganancia = dados.jugar(apuesta, tipo, valor, generador)
            apostado = apuesta
            empate = False
        elif juego == "tragamonedas":
            _, gano, ganancia, empate = tragamonedas.jugar(apuesta, generador)
            apostado = apuesta
        elif juego == "blackjack":
            detalle = blackjack.jugar_mano(
                apuesta, zapato,
                estrategia=tipo or "basica",
                umbral=int(valor) if valor not in (None, "") else 17,
            )
            gano = detalle["gano"]
            ganancia = detalle["ganancia"]
            apostado = detalle["apuesta"]  # el doblez arriesga el doble
            empate = detalle["empate"]
            conteo_resultados[detalle["resultado"]] = (
                conteo_resultados.get(detalle["resultado"], 0) + 1
            )

        saldo += ganancia
        total_apostado += apostado
        historial.append(saldo)
        if gano:
            victorias += 1
        elif empate:
            empates += 1
    transcurrido = time.perf_counter() - inicio

    ganancia_neta_total = saldo - saldo_inicial
    paso = max(1, len(historial) // MAX_PUNTOS_HISTORIAL)
    historial_muestreado = historial[::paso]

    resultado = {
        "juego": juego,
        "rondas": rondas,
        "victorias": victorias,
        "empates": empates,
        "derrotas": rondas - victorias - empates,
        "prob_victoria": victorias / rondas if rondas else 0,
        "prob_empate": empates / rondas if rondas else 0,
        "saldo_inicial": saldo_inicial,
        "saldo_final": saldo,
        "ganancia_neta": ganancia_neta_total,
        "total_apostado": total_apostado,
        "retorno_sobre_apuesta": (
            ganancia_neta_total / total_apostado if total_apostado else 0
        ),
        "historial": historial_muestreado,
        "metodo": metodo,
        "etiqueta_metodo": rng.ETIQUETAS_METODO[metodo],
        "semilla": generador.fuente.semilla,
        "segundos": transcurrido,
        "metricas_generador": generador.metricas(),
    }

    teorico = retorno_teorico(juego, tipo, valor)
    if teorico is not None:
        resultado["retorno_teorico"] = teorico
        resultado["diferencia_vs_teorico"] = resultado["retorno_sobre_apuesta"] - teorico

    prob_teorica = probabilidad_teorica(juego, tipo, valor)
    if prob_teorica is not None:
        resultado["prob_victoria_teorica"] = prob_teorica

    if juego == "blackjack":
        resultado["desglose"] = conteo_resultados
        resultado["zapato"] = zapato.composicion()

    return resultado


def retorno_teorico(juego, tipo, valor):
    """
    Valor esperado por unidad apostada cuando existe forma cerrada. En
    blackjack no la hay (depende de la estrategia y de las reglas), así que
    ahí la simulación ES la forma de estimarlo.
    """
    try:
        if juego == "ruleta":
            return ruleta.retorno_teorico(tipo, valor)
        if juego == "dados":
            return dados.retorno_teorico(tipo, valor)
        if juego == "tragamonedas":
            return tragamonedas.retorno_teorico()
    except (ValueError, KeyError, TypeError, IndexError):
        return None
    return None


def probabilidad_teorica(juego, tipo, valor):
    try:
        if juego == "ruleta":
            return ruleta.probabilidad_teorica(tipo, valor)
        if juego == "dados":
            return dados.probabilidad_teorica(tipo, valor)
        if juego == "tragamonedas":
            return tragamonedas.probabilidad_teorica_ganar()
    except (ValueError, KeyError, TypeError, IndexError):
        return None
    return None


def comparar_estrategias_blackjack(rondas=20000, apuesta=10, semilla=2024,
                                   metodo="inversa"):
    """
    Retorno estimado por estrategia. Es el resultado más informativo del
    blackjack: la estrategia básica pierde alrededor de medio punto por
    unidad apostada, imitar al dealer pierde bastante más, y los umbrales
    fijos muestran una curva con mínimo alrededor de 16-17.
    """
    escenarios = [("basica", None), ("dealer", None)]
    escenarios += [("umbral", u) for u in range(12, 21)]

    filas = []
    for estrategia, umbral in escenarios:
        r = simular(
            "blackjack", rondas, apuesta,
            tipo=estrategia, valor=umbral if umbral is not None else 17,
            metodo=metodo, semilla=semilla,
        )
        filas.append({
            "estrategia": estrategia,
            "umbral": umbral,
            "etiqueta": estrategia if umbral is None else f"umbral {umbral}",
            "prob_victoria": r["prob_victoria"],
            "prob_empate": r["prob_empate"],
            "retorno_sobre_apuesta": r["retorno_sobre_apuesta"],
            "ganancia_neta": r["ganancia_neta"],
            "desglose": r["desglose"],
        })

    mejor = max(filas, key=lambda f: f["retorno_sobre_apuesta"])
    return {
        "rondas_por_escenario": rondas,
        "apuesta": apuesta,
        "semilla": semilla,
        "metodo": metodo,
        "resultados": filas,
        "mejor": mejor["etiqueta"],
        "nota": (
            "Todas las estrategias tienen retorno negativo: la ventaja de la "
            "casa no se elimina, solo se reduce. La misma semilla se usa en "
            "todos los escenarios para que la comparación no dependa del azar."
        ),
    }
