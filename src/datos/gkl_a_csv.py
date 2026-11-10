"""Convierte el CSV de visitantes diarios de Grand Korea Leisure (GKL) en tablas usables.

Uso (desde la raíz del repo):
    python src/datos/gkl_a_csv.py "datos/crudos/gkl/<archivo>.csv" datos/procesados

Archivo de origen: data.go.kr, dataset 15116743, "그랜드코리아레저(주)_일별 방문고객 정보".
Lo revisado del archivo (versión 2026-06-18):
- Codificación CP949 (no UTF-8). 11 columnas:
  방문일자 (fecha), 영업장코드 (código), 영업점명 (sucursal), 성별 (sexo M/F/X),
  여권발급국가 (país, código), 여권발급국가명 (país), y cinco columnas de edad
  (60대이상, 50대 이상, 40대 이상, 30대 이상, 20대 이상).
- Las columnas de edad son CONTEOS de visitantes (enteros >= 0, sin vacíos):
  cada fila es un grupo fecha x sucursal x sexo x país, y la suma de las cinco
  columnas es el número de visitantes de ese grupo.
- Tres sucursales: CX = Coex (Seúl), HT = Dragon City (Seúl), LT = Lotte (Busan).
- Rango 2015-01-01 a 2026-06-23. Sin filas duplicadas.

Salidas (en la carpeta indicada):
- gkl_diario.csv: fecha, sucursal, visitantes y día de la semana, todos los días
  con registro, con la marca `excluido` para 2020-2022 (COVID: cierres en 2020-2021
  y fronteras abiertas a medias en 2022; el promedio diario de 2022 es ~35% del de 2019).
- gkl_resumen_anual.csv: días con registro y visitantes promedio por día, por año y sucursal.
- gkl_dia_semana.csv: para calibración (2023) y validación (2024), promedio de
  visitantes por sucursal y día de la semana, y el factor = promedio del día /
  promedio de la semana. El factor es lo que se usa en el modelo (se comparan
  patrones, no montos, porque GKL es un casino solo para extranjeros).

Los días sin fila para una sucursal se tratan como cerrados (no como cero) y no
entran en los promedios. Solo biblioteca estándar.
"""
import csv
import datetime as dt
import statistics
import sys
from collections import defaultdict
from pathlib import Path

SUCURSALES = {"CX": "Coex", "HT": "Dragon City", "LT": "Lotte Busan"}
DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
ANIOS_EXCLUIDOS = {2020, 2021, 2022}
PERIODOS = {"calibracion": 2023, "validacion": 2024}


def leer(ruta):
    """{(fecha, codigo): visitantes} sumando sexo, país y edades."""
    visitas = defaultdict(int)
    with open(ruta, encoding="cp949", newline="") as f:
        lector = csv.reader(f)
        cabecera = next(lector)
        if len(cabecera) != 11:
            raise ValueError(f"se esperaban 11 columnas, hay {len(cabecera)}")
        for fila in lector:
            fecha = dt.date.fromisoformat(fila[0])
            conteos = [int(x) for x in fila[6:11]]
            if min(conteos) < 0:
                raise ValueError(f"conteo negativo en {fila}")
            visitas[(fecha, fila[1])] += sum(conteos)
    return visitas


def escribir(ruta, filas):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    print(f"{len(filas)} filas en {ruta}")


def main(entrada, carpeta):
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    visitas = leer(entrada)

    diario = [{
        "fecha": f.isoformat(), "codigo": c, "sucursal": SUCURSALES.get(c, c),
        "dia_semana": DIAS[f.weekday()], "visitantes": v,
        "excluido": int(f.year in ANIOS_EXCLUIDOS),
    } for (f, c), v in sorted(visitas.items())]
    escribir(carpeta / "gkl_diario.csv", diario)

    por_anio = defaultdict(list)
    for (f, c), v in visitas.items():
        por_anio[(f.year, c)].append(v)
    totales_dia = defaultdict(int)
    for (f, c), v in visitas.items():
        totales_dia[f] += v
    for f, v in totales_dia.items():
        por_anio[(f.year, "TODAS")].append(v)
    resumen = [{
        "anio": a, "codigo": c, "dias_con_registro": len(vs),
        "visitantes_prom_dia": round(statistics.mean(vs), 1),
        "excluido": int(a in ANIOS_EXCLUIDOS),
    } for (a, c), vs in sorted(por_anio.items())]
    escribir(carpeta / "gkl_resumen_anual.csv", resumen)

    semana = []
    for periodo, anio in PERIODOS.items():
        for c in list(SUCURSALES) + ["TODAS"]:
            if c == "TODAS":
                serie = {f: v for f, v in totales_dia.items() if f.year == anio}
            else:
                serie = {f: v for (f, cc), v in visitas.items() if cc == c and f.year == anio}
            por_dia = defaultdict(list)
            for f, v in serie.items():
                por_dia[f.weekday()].append(v)
            prom_dia = {d: statistics.mean(vs) for d, vs in por_dia.items()}
            # promedio de la semana = media de los 7 promedios (no pesa más el día con más fechas)
            prom_semana = statistics.mean(prom_dia.values())
            for d in range(7):
                semana.append({
                    "periodo": periodo, "anio": anio, "codigo": c, "dia_semana": DIAS[d],
                    "n_dias": len(por_dia[d]),
                    "visitantes_prom": round(prom_dia[d], 1),
                    "desv": round(statistics.stdev(por_dia[d]), 1),
                    "factor": round(prom_dia[d] / prom_semana, 4),
                })
    escribir(carpeta / "gkl_dia_semana.csv", semana)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
