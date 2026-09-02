from . import dados, ruleta, tragamonedas

MAX_PUNTOS_HISTORIAL = 300


def simular(juego, rondas, apuesta, tipo=None, valor=None, saldo_inicial=1000):
    saldo = saldo_inicial
    historial = [saldo]
    victorias = 0

    for _ in range(rondas):
        if juego == "ruleta":
            _, _, gano, ganancia = ruleta.jugar(apuesta, tipo, valor)
        elif juego == "dados":
            _, _, _, gano, ganancia = dados.jugar(apuesta, tipo, valor)
        elif juego == "tragamonedas":
            _, gano, ganancia = tragamonedas.jugar(apuesta)
        else:
            raise ValueError("Juego inválido")

        saldo += ganancia
        historial.append(saldo)
        if gano:
            victorias += 1

    total_apostado = apuesta * rondas
    ganancia_neta_total = saldo - saldo_inicial

    paso = max(1, len(historial) // MAX_PUNTOS_HISTORIAL)
    historial_muestreado = historial[::paso]

    return {
        "rondas": rondas,
        "victorias": victorias,
        "derrotas": rondas - victorias,
        "prob_victoria": victorias / rondas if rondas else 0,
        "saldo_inicial": saldo_inicial,
        "saldo_final": saldo,
        "ganancia_neta": ganancia_neta_total,
        "total_apostado": total_apostado,
        "retorno_sobre_apuesta": (ganancia_neta_total / total_apostado) if total_apostado else 0,
        "historial": historial_muestreado,
    }
