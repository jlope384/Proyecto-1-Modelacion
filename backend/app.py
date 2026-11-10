import secrets

from flask import Flask, jsonify, request

from casino import (
    blackjack,
    dados,
    llegadas,
    piso,
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

# Mesa de blackjack de la sesión interactiva. Usan el generador
# global, así que cambiar el método desde /api/generador también cambia cómo
# salen las cartas.
mesa_blackjack = blackjack.Mesa()


@app.route("/api/estado")
def estado():
    return jsonify({
        "saldo": saldo_jugador["saldo"],
        "generador": rng.generador_actual().fuente.describir(),
        "metodo": rng.generador_actual().metodo,
    })


@app.route("/api/reiniciar", methods=["POST"])
def reiniciar():
    global mesa_blackjack
    saldo_jugador["saldo"] = SALDO_INICIAL
    mesa_blackjack = blackjack.Mesa()
    return jsonify({"saldo": saldo_jugador["saldo"]})


@app.route("/api/generador", methods=["GET", "POST"])
def generador():
    """
    Consulta o cambia el método de generación de la sesión interactiva.
    Sirve para demostrar en vivo que los dos métodos producen el mismo juego.
    """
    global mesa_blackjack
    if request.method == "POST":
        datos = request.get_json() or {}
        metodo = datos.get("metodo")
        if metodo is not None and metodo not in rng.METODOS:
            return jsonify({"error": f"Método inválido. Use uno de {rng.METODOS}"}), 400
        semilla = datos.get("semilla")
        rng.configurar_generador(metodo=metodo, semilla=int(semilla) if semilla else None)
        mesa_blackjack = blackjack.Mesa()

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

    tope = 100_000
    if rondas <= 0 or rondas > tope:
        return jsonify({"error": f"Número de rondas inválido (máx. {tope:,})"}), 400

    try:
        resultado = simulacion.simular(
            juego, rondas, apuesta, tipo, valor,
            metodo=metodo, semilla=int(semilla) if semilla else None,
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
