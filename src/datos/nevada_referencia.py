"""Deriva la tabla de calibración y validación a partir de nevada_mensual.csv.

Uso (desde la raíz del repo):
    python src/datos/nevada_referencia.py datos/procesados/nevada_mensual.csv \
        datos/procesados/nevada_referencia.csv

Solo usa las filas con periodo "mes" (un mes cada una) y agrega por periodo:
- calibracion: 2023-01 a 2023-12
- validacion:  2024-01 a 2024-12

Métricas, para los cuatro juegos del modelo (blackjack = Twenty One,
ruleta = Roulette, dados = Craps, tragamonedas = fila Total de Slot Machines):
- mezcla_ingreso_total: win del juego / (Total mesas + Total tragamonedas).
- mezcla_ingreso_4juegos: win del juego / suma del win de los cuatro juegos
  (lo comparable con el simulador, que solo tiene esos cuatro).
- win_por_unidad_mes_miles: win del periodo / unidades promedio / meses.
- unidades_por_local: promedio mensual de unidades / locales. OJO: cada juego
  tiene su propio número de locales (tragamonedas ~310, mesas ~100), así que
  estas cifras NO describen un mismo piso.
- unidades_estatales: promedio mensual de unidades en todo el estado. Es la
  composición con la que se calcula la mezcla de ingreso.
- win_pct: win percent de Nevada. En tragamonedas es win / dinero jugado
  (comparable con el hold del simulador); en mesas es sobre el drop (NO
  comparable, solo informativo).

`valor` es el agregado del periodo (cocientes de sumas); `desv_mensual` es la
desviación estándar del mismo indicador calculado mes a mes, para tener una
idea de la variabilidad real. Solo biblioteca estándar.
"""
import csv
import statistics
import sys
from collections import defaultdict
from pathlib import Path

PERIODOS = {
    "calibracion": [f"2023-{m:02d}" for m in range(1, 13)],
    "validacion": [f"2024-{m:02d}" for m in range(1, 13)],
}
JUEGOS = {  # (seccion, nombre en Nevada) -> nombre en el modelo
    ("mesas", "Twenty One"): "blackjack",
    ("mesas", "Roulette"): "ruleta",
    ("mesas", "Craps"): "dados",
    ("tragamonedas", "Total"): "tragamonedas",
}
UNIDAD = {
    "mezcla_ingreso_total": "fraccion",
    "mezcla_ingreso_4juegos": "fraccion",
    "win_por_unidad_mes_miles": "miles USD / unidad / mes",
    "unidades_por_local": "unidades / local",
    "unidades_estatales": "unidades",
    "win_pct": "%",
}


def leer(ruta):
    """{mes: {clave: fila}} con clave = (seccion, juego); solo periodo 'mes'."""
    datos = defaultdict(dict)
    with open(ruta, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["periodo"] != "mes":
                continue
            for c in ("locales", "unidades", "win_miles", "win_pct"):
                r[c] = float(r[c])
            datos[r["mes"]][(r["seccion"], r["juego"])] = r
    return datos


def metricas_de(meses_filas):
    """Métricas agregadas sobre una lista de dicts {clave: fila} (uno por mes)."""
    n = len(meses_filas)
    suma = lambda clave, campo: sum(m[clave][campo] for m in meses_filas)
    total = suma(("mesas", "Total"), "win_miles") + suma(("tragamonedas", "Total"), "win_miles")
    cuatro = sum(suma(clave, "win_miles") for clave in JUEGOS)
    out = {}
    for clave, juego in JUEGOS.items():
        win = suma(clave, "win_miles")
        unidades_prom = suma(clave, "unidades") / n
        out[("mezcla_ingreso_total", juego)] = win / total
        out[("mezcla_ingreso_4juegos", juego)] = win / cuatro
        out[("win_por_unidad_mes_miles", juego)] = win / unidades_prom / n
        out[("unidades_por_local", juego)] = statistics.mean(
            m[clave]["unidades"] / m[clave]["locales"] for m in meses_filas)
        out[("unidades_estatales", juego)] = unidades_prom
        out[("win_pct", juego)] = statistics.mean(m[clave]["win_pct"] for m in meses_filas)
    return out


def main(entrada, salida):
    datos = leer(entrada)
    filas = []
    for periodo, meses in PERIODOS.items():
        faltan = [m for m in meses if m not in datos]
        if faltan:
            sys.exit(f"Faltan meses de {periodo}: {faltan}")
        agregado = metricas_de([datos[m] for m in meses])
        por_mes = [metricas_de([datos[m]]) for m in meses]
        for (metrica, juego), valor in agregado.items():
            nota = ""
            if metrica == "win_pct":
                nota = ("win / dinero jugado (comparable)" if juego == "tragamonedas"
                        else "sobre el drop (no comparable con el hold)")
            filas.append({
                "periodo": periodo,
                "desde": meses[0], "hasta": meses[-1], "n_meses": len(meses),
                "metrica": metrica, "juego": juego,
                "valor": round(valor, 6),
                "desv_mensual": round(statistics.stdev(p[(metrica, juego)] for p in por_mes), 6),
                "unidad": UNIDAD[metrica], "nota": nota,
            })
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(filas)
    print(f"{len(filas)} filas en {salida}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
