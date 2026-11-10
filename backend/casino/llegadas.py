"""
Llegadas de jugadores al casino: proceso de Poisson.

El casino no solo tiene juegos, tiene clientes que entran. Esa es la fuente de
aleatoriedad continua del modelo, y se modela con un proceso de Poisson,
porque las llegadas cumplen sus supuestos razonablemente bien: los clientes
llegan de forma independiente unos de otros, no llegan dos exactamente en el
mismo instante, y en una ventana corta la tasa es prácticamente constante.

Se modelan dos versiones:

    Homogéneo: tasa lambda constante. Los tiempos entre llegadas son
    exponenciales Exp(lambda), y el número de llegadas en un intervalo de
    largo t es Poisson(lambda*t).

    No homogéneo: la tasa depende de la hora, lambda(t), porque un casino
    recibe mucha más gente a las 10 de la noche que a las 8 de la mañana.

Los dos métodos de generación se comparan aquí también:

    Transformada inversa: se acumula E ~ Exp(1) y se resuelve Lambda(t) = E.
    Como lambda(t) es constante a trozos, Lambda(t) es lineal a trozos y se
    invierte de forma exacta recorriendo los tramos. Sin rechazo.

    Aceptación-rechazo (adelgazamiento / thinning): se propone un proceso
    homogéneo con lambda_max = max lambda(t) y cada llegada propuesta se
    acepta con probabilidad lambda(t)/lambda_max. Es literalmente
    aceptación-rechazo aplicado a un proceso puntual, y las llegadas
    rechazadas son el costo del método.
"""

import math

from . import estadistica, rng

# Tasa de llegadas por hora del día (jugadores por hora). El pico es de
# 21:00 a 01:00; la madrugada y la mañana son valles.
TASA_POR_HORA = [
    45, 30, 18, 10, 6, 4, 4, 6,      # 00-07
    10, 14, 18, 24, 30, 32, 30, 28,  # 08-15
    32, 40, 50, 62, 75, 90, 85, 65,  # 16-23
]

LAMBDA_MAX = max(TASA_POR_HORA)


def tasa(t, tasas=None):
    """lambda(t) con t en horas desde el inicio de la simulación."""
    return (tasas or TASA_POR_HORA)[int(t) % 24]


def lambda_acumulada(t, tasas=None):
    """Lambda(t) = integral de lambda desde 0 hasta t (llegadas esperadas)."""
    tasas = tasas or TASA_POR_HORA
    total = 0.0
    entero = int(t)
    for h in range(entero):
        total += tasas[h % 24]
    total += (t - entero) * tasas[entero % 24]
    return total


# ---------------------------------------------------------------------------
# Generación del proceso
# ---------------------------------------------------------------------------


def _llegadas_inversa(horas, generador, tasas):
    """
    Transformada inversa sobre el proceso no homogéneo.

    Se generan incrementos exponenciales estándar y se busca el t que cumple
    Lambda(t) = acumulado. Como lambda es constante a trozos, se avanza tramo
    por tramo consumiendo el incremento: dentro de un tramo con tasa L, un
    saldo de "s" unidades de Lambda equivale a s/L horas.
    """
    llegadas = []
    t = 0.0
    while True:
        # incremento Exp(1) por transformada inversa
        u = generador.fuente.uniforme()
        generador.n_variables += 1
        saldo = -math.log(1.0 - u)

        # consumirlo avanzando por los tramos horarios
        while saldo > 0 and t < horas:
            hora_actual = int(t)
            fin_tramo = min(hora_actual + 1.0, horas)
            capacidad = (fin_tramo - t) * tasas[hora_actual % 24]
            if saldo <= capacidad:
                t += saldo / tasas[hora_actual % 24]
                saldo = 0.0
            else:
                saldo -= capacidad
                t = fin_tramo
        if t >= horas or saldo > 0:
            break
        llegadas.append(t)
    return llegadas


def _llegadas_adelgazamiento(horas, generador, tasas):
    """
    Aceptación-rechazo (adelgazamiento): se propone un proceso homogéneo con
    lambda_max y se acepta cada llegada con probabilidad lambda(t)/lambda_max.
    Las propuestas rechazadas son trabajo perdido, igual que en la versión
    discreta del método.
    """
    lambda_max = max(tasas)
    llegadas = []
    t = 0.0
    while True:
        u1 = generador.fuente.uniforme()
        t += -math.log(1.0 - u1) / lambda_max
        if t >= horas:
            break
        u2 = generador.fuente.uniforme()
        generador.n_propuestas += 1
        if u2 <= tasa(t, tasas) / lambda_max:
            llegadas.append(t)
            generador.n_variables += 1
        else:
            generador.n_rechazos += 1
    return llegadas


def generar(horas=24.0, metodo="inversa", semilla=None, generador=None,
            tasa_por_hora=None, factor=1.0):
    """
    Instantes de llegada (en horas) durante `horas` de operación.
    Devuelve (llegadas, generador) para poder leer las métricas de costo.
    """
    gen = generador if generador is not None else rng.Generador(metodo=metodo, semilla=semilla)
    gen.reiniciar_contadores()
    tasas = [x * factor for x in (tasa_por_hora or TASA_POR_HORA)]
    if metodo == "inversa":
        llegadas = _llegadas_inversa(horas, gen, tasas)
    elif metodo == "aceptacion_rechazo":
        llegadas = _llegadas_adelgazamiento(horas, gen, tasas)
    else:
        raise ValueError(f"Método inválido: {metodo!r}")
    return llegadas, gen


# ---------------------------------------------------------------------------
# Validación del proceso generado
# ---------------------------------------------------------------------------


def validar(horas=24.0, repeticiones=200, metodo="inversa", semilla=12345):
    """
    Dos comprobaciones sobre el proceso generado:

    1. Conteo por hora: el promedio de llegadas en cada hora debe acercarse a
       lambda de esa hora. Se contrasta con un chi-cuadrado entre el total
       observado por hora y el esperado (repeticiones * lambda_h).

    2. Tiempos entre llegadas dentro de la hora pico (donde lambda es
       prácticamente constante): deben ser exponenciales. Se agrupan en
       intervalos de igual probabilidad teórica y se hace chi-cuadrado.
    """
    gen = rng.Generador(metodo=metodo, semilla=semilla)
    observado_por_hora = [0] * 24
    entre_llegadas_pico = []
    hora_pico = TASA_POR_HORA.index(LAMBDA_MAX)

    for _ in range(repeticiones):
        llegadas, _ = generar(horas, metodo, generador=gen)
        anterior_pico = None
        for t in llegadas:
            h = int(t) % 24
            observado_por_hora[h] += 1
            if h == hora_pico:
                if anterior_pico is not None:
                    entre_llegadas_pico.append(t - anterior_pico)
                anterior_pico = t

    dias = horas / 24.0
    esperado_por_hora = [lam * repeticiones * max(1.0, dias) for lam in TASA_POR_HORA]
    if horas < 24:
        esperado_por_hora = [
            lam * repeticiones * (1.0 if h < horas else 0.0)
            for h, lam in enumerate(TASA_POR_HORA)
        ]

    horas_activas = [h for h in range(24) if esperado_por_hora[h] > 0]
    prueba_conteos = estadistica.prueba_chi2(
        [observado_por_hora[h] for h in horas_activas],
        [esperado_por_hora[h] for h in horas_activas],
        etiquetas=[f"{h:02d}h" for h in horas_activas],
    )
    prueba_conteos["prueba"] = "Chi-cuadrado: llegadas observadas por hora vs lambda(t)"
    prueba_conteos["hipotesis_nula"] = "Las llegadas siguen el proceso de Poisson especificado"

    resultado = {
        "metodo": metodo,
        "etiqueta_metodo": rng.ETIQUETAS_METODO[metodo],
        "horas_simuladas": horas,
        "repeticiones": repeticiones,
        "tasa_por_hora": TASA_POR_HORA,
        "promedio_observado_por_hora": [
            observado_por_hora[h] / repeticiones for h in range(24)
        ],
        "llegadas_totales": sum(observado_por_hora),
        "llegadas_esperadas": sum(esperado_por_hora),
        "prueba_conteos": prueba_conteos,
        "metricas": gen.metricas(),
    }

    if len(entre_llegadas_pico) >= 100:
        resultado["prueba_entre_llegadas"] = _chi2_exponencial(
            entre_llegadas_pico, LAMBDA_MAX
        )
    return resultado


def _chi2_exponencial(muestra, tasa_teorica, n_intervalos=10):
    """
    Chi-cuadrado de los tiempos entre llegadas contra Exp(tasa), delegando en
    la prueba general de `estadistica` con intervalos equiprobables. La
    inversa de la acumulada exponencial es x = -ln(1-u)/tasa.
    """
    prueba = estadistica.prueba_chi2_continua(
        muestra,
        lambda u: -math.log(1.0 - u) / tasa_teorica,
        n_intervalos=n_intervalos,
        nombre=f"Exp(lambda={tasa_teorica})",
    )
    prueba["prueba"] = "Chi-cuadrado: tiempos entre llegadas vs Exp(lambda)"
    prueba["hipotesis_nula"] = "Los tiempos entre llegadas son exponenciales"
    prueba["media_observada"] = sum(muestra) / len(muestra)
    prueba["media_teorica"] = 1.0 / tasa_teorica
    prueba["ks"] = estadistica.prueba_ks_continua(
        muestra,
        lambda x: 1.0 - math.exp(-tasa_teorica * x),
        nombre=f"Exp(lambda={tasa_teorica})",
    )
    return prueba


def comparar_metodos(horas=24.0, repeticiones=100, semilla=777):
    """
    Inversa vs adelgazamiento sobre el mismo proceso: cuántos uniformes
    consume cada uno por llegada generada, cuánto rechaza el segundo y cuánto
    tarda cada uno. Con lambda(t) muy variable el adelgazamiento sufre,
    porque lambda_max = 90 mientras el promedio ronda 32.
    """
    import time

    filas = []
    for metodo in rng.METODOS:
        gen = rng.Generador(metodo=metodo, semilla=semilla)
        gen.reiniciar_contadores()
        inicio = time.perf_counter()
        total_llegadas = 0
        for _ in range(repeticiones):
            llegadas, _ = generar(horas, metodo, generador=gen)
            total_llegadas += len(llegadas)
        transcurrido = time.perf_counter() - inicio
        metricas = gen.metricas()
        metricas.update({
            "segundos": transcurrido,
            "llegadas_generadas": total_llegadas,
            "microsegundos_por_llegada": (
                transcurrido / total_llegadas * 1e6 if total_llegadas else 0.0
            ),
        })
        filas.append(metricas)

    tasa_media = sum(TASA_POR_HORA) / 24.0
    return {
        "escenario": f"{repeticiones} réplicas de {horas} horas de llegadas",
        "lambda_max": LAMBDA_MAX,
        "lambda_media": tasa_media,
        "eficiencia_teorica_adelgazamiento": tasa_media / LAMBDA_MAX,
        "resultados": filas,
    }
