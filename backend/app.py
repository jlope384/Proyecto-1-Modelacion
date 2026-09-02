import secrets

from flask import Flask, jsonify, request

from casino import dados, ruleta, simulacion, tragamonedas

# El frontend (React + Vite) corre aparte en su propio servidor de desarrollo
# y llama a esta API vía el proxy configurado en frontend/vite.config.js.
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

SALDO_INICIAL = 1000

# Estado en memoria (un único jugador, sin base de datos: simplifica el proyecto).
saldo_jugador = {"saldo": SALDO_INICIAL}


@app.route("/api/estado")
def estado():
    return jsonify({"saldo": saldo_jugador["saldo"]})


@app.route("/api/reiniciar", methods=["POST"])
def reiniciar():
    saldo_jugador["saldo"] = SALDO_INICIAL
    return jsonify({"saldo": saldo_jugador["saldo"]})


def _validar_apuesta(apuesta):
    if apuesta <= 0 or apuesta > saldo_jugador["saldo"]:
        return False
    return True


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

    reels, gano, ganancia = tragamonedas.jugar(apuesta)
    saldo_jugador["saldo"] += ganancia

    return jsonify({
        "reels": reels,
        "gano": gano,
        "ganancia": ganancia,
        "saldo": saldo_jugador["saldo"],
    })


@app.route("/api/simulacion", methods=["POST"])
def simulacion_ejecutar():
    datos = request.get_json()
    juego = datos["juego"]
    rondas = int(datos["rondas"])
    apuesta = float(datos["apuesta"])
    tipo = datos.get("tipo")
    valor = datos.get("valor")

    if rondas <= 0 or rondas > 100_000:
        return jsonify({"error": "Número de rondas inválido (máx. 100,000)"}), 400
    if apuesta <= 0:
        return jsonify({"error": "Apuesta inválida"}), 400

    resultado = simulacion.simular(juego, rondas, apuesta, tipo, valor)
    return jsonify(resultado)


if __name__ == "__main__":
    app.run(debug=True)
