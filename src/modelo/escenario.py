"""Escenario del piso que comparten la calibración (Fase 6), el GA (Fase 7) y
los experimentos (Fase 8).

Aquí se juntan tres cosas:
  1. Los datos de referencia ya procesados (Nevada y Grand Korea Leisure).
  2. Los supuestos del modelo, cada uno con su etiqueta de procedencia.
  3. Los parámetros calibrados, que escribe `src/calibracion/calibrar.py` en
     `resultados/calibracion/parametros.json`.

El motor sigue siendo `backend/casino/piso.py`; este módulo solo arma los
argumentos de `simular_dia` para una configuración del piso.

Solo biblioteca estándar.
"""
import csv
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ / "backend") not in sys.path:
    sys.path.insert(0, str(RAIZ / "backend"))

from casino import llegadas, piso  # noqa: E402

DATOS = RAIZ / "datos" / "procesados"
RESULTADOS = RAIZ / "resultados"
PARAMETROS_CALIBRADOS = RESULTADOS / "calibracion" / "parametros.json"

JUEGOS = ("tragamonedas", "blackjack", "ruleta", "dados")
MESAS = ("blackjack", "ruleta", "dados")
DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")

# ---------------------------------------------------------------------------
# Supuestos (sin dato; se declaran y se prueban en la sensibilidad)
# ---------------------------------------------------------------------------

# Puestos por mesa, los mismos del Proyecto 1. Supuesto.
PUESTOS = {"tragamonedas": 1, "blackjack": 5, "ruleta": 7, "dados": 8}

# Área equivalente de cada unidad, en "máquinas". Estimación del equipo: una
# mesa ocupa lo de sus puestos más el espacio del crupier (blackjack 5 + 1,
# ruleta 7 + 1, dados 8 + 2 porque craps lleva dos o más empleados). No hay
# fuente; se prueba en la sensibilidad de área.
AREA = {"tragamonedas": 1, "blackjack": 6, "ruleta": 8, "dados": 10}

# El piso base es un local promedio de Nevada 2023 (unidades por local de
# cada juego) dividido entre ESCALA_PISO. 1/4 es la escala más pequeña en la
# que ruleta (4.41 / 4 = 1.10) y dados (3.15 / 4 = 0.79) redondean a una mesa.
# Ojo: las unidades por local de cada juego se promedian sobre locales
# distintos (tragamonedas en ~310 locales, mesas en ~100), así que este piso
# tiene más mesas por máquina que la composición estatal. Por eso la mezcla
# de ingreso se compara con la "mezcla implícita" (ver calibrar.py), que usa
# la composición estatal, y no con la mezcla de este piso.
ESCALA_PISO = 4

# Un "cliente" del simulador es una sesión en un juego; un visitante de GKL
# juega varias en una visita. Supuesto: 3 sesiones por visitante. Con este
# valor el piso base opera cerca del límite de 10% de abandono (ver
# docs-proyecto2/calibracion.md); con 1 sesión no hay congestión y no habría
# nada que optimizar. Se prueba con el factor de llegadas en la sensibilidad.
SESIONES_POR_VISITANTE = 3.0

# Restricción de la pregunta de investigación.
LIMITE_ABANDONO = 0.10

# Regla de negocio: el casino sigue ofreciendo los cuatro juegos, así que
# cada uno conserva al menos una unidad. Además, con la demanda por juego
# fija, un juego sin unidades no tendría dónde atender a quien lo elige.
MINIMO_UNIDADES = 1

# Periodos de los datos.
ANIO_CALIBRACION = 2023
ANIO_VALIDACION = 2024


# ---------------------------------------------------------------------------
# Lectura de datos procesados
# ---------------------------------------------------------------------------


def leer_nevada(periodo):
    """{metrica: {juego: valor}} de nevada_referencia.csv para 'calibracion' o 'validacion'."""
    out = {}
    with open(DATOS / "nevada_referencia.csv", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if fila["periodo"] == periodo:
                out.setdefault(fila["metrica"], {})[fila["juego"]] = float(fila["valor"])
    if not out:
        raise ValueError(f"periodo sin datos en nevada_referencia.csv: {periodo}")
    return out


def leer_gkl_dia_semana(anio, codigo="TODAS"):
    """{dia: {"visitantes": promedio, "factor": factor}} de gkl_dia_semana.csv."""
    out = {}
    with open(DATOS / "gkl_dia_semana.csv", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if int(fila["anio"]) == anio and fila["codigo"] == codigo:
                out[fila["dia_semana"]] = {"visitantes": float(fila["visitantes_prom"]),
                                           "factor": float(fila["factor"])}
    if set(out) != set(DIAS):
        raise ValueError(f"faltan días de la semana de GKL para {anio}/{codigo}")
    return out


def leer_gkl_nivel(anio):
    """Visitantes promedio por día y por sucursal (TODAS / número de sucursales)."""
    sucursales, total = 0, None
    with open(DATOS / "gkl_resumen_anual.csv", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if int(fila["anio"]) != anio:
                continue
            if fila["codigo"] == "TODAS":
                total = float(fila["visitantes_prom_dia"])
            else:
                sucursales += 1
    if total is None or not sucursales:
        raise ValueError(f"año sin datos en gkl_resumen_anual.csv: {anio}")
    return total / sucursales


# ---------------------------------------------------------------------------
# Piso base, demanda y área
# ---------------------------------------------------------------------------


def piso_base():
    """Unidades por juego: local promedio de Nevada 2023 / ESCALA_PISO, redondeado, mínimo 1."""
    unidades = leer_nevada("calibracion")["unidades_por_local"]
    return {j: max(1, round(unidades[j] / ESCALA_PISO)) for j in JUEGOS}


def pesos_demanda(conteos=None):
    """
    Probabilidad de que una sesión elija cada juego. Supuesto: el operador
    dimensionó el piso base según su demanda, así que la demanda es
    proporcional a los puestos del piso base. Queda fija cuando el GA cambia
    el piso: reacomodar mesas no cambia lo que la gente quiere jugar.
    """
    conteos = conteos or piso_base()
    puestos = {j: conteos[j] * PUESTOS[j] for j in JUEGOS}
    total = sum(puestos.values())
    return {j: puestos[j] / total for j in JUEGOS}


def area(conteos):
    return sum(AREA[j] * conteos[j] for j in JUEGOS)


def recursos(conteos):
    """Convierte {juego: unidades} al formato `recursos` de piso.simular_dia."""
    return {j: {"mesas": int(conteos[j]), "puestos_por_mesa": PUESTOS[j]}
            for j in JUEGOS if conteos[j] > 0}


def factor_llegadas(nivel_visitantes, sesiones=SESIONES_POR_VISITANTE, factor_dia=1.0):
    """
    Factor que se pasa a simular_dia para que las sesiones esperadas del día
    sean nivel_visitantes * sesiones * factor_dia. La forma horaria es la de
    llegadas.TASA_POR_HORA (supuesto del Proyecto 1, GKL no trae horas).
    """
    return nivel_visitantes * sesiones * factor_dia / sum(llegadas.TASA_POR_HORA)


# ---------------------------------------------------------------------------
# Parámetros calibrados y simulación
# ---------------------------------------------------------------------------


def cargar_parametros(ruta=PARAMETROS_CALIBRADOS):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def argumentos(parametros, conteos, **cambios):
    """
    kwargs de piso.simular_dia para una configuración del piso. `cambios`
    sobrescribe cualquier argumento (por ejemplo factor_llegadas o
    paciencia_media_min para la sensibilidad).
    """
    kw = {
        "horas": 24,
        "recursos": recursos(conteos),
        "pesos_juego": dict(parametros["pesos_demanda"]),
        "factor_llegadas": parametros["factor_llegadas"],
        "escala_bankroll_mesas": parametros["escala_bankroll_mesas"],
        # números aleatorios comunes reales entre configuraciones (ver piso.py)
        "flujos_por_cliente": True,
    }
    kw.update(cambios)
    return kw


def simular(parametros, conteos, semilla, **cambios):
    """
    Corre un día y devuelve solo las métricas que usan la calibración, el GA y
    los experimentos (la salida completa de simular_dia es grande para
    pasarla entre procesos).
    """
    faltan = [j for j in JUEGOS if conteos[j] < MINIMO_UNIDADES]
    if faltan:
        raise ValueError(f"cada juego necesita al menos {MINIMO_UNIDADES} unidad: {faltan}")
    r = piso.simular_dia(semilla=semilla, **argumentos(parametros, conteos, **cambios))
    return {
        "semilla": semilla,
        "llegadas": r["llegadas_totales"],
        "atendidos": r["atendidos"],
        "abandonos": r["abandonos"],
        "prob_abandono": r["prob_abandono"],
        "espera_promedio_min": r["espera_promedio_min"],
        "ingreso_total": r["ingreso_total"],
        "ingreso_por_juego": dict(r["ingreso_por_juego"]),
        "apostado_por_juego": dict(r["apostado_por_juego"]),
        "utilizacion": dict(r["utilizacion"]),
        "little_L_obs": r["little"]["L_observado"],
        "little_L_est": r["little"]["L_estimado_por_little"],
    }
