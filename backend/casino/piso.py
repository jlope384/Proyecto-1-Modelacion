"""
El piso del casino: sistema de llegadas y salidas.

Este es el sistema real que el proyecto simula: clientes que LLEGAN al casino
(proceso de Poisson no homogéneo de `llegadas.py`), ocupan un puesto en una
mesa o máquina con capacidad finita, juegan una sesión de rondas REALES contra
los módulos de juego ya existentes (`ruleta`, `dados`, `tragamonedas`,
`blackjack`), y SALEN por una de cuatro causas: se quedaron sin saldo, llegaron
a su meta de retiro, se les acabó el tiempo que pensaban quedarse, o se
cansaron de esperar en la cola y se fueron sin jugar.

De ahí nace la cola: cuando todos los puestos de un juego están ocupados, el
siguiente cliente espera. Eso es lo que permite estimar tiempo promedio de
espera, longitud de fila y probabilidad de congestión, que es exactamente lo
que pide el enunciado del proyecto y que la simulación de rondas sueltas de
`simulacion.py` no puede dar (ahí no hay capacidad limitada ni cola).

Motor: un calendario de eventos con `heapq` (Capa 1: LLEGADA, FIN_SERVICIO,
ABANDONO_COLA), tal como el enunciado autoriza explícitamente ("puede ser tan
simple como generar arreglos de tiempos y procesarlos secuencialmente"). No
hay evento por ronda: en cuanto un cliente se sienta se le resuelve la sesión
completa (todas sus rondas) de una vez, porque el resultado no depende de
nada más del sistema; solo el INSTANTE en que se sienta sí depende de la cola.

Todas las variables nuevas se generan con `Generador.discreta` /
`.triangular` / `.exponencial`, que YA existen en `rng.py` con los dos
métodos (inversa y aceptación-rechazo). No se agrega ninguna distribución
nueva al generador.
"""

import heapq
import itertools
import math

from . import blackjack, dados, llegadas, ruleta, rng, simulacion, tragamonedas

# ---------------------------------------------------------------------------
# Configuración del sistema
# ---------------------------------------------------------------------------

# Mesas y puestos por mesa de cada juego. La capacidad total (mesas *
# puestos) es lo que limita cuántos clientes atiende el piso a la vez; de ahí
# nace la cola cuando la tasa de llegadas supera la capacidad, como pasa en
# el pico de 21:00-01:00 (ver TASA_POR_HORA en llegadas.py).
RECURSOS = {
    "tragamonedas": {"mesas": 20, "puestos_por_mesa": 1},
    "ruleta": {"mesas": 2, "puestos_por_mesa": 7},
    "blackjack": {"mesas": 4, "puestos_por_mesa": 5},
    "dados": {"mesas": 1, "puestos_por_mesa": 8},
}

# Con qué probabilidad un cliente que llega elige cada juego. Las máquinas
# concentran el tráfico real de un casino; es el caso discreto DESBALANCEADO
# del sistema, donde el costo de aceptación-rechazo se nota frente al de la
# ruleta (que es uniforme).
PESOS_JUEGO = {"tragamonedas": 0.45, "ruleta": 0.25, "blackjack": 0.20, "dados": 0.10}
JUEGOS_PISO = tuple(PESOS_JUEGO.keys())

# Duración de UNA ronda por juego, Triangular(a, moda, b) en MINUTOS. El
# servicio no es instantáneo y varía por juego: apretar un botón toma
# segundos, una mano de blackjack toma más.
DURACION_RONDA_MIN = {
    "tragamonedas": (0.05, 0.08, 0.2),
    "ruleta": (0.6, 1.2, 2.5),
    "blackjack": (0.5, 1.0, 2.0),
    "dados": (0.7, 1.5, 3.0),
}

# Con cuánto dinero entra un cliente. Asimétrica a la derecha: la mayoría
# trae poco, pocos traen mucho.
BANKROLL_TRIANGULAR = (200.0, 400.0, 1500.0)

# Fracción del bankroll ACTUAL que se apuesta en cada ronda.
FRACCION_APUESTA_TRIANGULAR = (0.02, 0.05, 0.15)

# El cliente se retira si su saldo llega a este múltiplo de lo que trajo.
META_MULTIPLO_TRIANGULAR = (1.3, 1.8, 3.0)

# Cuánto tiempo (minutos) piensa quedarse un cliente como máximo, gane o pierda.
ESTADIA_MAX_MIN_TRIANGULAR = (20.0, 60.0, 150.0)

# Paciencia en cola: media en minutos de una Exponencial. Sin memoria, como
# corresponde: cuánto lleva esperando no cambia cuánto más aguanta.
PACIENCIA_MEDIA_MIN = 8.0

# Apuestas fijas y simples para ruleta y dados dentro del piso (ambas pagan
# 1:1); lo que importa aquí es el tiempo de servicio y el flujo de caja, no
# explorar todos los tipos de apuesta que ya cubre el modo interactivo.
_APUESTA_RULETA = ("color", "rojo")
_APUESTA_DADOS = ("field", None)

MAX_PUNTOS_SERIE = 2000

# Salvavidas de rendimiento: con apuestas fraccionales el tiempo de ruina
# puede alargarse mucho para semillas raras. Sin esto el peor caso no está
# acotado; con esto sí, a costa de truncar esa cola rara de sesiones.
# ponytail: tope duro por sesión, subir si algún escenario lo necesita.
MAX_RONDAS_SESION = 4000

# -- eventos del calendario --------------------------------------------------
_LLEGADA = "llegada"
_FIN_SERVICIO = "fin_servicio"
_ABANDONO = "abandono"


# ---------------------------------------------------------------------------
# Sesión de un cliente: todas sus rondas contra el juego real, de una vez
# ---------------------------------------------------------------------------


def _sesion(juego, bankroll_inicial, gen, zapato=None):
    """
    Juega rondas reales de `juego` hasta que el cliente quiebra, llega a su
    meta, o se le acaba el tiempo que pensaba quedarse. Cada ronda usa la
    función `jugar` real del módulo del juego (misma lógica que el modo
    interactivo), así que el dinero perdido/ganado es exactamente el que
    generaría un cliente humano jugando esas mismas rondas.
    """
    a, moda, b = DURACION_RONDA_MIN[juego]
    meta = bankroll_inicial * gen.triangular(*META_MULTIPLO_TRIANGULAR)
    estadia_max = gen.triangular(*ESTADIA_MAX_MIN_TRIANGULAR)

    bankroll = bankroll_inicial
    duracion_min = 0.0
    apostado = 0.0
    ganancia_cliente = 0.0
    rondas = 0
    motivo = "estadia"

    while True:
        if bankroll < 1.0:  # ya no le alcanza para la apuesta mínima
            motivo = "quiebra"
            break
        if bankroll >= meta:
            motivo = "meta"
            break
        if duracion_min >= estadia_max:
            motivo = "estadia"
            break
        if rondas >= MAX_RONDAS_SESION:
            motivo = "limite_rondas"
            break

        apuesta = max(1.0, min(bankroll, gen.triangular(*FRACCION_APUESTA_TRIANGULAR) * bankroll))

        if juego == "tragamonedas":
            _, _, ganancia, _ = tragamonedas.jugar(apuesta, gen)
        elif juego == "ruleta":
            tipo, valor = _APUESTA_RULETA
            _, _, _, ganancia = ruleta.jugar(apuesta, tipo, valor, gen)
        elif juego == "dados":
            tipo, valor = _APUESTA_DADOS
            _, _, _, _, ganancia = dados.jugar(apuesta, tipo, valor, gen)
        else:  # blackjack
            detalle = blackjack.jugar_mano(apuesta, zapato, estrategia="basica", umbral=17)
            ganancia = detalle["ganancia"]
            apuesta = detalle["apuesta"]  # el doblez arriesga el doble

        bankroll = max(0.0, bankroll + ganancia)
        apostado += apuesta
        ganancia_cliente += ganancia
        rondas += 1
        duracion_min += gen.triangular(a, moda, b)

    return {
        "rondas": rondas,
        "duracion_horas": duracion_min / 60.0,
        "apostado": apostado,
        "ganancia_cliente": ganancia_cliente,
        "bankroll_final": bankroll,
        "motivo_fin": motivo,
    }


# ---------------------------------------------------------------------------
# Motor de eventos
# ---------------------------------------------------------------------------


def simular_dia(horas=24.0, metodo="inversa", semilla=None, recursos=None, pesos_juego=None,
                factor_llegadas=1.0, tasa_por_hora=None, paciencia_media_min=None):
    """
    Corre el piso durante `horas` de llegadas (el calendario sigue procesando
    a los clientes que ya llegaron hasta que todos son atendidos o abandonan,
    aunque eso caiga después de la ventana de llegadas).

    Devuelve KPIs del sistema: espera promedio, longitud de fila, utilización
    por recurso, probabilidad de congestión/abandono, ingreso del casino, y
    el chequeo de consistencia de Little (L ≈ lambda_efectiva * W).
    """
    recursos = recursos or RECURSOS
    pesos_juego = pesos_juego or PESOS_JUEGO
    if paciencia_media_min is None:
        paciencia_media_min = PACIENCIA_MEDIA_MIN
    if not factor_llegadas > 0:
        raise ValueError("factor_llegadas debe ser > 0")
    if not paciencia_media_min > 0:
        raise ValueError("paciencia_media_min debe ser > 0")
    tasas = [x * factor_llegadas for x in (tasa_por_hora or llegadas.TASA_POR_HORA)]

    gen = rng.Generador(metodo=metodo, semilla=semilla)
    gen.reiniciar_contadores()

    instantes_llegada, _ = llegadas.generar(horas, metodo, generador=gen,
                                          tasa_por_hora=tasa_por_hora, factor=factor_llegadas)

    estado = {
        r: {
            "ocupacion": [0] * cfg["mesas"],
            "capacidad": cfg["puestos_por_mesa"],
            "cola": [],
            "zapatos": (
                [blackjack.Zapato(gen) for _ in range(cfg["mesas"])] if r == "blackjack" else None
            ),
        }
        for r, cfg in recursos.items()
    }
    capacidad_total = {r: cfg["mesas"] * cfg["puestos_por_mesa"] for r, cfg in recursos.items()}

    contador = itertools.count()
    eventos = []
    for t in instantes_llegada:
        heapq.heappush(eventos, (t, next(contador), _LLEGADA, None))

    clientes = {}
    siguiente_id = itertools.count()

    # -- acumuladores para las métricas del sistema --
    acum = {
        "t_prev": 0.0,
        "en_sistema": 0,
        "area_sistema": 0.0,
        "area_cola": {r: 0.0 for r in recursos},
        "area_ocupacion": {r: 0.0 for r in recursos},
        "cola_por_hora": [0.0] * 24,
        "ocupacion_por_hora": {r: [0.0] * 24 for r in recursos},
    }
    llegadas_por_hora = [0] * 24
    esperas_min = []
    tiempos_sistema_min = []
    abandonos = 0
    atendidos = 0
    ingreso_por_juego = {r: 0.0 for r in recursos}
    apostado_por_juego = {r: 0.0 for r in recursos}
    rondas_por_juego = {r: 0 for r in recursos}
    motivos_fin = {}

    def _avanzar(t):
        # Área bajo la curva (clientes x tiempo) desde el evento anterior
        # hasta este, para L y L_q. Se atribuye al bloque horario en el que
        # empieza el intervalo: aproximación razonable porque las sesiones
        # (minutos) son mucho más cortas que una hora.
        # ponytail: aproximación por hora de inicio; exacta si se partiera
        # el intervalo en la frontera de cada hora, no hace falta aquí.
        dt = t - acum["t_prev"]
        if dt > 0:
            hora = int(acum["t_prev"]) % 24
            acum["area_sistema"] += acum["en_sistema"] * dt
            for r in recursos:
                n_cola = len(estado[r]["cola"])
                n_ocup = sum(estado[r]["ocupacion"])
                acum["area_cola"][r] += n_cola * dt
                acum["area_ocupacion"][r] += n_ocup * dt
                acum["cola_por_hora"][hora] += n_cola * dt
                acum["ocupacion_por_hora"][r][hora] += n_ocup * dt
        acum["t_prev"] = t

    def _sentar(cliente, t, mesa, espera_min):
        recurso = cliente["juego"]
        st = estado[recurso]
        st["ocupacion"][mesa] += 1
        assert st["ocupacion"][mesa] <= st["capacidad"]  # invariante de capacidad

        bankroll = gen.triangular(*BANKROLL_TRIANGULAR)
        zapato = st["zapatos"][mesa] if recurso == "blackjack" else None
        resumen = _sesion(recurso, bankroll, gen, zapato)
        t_fin = t + resumen["duracion_horas"]

        cliente["estado"] = "atendido"
        cliente["t_inicio"] = t
        cliente["t_fin"] = t_fin
        cliente["mesa"] = mesa

        esperas_min.append(espera_min)
        tiempos_sistema_min.append((t_fin - cliente["t_llegada"]) * 60.0)
        nonlocal atendidos
        atendidos += 1
        ingreso_por_juego[recurso] += -resumen["ganancia_cliente"]
        apostado_por_juego[recurso] += resumen["apostado"]
        rondas_por_juego[recurso] += resumen["rondas"]
        motivos_fin[resumen["motivo_fin"]] = motivos_fin.get(resumen["motivo_fin"], 0) + 1

        heapq.heappush(eventos, (t_fin, next(contador), _FIN_SERVICIO, (cliente["id"], recurso, mesa)))

    def _intentar_atender(cliente, t):
        recurso = cliente["juego"]
        st = estado[recurso]
        mesa = next((i for i, n in enumerate(st["ocupacion"]) if n < st["capacidad"]), None)
        if mesa is not None:
            _sentar(cliente, t, mesa, espera_min=0.0)
            return
        # no hay puesto: se une a la cola con una paciencia Exp(media paciencia_media_min)
        cliente["estado"] = "esperando"
        st["cola"].append(cliente)
        tasa_paciencia = 60.0 / paciencia_media_min  # eventos por hora
        paciencia = gen.exponencial(tasa_paciencia)
        heapq.heappush(eventos, (t + paciencia, next(contador), _ABANDONO, cliente["id"]))

    while eventos:
        t, _, tipo, payload = heapq.heappop(eventos)
        _avanzar(t)

        if tipo == _LLEGADA:
            cid = next(siguiente_id)
            juego = gen.elegir(list(pesos_juego), pesos=list(pesos_juego.values()))
            llegadas_por_hora[int(t) % 24] += 1
            cliente = {"id": cid, "juego": juego, "t_llegada": t, "estado": "por_atender"}
            clientes[cid] = cliente
            acum["en_sistema"] += 1
            _intentar_atender(cliente, t)

        elif tipo == _FIN_SERVICIO:
            cid, recurso, mesa = payload
            estado[recurso]["ocupacion"][mesa] -= 1
            acum["en_sistema"] -= 1
            # ¿hay alguien en cola esperando este mismo recurso?
            cola = estado[recurso]["cola"]
            if cola:
                # el cliente que sale de la cola ya estaba contado en en_sistema
                # desde que llegó (nunca salió del sistema, solo de la cola), así
                # que aquí no se vuelve a incrementar.
                siguiente = cola.pop(0)
                espera_min = (t - siguiente["t_llegada"]) * 60.0
                _sentar(siguiente, t, mesa, espera_min)

        elif tipo == _ABANDONO:
            cliente = clientes[payload]
            if cliente["estado"] == "esperando":
                cliente["estado"] = "abandono"
                estado[cliente["juego"]]["cola"].remove(cliente)
                abandonos += 1
                acum["en_sistema"] -= 1

    tiempo_total = max(horas, acum["t_prev"], 1e-9)
    llegadas_totales = len(instantes_llegada)

    def _muestra(lista):
        return [round(x, 4) for x in lista[:MAX_PUNTOS_SERIE]]

    resultado = {
        "metodo": metodo,
        "etiqueta_metodo": rng.ETIQUETAS_METODO[metodo],
        "horas": horas,
        "tiempo_total_horas": tiempo_total,
        "semilla": gen.fuente.semilla,
        "recursos": {r: {"mesas": cfg["mesas"], "puestos_por_mesa": cfg["puestos_por_mesa"],
                          "capacidad_total": capacidad_total[r]} for r, cfg in recursos.items()},
        "pesos_juego": pesos_juego,

        "llegadas_totales": llegadas_totales,
        "llegadas_por_hora": llegadas_por_hora,
        "tasa_por_hora": tasas,
        "factor_llegadas": factor_llegadas,
        "paciencia_media_min": paciencia_media_min,

        "atendidos": atendidos,
        "abandonos": abandonos,
        "prob_abandono": abandonos / llegadas_totales if llegadas_totales else 0.0,
        "prob_congestion": (
            sum(1 for w in esperas_min if w > 1e-9) / atendidos if atendidos else 0.0
        ),
        "motivos_fin": motivos_fin,

        "espera_promedio_min": sum(esperas_min) / atendidos if atendidos else 0.0,
        "tiempo_sistema_promedio_min": (
            sum(tiempos_sistema_min) / atendidos if atendidos else 0.0
        ),
        "esperas_min": _muestra(esperas_min),

        "clientes_promedio_sistema": acum["area_sistema"] / tiempo_total,
        "clientes_promedio_cola": {
            r: acum["area_cola"][r] / tiempo_total for r in recursos
        },
        "utilizacion": {
            r: acum["area_ocupacion"][r] / (capacidad_total[r] * tiempo_total) for r in recursos
        },
        "cola_promedio_por_hora": [x / 1.0 for x in acum["cola_por_hora"]],
        "ocupacion_promedio_por_hora": acum["ocupacion_por_hora"],

        "ingreso_total": sum(ingreso_por_juego.values()),
        "ingreso_por_juego": ingreso_por_juego,
        "apostado_por_juego": apostado_por_juego,
        "rondas_por_juego": rondas_por_juego,
        "metricas_generador": gen.metricas(),
    }

    resultado["ingreso_teorico_por_juego"] = {}
    for r in recursos:
        tipo = valor = None
        if r == "ruleta":
            tipo, valor = _APUESTA_RULETA
        elif r == "dados":
            tipo, valor = _APUESTA_DADOS
        ventaja = simulacion.retorno_teorico(r, tipo, valor)
        if ventaja is not None:
            resultado["ingreso_teorico_por_juego"][r] = -ventaja * apostado_por_juego[r]

    lam_ef = atendidos / tiempo_total
    w_horas = resultado["tiempo_sistema_promedio_min"] / 60.0
    resultado["little"] = {
        "lambda_efectiva": lam_ef,
        "L_observado": resultado["clientes_promedio_sistema"],
        "L_estimado_por_little": lam_ef * w_horas,
    }

    return resultado


# ---------------------------------------------------------------------------
# Comparación de métodos a nivel de sistema
# ---------------------------------------------------------------------------


def _ic95(valores):
    n = len(valores)
    media = sum(valores) / n
    if n < 2:
        return media, media, media
    varianza = sum((x - media) ** 2 for x in valores) / (n - 1)
    ee = math.sqrt(varianza / n)
    return media, media - 1.96 * ee, media + 1.96 * ee


def comparar_metodos(horas=24.0, replicas=12, semilla_base=90210):
    """
    Corre `replicas` días completos con cada método (misma semilla por
    réplica en ambos, para que la única diferencia sea el método) y compara:

        - que los KPIs del sistema coinciden (los IC al 95% de la espera en
          cola y del ingreso deben solaparse, porque ambos métodos generan de
          la misma distribución);
        - que el costo NO coincide (uniformes consumidos por cliente
          atendido, tasa de rechazo, segundos por día simulado).

    Ese es el criterio de comparación: costo por variable generada a
    igualdad de resultado estadístico.
    """
    import time

    resultados = {}
    for metodo in rng.METODOS:
        wq, lq, ingresos, uniformes_por_atendido, tasas_rechazo, segundos = [], [], [], [], [], []
        for i in range(replicas):
            semilla = semilla_base + i
            inicio = time.perf_counter()
            r = simular_dia(horas, metodo, semilla=semilla)
            segundos.append(time.perf_counter() - inicio)
            wq.append(r["espera_promedio_min"])
            lq.append(sum(r["clientes_promedio_cola"].values()))
            ingresos.append(r["ingreso_total"])
            m = r["metricas_generador"]
            uniformes_por_atendido.append(m["uniformes_consumidos"] / max(1, r["atendidos"]))
            tasas_rechazo.append(m["tasa_rechazo"])

        media_wq, wq_bajo, wq_alto = _ic95(wq)
        media_lq, lq_bajo, lq_alto = _ic95(lq)
        media_ing, ing_bajo, ing_alto = _ic95(ingresos)

        resultados[metodo] = {
            "metodo": metodo,
            "etiqueta": rng.ETIQUETAS_METODO[metodo],
            "espera_cola_min": {"media": media_wq, "ic95": [wq_bajo, wq_alto]},
            "clientes_en_cola": {"media": media_lq, "ic95": [lq_bajo, lq_alto]},
            "ingreso_total": {"media": media_ing, "ic95": [ing_bajo, ing_alto]},
            "uniformes_por_atendido": sum(uniformes_por_atendido) / replicas,
            "tasa_rechazo": sum(tasas_rechazo) / replicas,
            "segundos_por_dia": sum(segundos) / replicas,
        }

    return {
        "horas": horas,
        "replicas": replicas,
        "semilla_base": semilla_base,
        "resultados": resultados,
        "nota": (
            "Los intervalos de confianza de espera en cola e ingreso deben "
            "solaparse entre métodos (ambos generan de la misma "
            "distribución); lo que cambia es el costo por cliente atendido "
            "y, con el mix de juegos desbalanceado, la tasa de rechazo de "
            "aceptación-rechazo."
        ),
    }


# ---------------------------------------------------------------------------
# Autochequeo
# ---------------------------------------------------------------------------


def _demo():
    r = simular_dia(horas=24, metodo="inversa", semilla=2024)

    assert all(w >= 0 for w in r["esperas_min"]), "hay una espera negativa"
    assert r["atendidos"] + r["abandonos"] == r["llegadas_totales"], (
        "todo cliente que llega debe terminar atendido o abandonando"
    )
    for rec, u in r["utilizacion"].items():
        assert 0.0 <= u <= 1.0 + 1e-9, f"utilización fuera de rango en {rec}: {u}"

    little = r["little"]
    L_obs, L_est = little["L_observado"], little["L_estimado_por_little"]
    assert abs(L_obs - L_est) / max(L_obs, 1e-9) < 0.05, (
        f"Little no cuadra: observado={L_obs:.3f} estimado={L_est:.3f}"
    )

    assert abs(dados.retorno_teorico("field", None) + 1 / 18) < 1e-12
    assert abs(tragamonedas.retorno_teorico() + 0.07325) < 1e-9
    teo = r["ingreso_teorico_por_juego"]
    assert teo and all(v > 0 for v in teo.values()), f"ingreso teórico no positivo: {teo}"

    comp = comparar_metodos(horas=24, replicas=15, semilla_base=555)
    a = comp["resultados"]["inversa"]["espera_cola_min"]["ic95"]
    b = comp["resultados"]["aceptacion_rechazo"]["espera_cola_min"]["ic95"]
    solapan = a[0] <= b[1] and b[0] <= a[1]
    assert solapan, f"los IC de espera en cola no se solapan entre métodos: {a} vs {b}"

    print("piso.py: autochequeo OK")
    print(f"  atendidos={r['atendidos']} abandonos={r['abandonos']} "
          f"espera_prom={r['espera_promedio_min']:.2f} min "
          f"ingreso={r['ingreso_total']:.0f}")


if __name__ == "__main__":
    _demo()
