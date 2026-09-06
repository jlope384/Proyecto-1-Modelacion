"""
Validación de los generadores y comparación de los dos métodos.

Se responde a dos preguntas distintas, que conviene no mezclar:

    1. ¿La fuente uniforme sirve? -> `validar_lcg`. Se prueba el LCG contra
       U(0,1) con media/varianza, chi-cuadrado, Kolmogorov-Smirnov, rachas y
       autocorrelación, y se contrasta con el Mersenne Twister de Python
       corriendo exactamente las mismas pruebas.

    2. ¿Los dos métodos generan de verdad la distribución que dicen, y cuál
       cuesta menos? -> `validar_juego` y `comparar_metodos`. La calidad se
       mide con chi-cuadrado contra la distribución teórica de cada juego, y
       el costo con tiempo, uniformes consumidos por variable y tasa de
       rechazo.

Criterio de comparación propuesto (y su justificación)
------------------------------------------------------
Los dos métodos son exactos: ambos generan de la distribución objetivo, así
que compararlos por "precisión" solo tiene sentido como verificación (los dos
deben pasar el chi-cuadrado; si uno fallara, estaría mal implementado). Lo que
de verdad los separa es el COSTO, y por eso el criterio es de tres partes:

    a) Uniformes consumidos por variable generada. Es la métrica limpia:
       no depende de la máquina ni del lenguaje, y es la que aparece en la
       teoría (para aceptación-rechazo, 2c uniformes esperados con
       c = k * p_max).
    b) Tiempo de ejecución por variable. Es lo que se siente al correr la
       simulación, y captura efectos que la métrica anterior no ve (la
       inversa recorre la acumulada, y ese recorrido cuesta).
    c) Tasa de rechazo. Explica el porqué de las dos anteriores y muestra
       cómo se degrada la aceptación-rechazo cuando la distribución es
       desbalanceada.
"""

import time

from . import (
    blackjack,
    carreras,
    dados,
    estadistica,
    llegadas,
    rng,
    ruleta,
    tragamonedas,
)

# ---------------------------------------------------------------------------
# 1. Validación de la fuente uniforme
# ---------------------------------------------------------------------------


def validar_fuente(fuente, n=100000):
    """Corre la batería completa de pruebas sobre una fuente uniforme."""
    fuente.reiniciar()
    muestra = fuente.uniformes(n)
    return {
        "generador": fuente.describir(),
        "n": n,
        "pruebas": [
            estadistica.prueba_medias(muestra),
            estadistica.prueba_uniformidad_chi2(muestra, n_intervalos=20),
            estadistica.prueba_ks_uniforme(muestra),
            estadistica.prueba_rachas(muestra),
            estadistica.prueba_autocorrelacion(muestra, retardo=1),
            estadistica.prueba_autocorrelacion(muestra, retardo=5),
        ],
    }


def validar_lcg(n=100000, semilla=987654321, comparar_con_python=True):
    """
    Valida el LCG propio y, opcionalmente, corre las mismas pruebas sobre el
    Mersenne Twister como referencia. Que los dos pasen las mismas pruebas es
    el argumento de que el generador propio se puede usar sin reparos en el
    resto del proyecto.
    """
    resultado = {"lcg_propio": validar_fuente(rng.LCG(semilla), n)}
    if comparar_con_python:
        resultado["mersenne_twister"] = validar_fuente(rng.FuentePython(semilla), n)

    pruebas = resultado["lcg_propio"]["pruebas"]
    fallidas = [p["prueba"] for p in pruebas if p["rechaza_h0"]]
    resultado["veredicto"] = {
        "pruebas_corridas": len(pruebas),
        "pruebas_rechazadas": len(fallidas),
        "nombres_rechazados": fallidas,
        "apto": len(fallidas) == 0,
        "nota": (
            "Con nivel 0.05 se espera que en promedio 1 de cada 20 pruebas "
            "falle por azar aun con un generador correcto; una prueba aislada "
            "con p bajo no condena al generador, un patrón de fallos sí."
        ),
    }
    return resultado


# ---------------------------------------------------------------------------
# 2. Distribuciones teóricas de cada juego
# ---------------------------------------------------------------------------


def distribucion_teorica(juego):
    """
    (etiquetas, probabilidades) de la variable que se VALIDA con chi-cuadrado.

    Ojo con la diferencia entre lo que se valida y lo que se genera: en dados
    se valida la suma (triangular sobre 11 valores) pero se generan dos caras
    uniformes; esa distinción importa para el costo teórico, ver
    `distribucion_base`.
    """
    if juego == "ruleta":
        return [str(i) for i in range(ruleta.CASILLAS)], ruleta.PROBABILIDADES
    if juego == "dados":
        return [str(s) for s in range(2, 13)], dados.PROBABILIDADES_SUMA
    if juego == "tragamonedas":
        return list(tragamonedas.SIMBOLOS), tragamonedas.PROBABILIDADES
    if juego == "blackjack":
        # Sobre zapatos completos cada rango aparece la misma cantidad de
        # veces, así que la marginal de la carta extraída es uniforme 1/13
        # aunque la condicional cambie tras cada extracción.
        return list(blackjack.RANGOS), [1.0 / 13.0] * 13
    raise ValueError("Juego inválido")


def distribucion_base(juego):
    """
    Distribución que realmente se le pasa al generador en cada llamada. Es la
    que determina el costo teórico de aceptación-rechazo, y no siempre
    coincide con la que se valida.
    """
    if juego == "ruleta":
        return ruleta.PROBABILIDADES
    if juego == "dados":
        return dados.PROBABILIDADES_DADO      # una cara, no la suma
    if juego == "tragamonedas":
        return tragamonedas.PROBABILIDADES
    if juego == "blackjack":
        return [1.0 / 13.0] * 13              # solo con el zapato completo
    raise ValueError("Juego inválido")


# Modos de muestreo del blackjack:
#   "iid"    -> cada carta sale de un zapato recién barajado. Las extracciones
#               son independientes y el chi-cuadrado es válido.
#   "zapato" -> el zapato real del juego (sin reemplazo). Es el modelo que usa
#               la simulación, pero el chi-cuadrado deja de ser válido: ver
#               la advertencia en `validar_juego`.
MODOS_BLACKJACK = ("iid", "zapato")


def _muestrear(juego, n, generador, modo="iid"):
    """n realizaciones de la variable base del juego, como índices."""
    if juego == "ruleta":
        return [ruleta.girar(generador) for _ in range(n)]
    if juego == "dados":
        return [dados.tirar(generador)[2] - 2 for _ in range(n)]
    if juego == "tragamonedas":
        return [generador.discreta(tragamonedas.PROBABILIDADES) for _ in range(n)]
    if juego == "blackjack":
        if modo == "iid":
            probabilidades = [1.0 / 13.0] * 13
            return [generador.discreta(probabilidades) for _ in range(n)]
        zapato = blackjack.Zapato(generador)
        indices = []
        for _ in range(n):
            zapato.barajar_si_toca()
            indices.append(blackjack.RANGOS.index(zapato.sacar()))
        return indices
    raise ValueError("Juego inválido")


ADVERTENCIA_ZAPATO = (
    "El chi-cuadrado supone extracciones independientes, y las cartas del "
    "zapato se sacan SIN reemplazo: al agotarse un rango su probabilidad baja, "
    "lo que hace que los conteos finales queden más parejos de lo que sería un "
    "muestreo multinomial. El estadístico sale demasiado pequeño y los "
    "p-valores se van cerca de 1, así que la prueba es conservadora y no "
    "sirve para detectar un fallo del generador. Por eso la validación por "
    "defecto usa el modo 'iid' (un zapato recién barajado por carta), donde "
    "el supuesto sí se cumple; el modo 'zapato' se deja para mostrar "
    "justamente ese efecto."
)


def validar_juego(juego, n=60000, metodo="inversa", semilla=13579, modo="iid"):
    """
    Chi-cuadrado de bondad de ajuste entre lo generado y la distribución
    teórica del juego, más el costo observado del método.
    """
    etiquetas, probabilidades = distribucion_teorica(juego)
    generador = rng.Generador(metodo=metodo, semilla=semilla)
    generador.reiniciar_contadores()

    inicio = time.perf_counter()
    indices = _muestrear(juego, n, generador, modo)
    transcurrido = time.perf_counter() - inicio

    conteos = [0] * len(probabilidades)
    for i in indices:
        conteos[i] += 1
    esperados = [p * n for p in probabilidades]

    prueba = estadistica.prueba_chi2(conteos, esperados, etiquetas=etiquetas)
    metricas = generador.metricas()
    generadas = metricas["variables_generadas"] or 1
    metricas["segundos"] = transcurrido
    metricas["microsegundos_por_variable"] = transcurrido / generadas * 1e6
    metricas["variables_por_observacion"] = generadas / n if n else 0.0

    resultado = {
        "juego": juego,
        "metodo": metodo,
        "etiqueta_metodo": rng.ETIQUETAS_METODO[metodo],
        "n": n,
        "semilla": semilla,
        "categorias": etiquetas,
        "observados": conteos,
        "esperados": esperados,
        "frecuencias_relativas": [c / n for c in conteos],
        "probabilidades_teoricas": list(probabilidades),
        "prueba": prueba,
        "metricas": metricas,
    }
    if juego == "blackjack":
        resultado["modo"] = modo
        resultado["chi2_valido"] = modo == "iid"
        if modo == "zapato":
            resultado["advertencia"] = ADVERTENCIA_ZAPATO
    return resultado


# ---------------------------------------------------------------------------
# 3. Comparación de los dos métodos
# ---------------------------------------------------------------------------


def validar_replicado(juego, n=20000, metodo="inversa", replicas=100,
                      semilla_base=104729, modo="iid"):
    """
    Validación por réplicas, que es la forma correcta de juzgar un generador.

    Una sola prueba chi-cuadrado no dice gran cosa: con nivel 0.05, incluso un
    generador perfecto rechaza H0 en 1 de cada 20 corridas. Lo que sí es
    evidencia es repetir la prueba con muchas semillas y verificar dos cosas:

        - la fracción de rechazos ronda el 5%, ni más (generador sesgado) ni
          mucho menos (prueba conservadora, como pasa con el zapato sin
          reemplazo);
        - los p-valores se reparten de forma aproximadamente uniforme en
          [0,1], con media cerca de 0.5. Bajo H0 el p-valor ES uniforme, así
          que esto se puede verificar con un Kolmogorov-Smirnov sobre los
          propios p-valores.
    """
    p_valores = []
    for i in range(replicas):
        r = validar_juego(juego, n, metodo, semilla_base * (i + 1), modo)
        p_valores.append(r["prueba"]["p_valor"])

    rechazos = sum(1 for p in p_valores if p < estadistica.NIVEL_SIGNIFICANCIA)
    media = sum(p_valores) / len(p_valores)
    ks = estadistica.prueba_ks_uniforme(p_valores)
    ks["prueba"] = "Kolmogorov-Smirnov sobre los p-valores de las réplicas"
    ks["hipotesis_nula"] = "Los p-valores se distribuyen U(0,1), como debe ser bajo H0"

    return {
        "juego": juego,
        "metodo": metodo,
        "etiqueta_metodo": rng.ETIQUETAS_METODO[metodo],
        "modo": modo,
        "replicas": replicas,
        "n_por_replica": n,
        "rechazos": rechazos,
        "tasa_rechazo_observada": rechazos / replicas,
        "tasa_rechazo_esperada": estadistica.NIVEL_SIGNIFICANCIA,
        "p_valor_medio": media,
        "prueba_uniformidad_p_valores": ks,
        "veredicto": _veredicto_replicas(rechazos / replicas, media, ks),
    }


def _veredicto_replicas(tasa, media, ks):
    if tasa > 0.15:
        return ("Rechaza demasiado seguido: hay evidencia de que lo generado no "
                "sigue la distribución teórica.")
    if tasa < 0.005 and media > 0.9:
        return ("Casi nunca rechaza y los p-valores se van a 1: la prueba es "
                "conservadora en este escenario y no sirve como validación "
                "(típico del muestreo sin reemplazo).")
    if ks["rechaza_h0"]:
        return ("La tasa de rechazo es razonable, pero los p-valores no se "
                "distribuyen uniformemente: conviene revisar el escenario.")
    return ("Comportamiento correcto: la tasa de rechazo es compatible con el "
            "5% esperado y los p-valores se reparten uniformemente, que es "
            "justo lo que debe pasar si el generador produce la distribución "
            "objetivo.")


def _costo_teorico_aceptacion_rechazo(probabilidades):
    """
    Con propuesta uniforme sobre k categorías, la constante de mayoración es
    c = k * p_max, la probabilidad de aceptar en un intento es 1/c y el
    número esperado de uniformes por variable es 2c.
    """
    k = len(probabilidades)
    c = k * max(probabilidades)
    return {
        "constante_mayoracion": c,
        "prob_aceptar_por_intento": 1.0 / c,
        "intentos_esperados": c,
        "uniformes_esperados_por_variable": 2.0 * c,
        "tasa_rechazo_esperada": 1.0 - 1.0 / c,
    }


def comparar_metodos(juego, n=60000, semilla=13579, modo="iid"):
    """
    Corre el mismo juego con los dos métodos, misma semilla y mismo n, y
    devuelve calidad (chi-cuadrado) y costo (tiempo, uniformes por variable,
    tasa de rechazo) lado a lado, junto con el costo teórico esperado.
    """
    probabilidades = distribucion_base(juego)
    filas = [validar_juego(juego, n, metodo, semilla, modo) for metodo in rng.METODOS]

    inversa, ar = filas[0], filas[1]
    veredicto = {
        "ambos_pasan_chi2": not (inversa["prueba"]["rechaza_h0"] or ar["prueba"]["rechaza_h0"]),
        "nota_chi2": (
            "Una corrida aislada rechaza H0 el 5% de las veces aunque el "
            "generador esté bien; para concluir algo hay que mirar la "
            "validación por réplicas (`validar_replicado`), no una sola prueba."
        ),
        "razon_uniformes": (
            ar["metricas"]["uniformes_por_variable"]
            / inversa["metricas"]["uniformes_por_variable"]
            if inversa["metricas"]["uniformes_por_variable"] else 0.0
        ),
        "razon_tiempo": (
            ar["metricas"]["segundos"] / inversa["metricas"]["segundos"]
            if inversa["metricas"]["segundos"] else 0.0
        ),
        "mas_rapido": (
            "inversa" if inversa["metricas"]["segundos"] <= ar["metricas"]["segundos"]
            else "aceptacion_rechazo"
        ),
    }

    return {
        "juego": juego,
        "n": n,
        "semilla": semilla,
        "categorias_generadas": len(probabilidades),
        "prob_maxima": max(probabilidades),
        "costo_teorico_aceptacion_rechazo": _costo_teorico_aceptacion_rechazo(probabilidades),
        "resultados": filas,
        "veredicto": veredicto,
    }


def analisis_zapato_blackjack(manos=4000, semilla=4242, tramos=6):
    """
    Cómo se degrada aceptación-rechazo conforme se vacía el zapato.

    Con el zapato completo los 13 rangos son equiprobables y c = 13*(1/13) = 1:
    no hay rechazo. Pero al repartir cartas los rangos se desbalancean, p_max
    sube y c crece con él. Este análisis mide la tasa de rechazo real por
    tramo de penetración, y es la razón por la que la ventaja "sin acumulada"
    de aceptación-rechazo en blackjack se paga en otro lado.
    """
    generador = rng.Generador(metodo="aceptacion_rechazo", semilla=semilla)
    zapato = blackjack.Zapato(generador)
    total_cartas = 52 * zapato.n_barajas
    limite = total_cartas * zapato.penetracion

    acumulado = [{"repartidas": 0, "propuestas": 0, "rechazos": 0, "p_max": 0.0,
                  "muestras": 0} for _ in range(tramos)]

    for _ in range(manos):
        zapato.barajar_si_toca()
        repartidas = total_cartas - zapato.total_restantes
        tramo = min(tramos - 1, int(repartidas / limite * tramos))
        antes_prop, antes_rech = generador.n_propuestas, generador.n_rechazos
        p_max = max(zapato.probabilidades())
        blackjack.jugar_mano(10, zapato, estrategia="basica")
        acumulado[tramo]["repartidas"] += 1
        acumulado[tramo]["propuestas"] += generador.n_propuestas - antes_prop
        acumulado[tramo]["rechazos"] += generador.n_rechazos - antes_rech
        acumulado[tramo]["p_max"] += p_max
        acumulado[tramo]["muestras"] += 1

    filas = []
    for i, a in enumerate(acumulado):
        if not a["muestras"]:
            continue
        filas.append({
            "tramo": f"{int(i / tramos * 100)}-{int((i + 1) / tramos * 100)}% del zapato",
            "manos": a["muestras"],
            "p_max_promedio": a["p_max"] / a["muestras"],
            "propuestas": a["propuestas"],
            "rechazos": a["rechazos"],
            "tasa_rechazo": a["rechazos"] / a["propuestas"] if a["propuestas"] else 0.0,
        })

    return {
        "manos_simuladas": manos,
        "barajas": zapato.n_barajas,
        "penetracion": zapato.penetracion,
        "tramos": filas,
        "lectura": (
            "Con el zapato recién barajado los 13 rangos son equiprobables y "
            "aceptación-rechazo no descarta nada. Conforme se reparte, algunos "
            "rangos se agotan antes que otros, p_max sube y la tasa de rechazo "
            "crece con ella: el costo del método no es constante, depende del "
            "estado del sistema."
        ),
    }


def comparar_todos(n=40000, semilla=13579):
    """Comparación de los dos métodos en los cuatro juegos, de un tirón."""
    comparaciones = {j: comparar_metodos(j, n, semilla) for j in
                     ("ruleta", "dados", "tragamonedas", "blackjack")}
    return {
        "n_por_juego": n,
        "semilla": semilla,
        "juegos": comparaciones,
        "criterio": {
            "a_uniformes_por_variable": (
                "Métrica independiente de la máquina; la teoría predice 1 para "
                "la inversa y 2c para aceptación-rechazo."
            ),
            "b_tiempo_por_variable": (
                "Lo que se siente al correr la simulación; castiga a la "
                "inversa cuando hay muchas categorías y la acumulada hay que "
                "recorrerla completa."
            ),
            "c_tasa_rechazo": (
                "Explica las dos anteriores y muestra la degradación de "
                "aceptación-rechazo con distribuciones desbalanceadas."
            ),
        },
        "conclusion_esperada": (
            "Los dos métodos son exactos y los dos pasan el chi-cuadrado: la "
            "diferencia está en el costo. Cuando la distribución base es "
            "uniforme (ruleta con 37 casillas, dados con 6 caras, zapato "
            "completo con 13 rangos) aceptación-rechazo nunca rechaza y su "
            "costo extra es solo el segundo uniforme por variable. Cuando es "
            "desbalanceada, se degrada rápido: en la tragamonedas, con p_max = "
            "0.35 sobre 5 símbolos, c = 1.75 y descarta cerca del 43% de sus "
            "propuestas. La transformada inversa paga en cambio el recorrido "
            "de la acumulada, que crece con el número de categorías; por eso "
            "en la ruleta (37 categorías) la ventaja de la inversa casi "
            "desaparece."
        ),
    }


# ---------------------------------------------------------------------------
# 4. Reporte completo
# ---------------------------------------------------------------------------


def reporte_completo(n_uniformes=50000, n_por_juego=30000, semilla=13579):
    """Todo lo que hay que enseñar en el informe, en una sola llamada."""
    return {
        "fuente_uniforme": validar_lcg(n_uniformes, semilla),
        "juegos": comparar_todos(n_por_juego, semilla),
        "blackjack_zapato": {
            "chi2_modo_zapato": validar_juego(
                "blackjack", n_por_juego, "inversa", semilla, modo="zapato"
            ),
            "degradacion_aceptacion_rechazo": analisis_zapato_blackjack(),
        },
        # variables continuas: la triangular de las carreras y la exponencial
        # de las llegadas, que es donde los dos métodos se comparan fuera del
        # terreno discreto
        "carreras": carreras.comparar_metodos(n=n_por_juego),
        "llegadas": {
            "validacion": llegadas.validar(horas=24, repeticiones=100, metodo="inversa"),
            "comparacion": llegadas.comparar_metodos(horas=24, repeticiones=50),
        },
    }
