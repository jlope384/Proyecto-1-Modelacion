"""API del panel de análisis (Proyecto 2).

El frontend (React + Vite, carpeta frontend/) llama a estas rutas mediante el
proxy de vite.config.js. Cada pestaña de la UI se conecta con una parte del
proyecto en Python:

    GET  /api/config                    parámetros calibrados, pisos base y mejorado (Fases 6 y 7)
    POST /api/piso                      simula un día con la configuración elegida (motor casino/piso.py)
    GET  /api/datos/referencia          tabla Real / Base / Mejorada y llegadas por día (Fases 5, 6 y 8)
    GET  /api/optimizacion/resultado    resultado del GA y su convergencia (Fase 7)
    POST /api/optimizacion/correr       lanza el GA en versión mini (src/optimizacion/genetico.py --prueba)
    GET  /api/optimizacion/estado       progreso de la versión mini
    GET  /api/escenarios                base, mejorada y sensibilidad con IC 95 % (Fase 8 y área por unidad)
    GET  /api/validacion                pruebas del generador, Little, conservación y hold por juego

Las rutas GET solo leen archivos de resultados/; si falta uno devuelven 404
con el comando que lo genera. Ejecutar desde backend/: python app.py
"""
import csv
import json
import math
import statistics
import subprocess
import sys
import threading
import time
from functools import lru_cache
from pathlib import Path

from flask import Flask, jsonify, request

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from casino import dados, piso, ruleta, tragamonedas, validacion  # noqa: E402
from modelo import escenario as esc  # noqa: E402

RES = RAIZ / "resultados"
ARCHIVOS = {
    "parametros": (RES / "calibracion" / "parametros.json", "python src/calibracion/calibrar.py"),
    "llegadas_dia": (RES / "calibracion" / "llegadas_dia_semana.csv", "python src/calibracion/calibrar.py"),
    "ga": (RES / "optimizacion" / "resultado.json", "python src/optimizacion/genetico.py"),
    "historial": (RES / "optimizacion" / "historial.csv", "python src/optimizacion/genetico.py"),
    "escenarios": (RES / "experimentos" / "escenarios.json", "python src/experimentos/correr.py"),
    "comparacion": (RES / "experimentos" / "comparacion_real.json", "python src/experimentos/correr.py"),
    "replicas": (RES / "experimentos" / "replicas.jsonl", "python src/experimentos/correr.py"),
}

# Ventaja de la casa por apuesta del piso. Blackjack no tiene forma cerrada:
# se midió con 200,000 manos (docs-proyecto2/hold_juegos.md).
HOLD_TEORICO = {
    "tragamonedas": {"valor": -tragamonedas.retorno_teorico(), "origen": "teórico, tabla de pagos"},
    "blackjack": {"valor": 0.0092, "origen": "simulado, 200,000 manos con estrategia básica"},
    "ruleta": {"valor": -ruleta.retorno_teorico("color", "rojo"), "origen": "teórico, rojo en ruleta europea"},
    "dados": {"valor": -dados.retorno_teorico("field", None), "origen": "teórico, apuesta field"},
}

# Justificación de los parámetros del GA, la misma de docs-proyecto2/genetico.md
JUSTIFICACION_GA = {
    "poblacion": "Solo hay 3 genes libres; 20 individuos cubren bien el espacio.",
    "generaciones_max": "Tope; el GA para antes si se estanca.",
    "prob_cruce": "Valor usual en GA de codificación entera.",
    "prob_mutacion": "Alta porque solo hay 3 genes libres (±1 por gen).",
    "torneo": "Presión de selección moderada.",
    "elite": "Conserva a los 2 mejores entre generaciones.",
    "estancamiento": "Generaciones sin mejora para detenerse.",
    "replicas_fitness": "Promedio de 10 días con las mismas semillas para todos (números aleatorios comunes).",
    "replicas_reevaluacion": "Los 5 mejores se re-evalúan con 30 semillas nuevas antes de elegir.",
    "lambda_penalizacion": "Multiplica el ingreso base por cada punto de abandono sobre el 10 %.",
}

app = Flask(__name__)


class FaltaArchivo(Exception):
    pass


@app.errorhandler(FaltaArchivo)
def _falta(e):
    return jsonify({"error": str(e)}), 404


def _ruta(clave):
    ruta, comando = ARCHIVOS[clave]
    if not ruta.exists():
        raise FaltaArchivo(f"Falta {ruta.relative_to(RAIZ)}. Genéralo desde la raíz con: {comando}")
    return ruta


def _json(clave):
    with open(_ruta(clave), encoding="utf-8") as f:
        return json.load(f)


def _csv(clave):
    with open(_ruta(clave), encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _replicas():
    with open(_ruta("replicas"), encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def _conteos_de(datos):
    conteos = {}
    for j in esc.JUEGOS:
        try:
            v = int(datos.get(j))
        except (TypeError, ValueError):
            raise ValueError(f"Cantidad inválida para {j}")
        if v < esc.MINIMO_UNIDADES or v > 500:
            raise ValueError(f"{j}: entre {esc.MINIMO_UNIDADES} y 500 unidades")
        conteos[j] = v
    return conteos


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------


@app.route("/api/config")
def config():
    p = _json("parametros")
    ga = _json("ga")
    out = {
        "juegos": list(esc.JUEGOS),
        "piso_base": p["piso_base"],
        "piso_mejorada": ga["mejorada"]["conteos"],
        "area_por_unidad": p["area_por_unidad"],
        "area_base": p["area_base"],
        "puestos_por_unidad": p["puestos_por_unidad"],
        "pesos_demanda": p["pesos_demanda"],
        "factor_llegadas_calibrado": p["factor_llegadas"],
        "sesiones_dia_calibradas": p["nivel_visitantes_dia"] * p["sesiones_por_visitante"],
        "paciencia_media_min": piso.PACIENCIA_MEDIA_MIN,
        "limite_abandono": p["limite_abandono"],
        "procedencia": p.get("procedencia", {}),
    }
    # Win por unidad y día de la corrida principal (100 réplicas), para "Armar piso".
    try:
        reps = [r for r in _replicas() if r["condicion"] == "principal"]
        for nombre, conteos in (("base", p["piso_base"]), ("mejorada", ga["mejorada"]["conteos"])):
            fs = [r for r in reps if r["configuracion"] == nombre]
            if fs:
                out[f"win_por_unidad_dia_{nombre}"] = {
                    j: statistics.fmean(r["ingreso_por_juego"][j] for r in fs) / conteos[j] for j in esc.JUEGOS}
                out[f"ingreso_dia_{nombre}"] = statistics.fmean(r["ingreso_total"] for r in fs)
    except FaltaArchivo:
        pass
    return jsonify(out)


# ---------------------------------------------------------------------------
# El piso: un día simulado
# ---------------------------------------------------------------------------


@app.route("/api/piso", methods=["POST"])
def piso_simular():
    datos = request.get_json(silent=True) or {}
    p = _json("parametros")
    try:
        conteos = _conteos_de(datos.get("conteos") or p["piso_base"])
        factor = float(datos.get("factor_llegadas", 1.0))
        paciencia = float(datos.get("paciencia_media_min", piso.PACIENCIA_MEDIA_MIN))
        semilla = int(datos.get("semilla", 42))
    except (TypeError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    if not 0.5 <= factor <= 2.0:
        return jsonify({"error": "Factor de llegadas fuera de rango (0.5 a 2.0)"}), 400
    if not 1 <= paciencia <= 60:
        return jsonify({"error": "Paciencia fuera de rango (1 a 60 min)"}), 400

    t0 = time.perf_counter()
    kw = esc.argumentos(p, conteos, factor_llegadas=p["factor_llegadas"] * factor,
                        paciencia_media_min=paciencia)
    r = piso.simular_dia(semilla=semilla, **kw)
    area = esc.area(conteos)
    hold = {}
    for j in esc.JUEGOS:
        apostado = r["apostado_por_juego"][j]
        hold[j] = {
            "unidades": conteos[j],
            "puestos": conteos[j] * esc.PUESTOS[j],
            "apostado": apostado,
            "ingreso": r["ingreso_por_juego"][j],
            "hold": r["ingreso_por_juego"][j] / apostado if apostado else None,
            "win_por_unidad": r["ingreso_por_juego"][j] / conteos[j],
            "utilizacion": r["utilizacion"][j],
        }
    capacidad = sum(conteos[j] * esc.PUESTOS[j] for j in esc.JUEGOS)
    ocupacion = sum(r["utilizacion"][j] * conteos[j] * esc.PUESTOS[j] for j in esc.JUEGOS)
    apostado_total = sum(r["apostado_por_juego"].values())
    return jsonify({
        "conteos": conteos,
        "area": area, "area_base": p["area_base"], "dentro_del_area": area <= p["area_base"],
        "factor_llegadas": factor, "paciencia_media_min": paciencia, "semilla": semilla,
        "llegadas": r["llegadas_totales"], "atendidos": r["atendidos"], "abandonos": r["abandonos"],
        "prob_abandono": r["prob_abandono"], "prob_congestion": r["prob_congestion"],
        "espera_promedio_min": r["espera_promedio_min"],
        "tiempo_sistema_promedio_min": r["tiempo_sistema_promedio_min"],
        "utilizacion_global": ocupacion / capacidad if capacidad else 0.0,
        "ingreso_total": r["ingreso_total"],
        "hold_global": r["ingreso_total"] / apostado_total if apostado_total else None,
        "por_juego": hold,
        "por_hora": {
            "llegadas": r["llegadas_por_hora"],
            "abandonos": r["abandonos_por_hora"],
            # área bajo la cola en cada hora / 1 h = clientes en cola en promedio esa hora
            "cola_promedio": r["cola_promedio_por_hora"],
        },
        "little": r["little"],
        "conservacion": r["atendidos"] + r["abandonos"] == r["llegadas_totales"],
        "limite_abandono": p["limite_abandono"],
        "segundos": time.perf_counter() - t0,
    })


# ---------------------------------------------------------------------------
# Datos reales
# ---------------------------------------------------------------------------


@app.route("/api/datos/referencia")
def datos_referencia():
    comp = _json("comparacion")
    dias = _csv("llegadas_dia")
    filas = comp["filas"]
    mezcla = {}
    for col in ("real", "base", "mejorada"):
        mezcla[col] = next(f[col] for f in filas
                           if f["metrica"].startswith("Participación") and f["juego_o_dia"] == "tragamonedas")
    return jsonify({
        **comp,
        "llegadas_dia_semana": [{k: (v if k == "dia" else float(v)) for k, v in d.items()} for d in dias],
        "mezcla_tragamonedas": mezcla,
        "fuentes": {
            "nevada": "Nevada Gaming Control Board, Monthly Revenue Report, ene-dic 2024 (validación); 2023 para calibrar",
            "gkl": "Grand Korea Leisure, visitantes diarios de 3 sucursales, 2024 (validación); 2023 para calibrar",
        },
    })


# ---------------------------------------------------------------------------
# Optimización
# ---------------------------------------------------------------------------


@app.route("/api/optimizacion/resultado")
def optimizacion_resultado():
    ga = _json("ga")
    hist = _csv("historial")
    params = [{"clave": k, "valor": v, "justificacion": JUSTIFICACION_GA.get(k, "")}
              for k, v in ga["parametros_ga"].items() if k in JUSTIFICACION_GA]
    return jsonify({
        "parametros": params,
        "historial": [{k: float(v) for k, v in h.items()} for h in hist],
        "base": ga["base"], "mejorada": ga["mejorada"],
        "diferencia": ga["diferencia_mejorada_menos_base"],
        "reevaluacion": ga["reevaluacion"],
        "comprobacion": ga["comprobacion_restricciones"],
        "area_por_unidad": ga["area_por_unidad"],
        "configuraciones_evaluadas": ga["configuraciones_evaluadas"],
        "simulaciones": ga["simulaciones"],
        "segundos": ga["segundos"],
    })


_mini = {"proceso": None, "inicio": None, "log": RES / "optimizacion_prueba" / "consola_api.log"}
_mini_lock = threading.Lock()


@app.route("/api/optimizacion/correr", methods=["POST"])
def optimizacion_correr():
    """Lanza el GA mini (población 6, 3 generaciones, 3 réplicas) en un proceso aparte."""
    with _mini_lock:
        pr = _mini["proceso"]
        if pr is not None and pr.poll() is None:
            return jsonify({"error": "Ya hay una corrida mini en curso"}), 409
        _mini["log"].parent.mkdir(parents=True, exist_ok=True)
        log = open(_mini["log"], "w", encoding="utf-8")
        _mini["proceso"] = subprocess.Popen(
            [sys.executable, "-u", str(RAIZ / "src" / "optimizacion" / "genetico.py"), "--prueba",
             "--procesos", "4", "--salida", "optimizacion_prueba"],
            cwd=str(RAIZ), stdout=log, stderr=subprocess.STDOUT)
        _mini["inicio"] = time.time()
    return jsonify({"iniciado": True}), 202


@app.route("/api/optimizacion/estado")
def optimizacion_estado():
    pr = _mini["proceso"]
    if pr is None:
        return jsonify({"estado": "sin_correr"})
    log = _mini["log"].read_text(encoding="utf-8") if _mini["log"].exists() else ""
    codigo = pr.poll()
    out = {"estado": "corriendo" if codigo is None else ("terminado" if codigo == 0 else "error"),
           "segundos": time.time() - _mini["inicio"], "log": log.splitlines()[-12:]}
    if codigo == 0:
        with open(RES / "optimizacion_prueba" / "resultado.json", encoding="utf-8") as f:
            r = json.load(f)
        out["resultado"] = {"base": r["base"], "mejorada": r["mejorada"],
                            "diferencia": r["diferencia_mejorada_menos_base"],
                            "comprobacion": r["comprobacion_restricciones"],
                            "parametros": r["parametros_ga"]}
    return jsonify(out)


# ---------------------------------------------------------------------------
# Escenarios
# ---------------------------------------------------------------------------


@app.route("/api/escenarios")
def escenarios():
    out = _json("escenarios")
    # Sensibilidad al área por unidad (src/experimentos/sensibilidad_area.py), si ya se corrió.
    ruta_area = RES / "experimentos" / "sensibilidad_area.json"
    if ruta_area.exists():
        with open(ruta_area, encoding="utf-8") as f:
            out["sensibilidad_area"] = json.load(f)
    return jsonify(out)


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _validacion_generador():
    lcg = validacion.validar_lcg(50000, 13579, comparar_con_python=False)["lcg_propio"]
    pruebas = [{"nombre": t["prueba"], "hipotesis": t.get("hipotesis_nula", ""),
                "estadistico": t.get("estadistico"), "p_valor": t.get("p_valor"),
                "aprobado": not t.get("rechaza_h0", False)} for t in lcg["pruebas"]]
    # Validación por réplicas (validacion.validar_replicado del Proyecto 1): una
    # sola chi² rechaza por azar 1 de cada 20 veces; con 100 semillas la tasa
    # de rechazo debe rondar el 5 % y los p-valores ser uniformes.
    juegos = []
    for j in esc.JUEGOS:
        r = validacion.validar_replicado(j, n=20000, replicas=100)
        ks = r["prueba_uniformidad_p_valores"]
        juegos.append({"juego": j, "replicas": r["replicas"], "n": r["n_por_replica"],
                       "rechazos": r["rechazos"], "tasa_rechazo": r["tasa_rechazo_observada"],
                       "tasa_esperada": r["tasa_rechazo_esperada"], "p_medio": r["p_valor_medio"],
                       "ks_p": ks["p_valor"], "veredicto": r["veredicto"],
                       "aprobado": r["veredicto"].startswith("Comportamiento correcto")})
    return {"generador": lcg["generador"], "n": lcg["n"], "pruebas": pruebas, "juegos": juegos}


def _hold_simulado():
    """
    Hold agregado por juego (suma de ingreso / suma de apostado) en las 100
    réplicas de la condición principal, piso base. Prueba: z sobre
    d_i = ingreso_i - h0 * apostado_i (si el hold real es h0, E[d] = 0).
    """
    reps = [r for r in _replicas() if r["condicion"] == "principal" and r["configuracion"] == "base"]
    out = []
    for j in esc.JUEGOS:
        h0 = HOLD_TEORICO[j]["valor"]
        d = [r["ingreso_por_juego"][j] - h0 * r["apostado_por_juego"][j] for r in reps]
        apo = statistics.fmean(r["apostado_por_juego"][j] for r in reps)
        se = statistics.stdev(d) / math.sqrt(len(d))
        z = statistics.fmean(d) / se if se else 0.0
        sim = sum(r["ingreso_por_juego"][j] for r in reps) / sum(r["apostado_por_juego"][j] for r in reps)
        out.append({"juego": j, "teorico": h0, "origen_teorico": HOLD_TEORICO[j]["origen"], "simulado": sim,
                    "ic95": [sim - 1.96 * se / apo, sim + 1.96 * se / apo], "z": z,
                    "aprobado": abs(z) <= 1.96, "replicas": len(reps)})
    return out


@app.route("/api/validacion")
def validacion_completa():
    gen = _validacion_generador()
    esc_ = _json("escenarios")
    c = esc_["consistencia"]
    sistema = [
        {"nombre": "Ley de Little", "que": "L = λ · W en cada día simulado",
         "resultado": f"error relativo máximo {100 * c['little_error_rel_max']:.2f} % en {c['replicas_totales']} réplicas",
         "aprobado": c["little_ok"], "criterio": "error relativo < 5 %"},
        {"nombre": "Conservación de clientes", "que": "llegadas = atendidos + abandonos",
         "resultado": f"se cumple en las {c['replicas_totales']} réplicas" if c["conservacion_clientes"]
         else "falla en alguna réplica",
         "aprobado": c["conservacion_clientes"], "criterio": "igualdad exacta"},
    ]
    return jsonify({**gen, "sistema": sistema, "hold": _hold_simulado(),
                    "criterio_hold": "|z| ≤ 1.96: el hold teórico es compatible con el simulado al 5 %"})


@app.route("/api/salud")
def salud():
    return jsonify({"ok": True, "archivos": {k: v[0].exists() for k, v in ARCHIVOS.items()}})


if __name__ == "__main__":
    app.run(debug=True)
