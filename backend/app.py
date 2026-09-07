import secrets

from flask import Flask, jsonify, request

from casino import (
    blackjack,
    carreras,
    dados,
    llegadas,
    piso,
    poker,
    rng,
    ruleta,
    simulacion,
    tragamonedas,
    validacion,
)

# El frontend (React + Vite) corre aparte en su propio servidor de desarrollo
# y llama a esta API vía el proxy configurado en frontend/vite.config.js.
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

SALDO_INICIAL = 1000

# Estado en memoria (un único jugador, sin base de datos: simplifica el proyecto).
saldo_jugador = {"saldo": SALDO_INICIAL}

# Mesa de blackjack e hipódromo de la sesión interactiva. Usan el generador
# global, así que cambiar el método desde /api/generador también cambia cómo
# salen las cartas y cómo corren los caballos.
mesa_blackjack = blackjack.Mesa()
hipodromo = carreras.Hipodromo()
mesa_poker = poker.MesaPoker()


@app.route("/api/estado")
def estado():
    return jsonify({
        "saldo": saldo_jugador["saldo"],
        "generador": rng.generador_actual().fuente.describir(),
        "metodo": rng.generador_actual().metodo,
    })


@app.route("/api/reiniciar", methods=["POST"])
def reiniciar():
    global mesa_blackjack, hipodromo, mesa_poker
    saldo_jugador["saldo"] = SALDO_INICIAL
    mesa_blackjack = blackjack.Mesa()
    hipodromo = carreras.Hipodromo()
    mesa_poker = poker.MesaPoker()
    return jsonify({"saldo": saldo_jugador["saldo"]})


@app.route("/api/generador", methods=["GET", "POST"])
def generador():
    """
    Consulta o cambia el método de generación de la sesión interactiva.
    Sirve para demostrar en vivo que los dos métodos producen el mismo juego.
    """
    global mesa_blackjack, hipodromo, mesa_poker
    if request.method == "POST":
        datos = request.get_json() or {}
        metodo = datos.get("metodo")
        if metodo is not None and metodo not in rng.METODOS:
            return jsonify({"error": f"Método inválido. Use uno de {rng.METODOS}"}), 400
        semilla = datos.get("semilla")
        rng.configurar_generador(metodo=metodo, semilla=int(semilla) if semilla else None)
        mesa_blackjack = blackjack.Mesa()
        hipodromo = carreras.Hipodromo()
        mesa_poker = poker.MesaPoker()

    gen = rng.generador_actual()
    return jsonify({
        "metodo": gen.metodo,
        "etiqueta": rng.ETIQUETAS_METODO[gen.metodo],
        "metodos_disponibles": [
            {"id": m, "etiqueta": rng.ETIQUETAS_METODO[m]} for m in rng.METODOS
        ],
        "fuente": gen.fuente.describir(),
        "metricas": gen.metricas(),
    })


def _validar_apuesta(apuesta):
    if apuesta <= 0 or apuesta > saldo_jugador["saldo"]:
        return False
    return True


# ---------------------------------------------------------------------------
# Juegos interactivos
# ---------------------------------------------------------------------------


@app.route("/api/ruleta/jugar", methods=["POST"])
def ruleta_jugar():
    datos = request.get_json()
    apuesta = float(datos["apuesta"])

    if not _validar_apuesta(apuesta):
        return jsonify({"error": "Apuesta inválida"}), 400

    numero, color, gano, ganancia = ruleta.jugar(apuesta, datos["tipo"], datos["valor"])
    saldo_jugador["saldo"] += ganancia

    return jsonify({
        "numero": numero,
        "color": color,
        "gano": gano,
        "ganancia": ganancia,
        "saldo": saldo_jugador["saldo"],
    })


@app.route("/api/dados/jugar", methods=["POST"])
def dados_jugar():
    datos = request.get_json()
    apuesta = float(datos["apuesta"])

    if not _validar_apuesta(apuesta):
        return jsonify({"error": "Apuesta inválida"}), 400

    d1, d2, suma, gano, ganancia = dados.jugar(apuesta, datos["tipo"], datos["valor"])
    saldo_jugador["saldo"] += ganancia

    return jsonify({
        "dado1": d1,
        "dado2": d2,
        "suma": suma,
        "gano": gano,
        "ganancia": ganancia,
        "saldo": saldo_jugador["saldo"],
    })


@app.route("/api/tragamonedas/jugar", methods=["POST"])
def tragamonedas_jugar():
    datos = request.get_json()
    apuesta = float(datos["apuesta"])

    if not _validar_apuesta(apuesta):
        return jsonify({"error": "Apuesta inválida"}), 400

    reels, gano, ganancia, empate = tragamonedas.jugar(apuesta)
    saldo_jugador["saldo"] += ganancia

    return jsonify({
        "reels": reels,
        "gano": gano,
        "empate": empate,
        "ganancia": ganancia,
        "saldo": saldo_jugador["saldo"],
    })


@app.route("/api/tragamonedas/tabla")
def tragamonedas_tabla():
    """Tabla de pagos y valores teóricos exactos (espacio muestral de 125)."""
    return jsonify({
        "simbolos": tragamonedas.SIMBOLOS,
        "pesos": tragamonedas.PESOS,
        "probabilidades": tragamonedas.PROBABILIDADES,
        "tabla": tragamonedas.tabla_pagos(),
        "prob_ganar": tragamonedas.probabilidad_teorica_ganar(),
        "prob_empate": tragamonedas.probabilidad_empate(),
        "prob_perder": tragamonedas.probabilidad_perder(),
        "retorno_teorico": tragamonedas.retorno_teorico(),
    })


# ---------------------------------------------------------------------------
# Blackjack interactivo
#
# A diferencia de los otros tres juegos, una mano de blackjack son varias
# decisiones del jugador, así que la mesa mantiene estado entre peticiones:
# repartir -> (pedir | doblar)* -> plantarse -> liquidar.
# ---------------------------------------------------------------------------


def _responder_mesa(liquidar=False):
    estado_mesa = mesa_blackjack.estado()
    if liquidar and not estado_mesa["en_juego"]:
        saldo_jugador["saldo"] += estado_mesa["ganancia"]
    estado_mesa["saldo"] = saldo_jugador["saldo"]
    return jsonify(estado_mesa)


@app.route("/api/blackjack/estado")
def blackjack_estado():
    estado_mesa = mesa_blackjack.estado()
    estado_mesa["saldo"] = saldo_jugador["saldo"]
    return jsonify(estado_mesa)


@app.route("/api/blackjack/nueva", methods=["POST"])
def blackjack_nueva():
    datos = request.get_json() or {}
    apuesta = float(datos.get("apuesta", 0))

    if not _validar_apuesta(apuesta):
        return jsonify({"error": "Apuesta inválida"}), 400
    if mesa_blackjack.estado()["en_juego"]:
        return jsonify({"error": "Ya hay una mano en curso"}), 400

    mesa_blackjack.nueva_mano(apuesta)
    return _responder_mesa(liquidar=True)  # por si sale blackjack de entrada


@app.route("/api/blackjack/pedir", methods=["POST"])
def blackjack_pedir():
    try:
        mesa_blackjack.pedir()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return _responder_mesa(liquidar=True)


@app.route("/api/blackjack/plantarse", methods=["POST"])
def blackjack_plantarse():
    try:
        mesa_blackjack.plantarse()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return _responder_mesa(liquidar=True)


@app.route("/api/blackjack/doblar", methods=["POST"])
def blackjack_doblar():
    estado_mesa = mesa_blackjack.estado()
    if not estado_mesa["en_juego"]:
        return jsonify({"error": "No hay una mano en curso"}), 400
    # doblar arriesga el doble: hay que poder cubrirlo
    if estado_mesa["apuesta"] * 2 > saldo_jugador["saldo"]:
        return jsonify({"error": "Saldo insuficiente para doblar"}), 400
    try:
        mesa_blackjack.doblar()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return _responder_mesa(liquidar=True)


@app.route("/api/blackjack/analisis-zapato", methods=["POST"])
def blackjack_analisis_zapato():
    """
    Cómo se degrada aceptación-rechazo conforme se vacía el zapato.

    Estaba solo dentro de /api/reporte, que corre todo el paquete de
    validación; aquí se expone aparte para poder graficarlo en la interfaz
    sin pagar el resto.
    """
    datos = request.get_json(silent=True) or {}
    manos = int(datos.get("manos", 4000))
    tramos = int(datos.get("tramos", 6))
    if manos < 200 or manos > 20000:
        return jsonify({"error": "Manos fuera de rango (200 a 20,000)"}), 400
    if tramos < 3 or tramos > 12:
        return jsonify({"error": "Tramos fuera de rango (3 a 12)"}), 400
    return jsonify(validacion.analisis_zapato_blackjack(manos=manos, tramos=tramos))


# ---------------------------------------------------------------------------
# Carrera de caballos interactiva
#
# El flujo tiene más pasos que los otros juegos porque hay que ponerle precio
# al lote antes de aceptar apuestas:
#   nueva -> (dato | redbull)* -> apostar -> correr
# ---------------------------------------------------------------------------


def _responder_hipodromo(cobrar_soborno=0.0, liquidar=False):
    estado_pista = hipodromo.estado()
    if cobrar_soborno:
        saldo_jugador["saldo"] -= cobrar_soborno
    if liquidar and estado_pista.get("corrida"):
        saldo_jugador["saldo"] += estado_pista["ganancia"]
    estado_pista["saldo"] = saldo_jugador["saldo"]
    return jsonify(estado_pista)


@app.route("/api/carreras/estado")
def carreras_estado():
    estado_pista = hipodromo.estado()
    estado_pista["saldo"] = saldo_jugador["saldo"]
    return jsonify(estado_pista)


@app.route("/api/carreras/nueva", methods=["POST"])
def carreras_nueva():
    hipodromo.nueva_carrera()
    return _responder_hipodromo()


@app.route("/api/carreras/apostar", methods=["POST"])
def carreras_apostar():
    datos = request.get_json() or {}
    apuesta = float(datos.get("apuesta", 0))
    caballo = datos.get("caballo")

    if not _validar_apuesta(apuesta):
        return jsonify({"error": "Apuesta inválida"}), 400
    if caballo is None:
        return jsonify({"error": "Falta el número de caballo"}), 400

    try:
        hipodromo.apostar(caballo, apuesta)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    saldo_jugador["saldo"] -= apuesta  # la apuesta se retiene al registrarla
    return _responder_hipodromo()


@app.route("/api/carreras/soborno/dato", methods=["POST"])
def carreras_soborno_dato():
    if saldo_jugador["saldo"] < carreras.COSTO_DATO:
        return jsonify({"error": "Saldo insuficiente para el dato"}), 400
    try:
        hipodromo.comprar_dato()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return _responder_hipodromo(cobrar_soborno=carreras.COSTO_DATO)


@app.route("/api/carreras/soborno/redbull", methods=["POST"])
def carreras_soborno_redbull():
    datos = request.get_json() or {}
    caballo = datos.get("caballo")
    if caballo is None:
        return jsonify({"error": "Falta el número de caballo"}), 400
    if saldo_jugador["saldo"] < carreras.COSTO_REDBULL:
        return jsonify({"error": "Saldo insuficiente para el redbull"}), 400
    try:
        hipodromo.dar_redbull(caballo)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return _responder_hipodromo(cobrar_soborno=carreras.COSTO_REDBULL)


@app.route("/api/carreras/correr", methods=["POST"])
def carreras_correr():
    try:
        hipodromo.correr_carrera()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    # al liquidar se devuelve la apuesta retenida más la ganancia neta
    estado_pista = hipodromo.estado()
    if estado_pista["caballo_apostado"] is not None:
        saldo_jugador["saldo"] += estado_pista["apuesta"] + estado_pista["ganancia"]
    estado_pista["saldo"] = saldo_jugador["saldo"]
    return jsonify(estado_pista)


@app.route("/api/carreras/soborno/analisis", methods=["POST"])
def carreras_analisis_soborno():
    datos = request.get_json() or {}
    repeticiones = int(datos.get("repeticiones", 400))
    apuesta = float(datos.get("apuesta", 100))
    if repeticiones < 10 or repeticiones > 3000:
        return jsonify({"error": "Repeticiones fuera de rango (10 a 3000)"}), 400
    if apuesta <= 0:
        return jsonify({"error": "Apuesta inválida"}), 400
    return jsonify(carreras.analisis_soborno(repeticiones, apuesta))


@app.route("/api/carreras/precision-cuotas", methods=["POST"])
def carreras_precision_cuotas():
    """Sesgo de selección (maldición del ganador) según cuánto simula la casa."""
    datos = request.get_json() or {}
    lotes = int(datos.get("lotes", 60))
    m_referencia = int(datos.get("m_referencia", 2500))
    if lotes < 10 or lotes > 500:
        return jsonify({"error": "Lotes fuera de rango (10 a 500)"}), 400
    if m_referencia < 500 or m_referencia > 10000:
        return jsonify({"error": "m_referencia fuera de rango (500 a 10,000)"}), 400
    return jsonify(carreras.analisis_precision_cuotas(
        lotes=lotes, m_referencia=m_referencia
    ))


@app.route("/api/carreras/validacion", methods=["GET", "POST"])
def carreras_validacion():
    """Chi-cuadrado y KS de la velocidad triangular, con los dos métodos."""
    datos = request.get_json(silent=True) or {}
    n = int(datos.get("n", 50000))
    if n < 500 or n > 300_000:
        return jsonify({"error": "n fuera de rango (500 a 300,000)"}), 400
    return jsonify(carreras.comparar_metodos(n))


# ---------------------------------------------------------------------------
# Póker (Texas Hold'em) interactivo
#
# El humano se sienta comprando fichas con su saldo del casino y juega mano
# tras mano contra 3 bots que deciden con equity por Monte Carlo. Como en
# blackjack, una mano son varias decisiones: nueva -> accion* -> (showdown |
# todos se retiran menos uno), y la mesa resuelve los turnos de los bots
# automáticamente entre una llamada y la siguiente.
# ---------------------------------------------------------------------------


def _responder_poker():
    estado_mesa = mesa_poker.estado()
    estado_mesa["saldo"] = saldo_jugador["saldo"]
    return jsonify(estado_mesa)


@app.route("/api/poker/estado")
def poker_estado():
    return _responder_poker()


@app.route("/api/poker/comprar", methods=["POST"])
def poker_comprar():
    datos = request.get_json() or {}
    monto = float(datos.get("monto", 0))

    if monto <= 0 or monto > saldo_jugador["saldo"]:
        return jsonify({"error": "Monto inválido"}), 400
    try:
        mesa_poker.comprar_fichas(monto)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    saldo_jugador["saldo"] -= monto
    return _responder_poker()


@app.route("/api/poker/retirarse", methods=["POST"])
def poker_retirarse():
    try:
        stack_final = mesa_poker.retirarse_mesa()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    saldo_jugador["saldo"] += stack_final
    return _responder_poker()


@app.route("/api/poker/nueva", methods=["POST"])
def poker_nueva():
    try:
        mesa_poker.nueva_mano()
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return _responder_poker()


@app.route("/api/poker/accion", methods=["POST"])
def poker_accion():
    datos = request.get_json() or {}
    accion = datos.get("accion")
    monto = float(datos.get("monto", 0))

    if accion not in ("fold", "check", "call", "raise"):
        return jsonify({"error": "Acción inválida. Use fold, check, call o raise"}), 400
    try:
        mesa_poker.actuar(accion, monto)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    return _responder_poker()


# ---------------------------------------------------------------------------
# Simulación
# ---------------------------------------------------------------------------


@app.route("/api/simulacion", methods=["POST"])
def simulacion_ejecutar():
    datos = request.get_json()
    juego = datos["juego"]
    rondas = int(datos["rondas"])
    apuesta = float(datos["apuesta"])
    tipo = datos.get("tipo")
    valor = datos.get("valor")
    metodo = datos.get("metodo", "inversa")
    semilla = datos.get("semilla")

    if juego not in simulacion.JUEGOS:
        return jsonify({"error": f"Juego inválido. Use uno de {simulacion.JUEGOS}"}), 400
    if metodo not in rng.METODOS:
        return jsonify({"error": f"Método inválido. Use uno de {rng.METODOS}"}), 400
    if apuesta <= 0:
        return jsonify({"error": "Apuesta inválida"}), 400

    # la carrera y el póker cuestan mucho más por ronda que los demás juegos:
    # la carrera pone precio simulando el lote antes de correr, y el póker
    # corre una estimación de equity por Monte Carlo en cada decisión de bot
    tope = 100_000
    if juego == "carreras":
        tope = simulacion.MAX_RONDAS_CARRERAS
    elif juego == "poker":
        tope = simulacion.MAX_RONDAS_POKER
    if rondas <= 0 or rondas > tope:
        return jsonify({"error": f"Número de rondas inválido (máx. {tope:,})"}), 400

    try:
        resultado = simulacion.simular(
            juego, rondas, apuesta, tipo, valor,
            metodo=metodo, semilla=int(semilla) if semilla else None,
            m_cuotas=int(datos.get("m_cuotas", simulacion.SIMULACIONES_CUOTA_LOTE)),
        )
    except (ValueError, KeyError, IndexError) as e:
        return jsonify({"error": f"Parámetros inválidos: {e}"}), 400
    return jsonify(resultado)


@app.route("/api/simulacion/blackjack/estrategias", methods=["POST"])
def simulacion_estrategias():
    """Barrido de estrategias de blackjack con la misma semilla."""
    datos = request.get_json() or {}
    rondas = int(datos.get("rondas", 20000))
    apuesta = float(datos.get("apuesta", 10))
    metodo = datos.get("metodo", "inversa")
    semilla = int(datos.get("semilla", 2024))

    if rondas <= 0 or rondas > 100_000:
        return jsonify({"error": "Número de rondas inválido (máx. 100,000)"}), 400
    if metodo not in rng.METODOS:
        return jsonify({"error": f"Método inválido. Use uno de {rng.METODOS}"}), 400

    return jsonify(simulacion.comparar_estrategias_blackjack(rondas, apuesta, semilla, metodo))


# ---------------------------------------------------------------------------
# Validación de los generadores y comparación de métodos
# ---------------------------------------------------------------------------


@app.route("/api/validacion/uniforme", methods=["GET", "POST"])
def validacion_uniforme():
    datos = request.get_json(silent=True) or {}
    n = int(datos.get("n", request.args.get("n", 100000)))
    semilla = int(datos.get("semilla", request.args.get("semilla", 987654321)))
    if n < 100 or n > 500_000:
        return jsonify({"error": "n fuera de rango (100 a 500,000)"}), 400
    return jsonify(validacion.validar_lcg(n, semilla))


@app.route("/api/validacion/juego", methods=["POST"])
def validacion_juego():
    datos = request.get_json() or {}
    juego = datos.get("juego", "ruleta")
    n = int(datos.get("n", 60000))
    metodo = datos.get("metodo", "inversa")
    semilla = int(datos.get("semilla", 13579))

    if juego not in simulacion.JUEGOS:
        return jsonify({"error": f"Juego inválido. Use uno de {simulacion.JUEGOS}"}), 400
    if metodo not in rng.METODOS:
        return jsonify({"error": f"Método inválido. Use uno de {rng.METODOS}"}), 400
    if n < 100 or n > 300_000:
        return jsonify({"error": "n fuera de rango (100 a 300,000)"}), 400

    return jsonify(validacion.validar_juego(juego, n, metodo, semilla))


@app.route("/api/comparacion", methods=["POST"])
def comparacion_metodos():
    """Inversa vs aceptación-rechazo en un juego, o en todos."""
    datos = request.get_json() or {}
    juego = datos.get("juego", "todos")
    n = int(datos.get("n", 40000))
    semilla = int(datos.get("semilla", 13579))

    if n < 100 or n > 300_000:
        return jsonify({"error": "n fuera de rango (100 a 300,000)"}), 400
    if juego == "todos":
        return jsonify(validacion.comparar_todos(n, semilla))
    if juego not in simulacion.JUEGOS:
        return jsonify({"error": f"Juego inválido. Use uno de {simulacion.JUEGOS}"}), 400
    return jsonify(validacion.comparar_metodos(juego, n, semilla))


# ---------------------------------------------------------------------------
# Llegadas de jugadores (proceso de Poisson)
# ---------------------------------------------------------------------------


@app.route("/api/llegadas", methods=["POST"])
def llegadas_generar():
    datos = request.get_json() or {}
    horas = float(datos.get("horas", 24))
    metodo = datos.get("metodo", "inversa")
    semilla = datos.get("semilla")

    if metodo not in rng.METODOS:
        return jsonify({"error": f"Método inválido. Use uno de {rng.METODOS}"}), 400
    if horas <= 0 or horas > 24 * 30:
        return jsonify({"error": "Horas fuera de rango (0 a 720)"}), 400

    instantes, gen = llegadas.generar(
        horas, metodo, semilla=int(semilla) if semilla else None
    )
    por_hora = [0] * int(min(24, max(1, horas)) if horas <= 24 else 24)
    for t in instantes:
        por_hora[int(t) % len(por_hora)] += 1

    return jsonify({
        "metodo": metodo,
        "etiqueta_metodo": rng.ETIQUETAS_METODO[metodo],
        "horas": horas,
        "tasa_por_hora": llegadas.TASA_POR_HORA,
        "llegadas_por_hora": por_hora,
        "total_llegadas": len(instantes),
        "esperado": llegadas.lambda_acumulada(horas),
        "instantes": [round(t, 4) for t in instantes[:500]],
        "metricas": gen.metricas(),
    })


@app.route("/api/llegadas/validacion", methods=["POST"])
def llegadas_validacion():
    datos = request.get_json() or {}
    horas = float(datos.get("horas", 24))
    repeticiones = int(datos.get("repeticiones", 200))
    metodo = datos.get("metodo", "inversa")

    if metodo not in rng.METODOS:
        return jsonify({"error": f"Método inválido. Use uno de {rng.METODOS}"}), 400
    if repeticiones < 1 or repeticiones > 2000:
        return jsonify({"error": "Repeticiones fuera de rango (1 a 2000)"}), 400

    return jsonify({
        "validacion": llegadas.validar(horas, repeticiones, metodo),
        "comparacion": llegadas.comparar_metodos(horas, max(10, repeticiones // 4)),
    })


# ---------------------------------------------------------------------------
# El piso del casino (sistema de llegadas y salidas)
# ---------------------------------------------------------------------------


@app.route("/api/piso", methods=["POST"])
def piso_simular():
    datos = request.get_json() or {}
    horas = float(datos.get("horas", 24))
    metodo = datos.get("metodo", "inversa")
    semilla = datos.get("semilla")

    if metodo not in rng.METODOS:
        return jsonify({"error": f"Método inválido. Use uno de {rng.METODOS}"}), 400
    if horas <= 0 or horas > 24 * 7:
        return jsonify({"error": "Horas fuera de rango (0 a 168)"}), 400

    return jsonify(piso.simular_dia(horas, metodo, semilla=int(semilla) if semilla else None))


@app.route("/api/piso/comparacion", methods=["POST"])
def piso_comparacion():
    datos = request.get_json() or {}
    horas = float(datos.get("horas", 24))
    replicas = int(datos.get("replicas", 12))
    semilla_base = int(datos.get("semilla_base", 90210))

    if horas <= 0 or horas > 24 * 7:
        return jsonify({"error": "Horas fuera de rango (0 a 168)"}), 400
    if replicas < 2 or replicas > 30:
        return jsonify({"error": "Réplicas fuera de rango (2 a 30)"}), 400

    return jsonify(piso.comparar_metodos(horas, replicas, semilla_base))


@app.route("/api/reporte", methods=["GET", "POST"])
def reporte():
    """Todo el paquete de validación y comparación en una sola llamada."""
    datos = request.get_json(silent=True) or {}
    return jsonify(validacion.reporte_completo(
        n_uniformes=int(datos.get("n_uniformes", 50000)),
        n_por_juego=int(datos.get("n_por_juego", 30000)),
        semilla=int(datos.get("semilla", 13579)),
    ))


if __name__ == "__main__":
    app.run(debug=True)
