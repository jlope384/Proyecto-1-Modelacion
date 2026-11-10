"""Sensibilidad al área por unidad de las mesas (supuesto sin fuente).

Uso (desde la raíz del repo), después de correr el GA con otras áreas:
    python src/optimizacion/genetico.py --area blackjack=5,ruleta=6,dados=8 --salida optimizacion_area_menos25
    python src/optimizacion/genetico.py --area blackjack=8,ruleta=10,dados=13 --salida optimizacion_area_mas25
    python src/experimentos/sensibilidad_area.py [--procesos 4]

El área por unidad (máquina 1, blackjack 6, ruleta 8, dados 10) es una
estimación del equipo y define el trade-off que optimiza el GA. Aquí se
compara, para cada juego de áreas, el reparto que eligió el GA contra el piso
base con 100 réplicas pareadas (las mismas semillas 7001-7100 de la Fase 8).

La simulación de un día no depende del área (solo decide qué repartos caben),
así que las réplicas del piso base y de 84/5/1/2 se reutilizan de
resultados/experimentos/replicas.jsonl; solo se simulan los repartos nuevos.

Salidas en resultados/experimentos/:
    replicas_area.jsonl         réplicas de los repartos nuevos (se retoma si se interrumpe)
    sensibilidad_area.json      resumen por escenario de área

Solo biblioteca estándar.
"""
import argparse
import json
import statistics
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modelo import escenario as esc  # noqa: E402
from experimentos.correr import (REPLICAS_JSONL, SALIDA, diferencia_pareada,  # noqa: E402
                                 metricas_de, SEMILLA_INICIAL)

REPLICAS = 100
ESCENARIOS = (
    ("menos25", "Mesas 25 % más chicas", "optimizacion_area_menos25"),
    ("calibrado", "Áreas del modelo", "optimizacion"),
    ("mas25", "Mesas 25 % más grandes", "optimizacion_area_mas25"),
)
ARCHIVO = SALIDA / "replicas_area.jsonl"


def _simular(args):
    parametros, conteos, semilla = args
    r = esc.simular(parametros, conteos, semilla)
    r["conteos"] = conteos
    return r


def clave(conteos):
    return "/".join(str(conteos[j]) for j in esc.JUEGOS)


def area_con(conteos, areas):
    return sum(areas[j] * conteos[j] for j in esc.JUEGOS)


def leer(ruta):
    if not ruta.exists():
        return []
    with open(ruta, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--procesos", type=int, default=4)
    args = ap.parse_args()
    t0 = time.time()
    parametros = esc.cargar_parametros()
    semillas = [SEMILLA_INICIAL + i for i in range(REPLICAS)]

    # Réplicas ya hechas, por reparto: las de la Fase 8 (condición principal) y las propias.
    por_reparto = {}
    piso_ga = None
    for r in leer(REPLICAS_JSONL):
        if r["condicion"] == "principal":
            c = parametros["piso_base"] if r["configuracion"] == "base" else None
            if c is None:
                with open(esc.RESULTADOS / "optimizacion" / "resultado.json", encoding="utf-8") as f:
                    c = piso_ga = piso_ga or json.load(f)["mejorada"]["conteos"]
            por_reparto.setdefault(clave(c), {})[r["semilla"]] = r
    for r in leer(ARCHIVO):
        por_reparto.setdefault(clave(r["conteos"]), {})[r["semilla"]] = r

    escenarios = []
    for eid, etiqueta, carpeta in ESCENARIOS:
        ruta = esc.RESULTADOS / carpeta / "resultado.json"
        if not ruta.exists():
            print(f"Falta {ruta.relative_to(esc.RAIZ)}: corre el GA de ese escenario. Se omite.")
            continue
        with open(ruta, encoding="utf-8") as f:
            ga = json.load(f)
        escenarios.append((eid, etiqueta, carpeta, ga))

    # Simular lo que falte
    trabajos = []
    for _, _, _, ga in escenarios:
        c = ga["mejorada"]["conteos"]
        hechas = por_reparto.get(clave(c), {})
        trabajos += [(parametros, c, s) for s in semillas if s not in hechas]
    trabajos = list({(clave(t[1]), t[2]): t for t in trabajos}.values())
    if trabajos:
        print(f"{len(trabajos)} simulaciones nuevas, {args.procesos} procesos")
        with Pool(args.procesos) as pool, open(ARCHIVO, "a", encoding="utf-8") as f:
            for i, r in enumerate(pool.imap_unordered(_simular, trabajos, chunksize=2), 1):
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                f.flush()
                por_reparto.setdefault(clave(r["conteos"]), {})[r["semilla"]] = r
                if i % 25 == 0 or i == len(trabajos):
                    print(f"  {i}/{len(trabajos)}  {time.time() - t0:.0f} s")

    base = [por_reparto[clave(parametros["piso_base"])][s] for s in semillas]
    piso_ga = piso_ga or parametros["piso_base"]
    salida = []
    for eid, etiqueta, carpeta, ga in escenarios:
        areas = ga["area_por_unidad"]
        c = ga["mejorada"]["conteos"]
        mej = [por_reparto[clave(c)][s] for s in semillas]
        d = diferencia_pareada(mej, base)
        mb, mm = metricas_de(base), metricas_de(mej)
        area_ga_original = area_con(piso_ga, areas)
        salida.append({
            "id": eid, "etiqueta": etiqueta, "carpeta_ga": f"resultados/{carpeta}",
            "area_por_unidad": areas, "area_total": area_con(parametros["piso_base"], areas),
            "piso_base": parametros["piso_base"], "piso_elegido": c,
            "mismo_reparto_que_el_ga_principal": clave(c) == clave(piso_ga),
            "ga": {"configuraciones_evaluadas": ga["configuraciones_evaluadas"],
                   "generaciones": ga["parametros_ga"]["generaciones_corridas"],
                   "diferencia_reevaluacion_30": ga["diferencia_mejorada_menos_base"],
                   "comprobacion": ga["comprobacion_restricciones"]},
            "replicas": len(semillas), "semillas": [semillas[0], semillas[-1]],
            "base": {"ingreso_total": mb["ingreso_total"], "prob_abandono": mb["prob_abandono"],
                     "espera_promedio_min": mb["espera_promedio_min"]},
            "mejorada": {"ingreso_total": mm["ingreso_total"], "prob_abandono": mm["prob_abandono"],
                         "espera_promedio_min": mm["espera_promedio_min"]},
            "diferencia": d,
            "mejora_significativa": d["ingreso"]["ic95"][0] > 0,
            "mejorada_dentro_del_limite": mm["prob_abandono"]["media"] <= parametros["limite_abandono"],
            # ¿Cabe el reparto del GA principal (84/5/1/2) si las mesas midieran esto?
            "reparto_principal": piso_ga,
            "area_reparto_principal": area_ga_original,
            "reparto_principal_cabe": area_ga_original <= area_con(parametros["piso_base"], areas),
        })

    resumen = {
        "replicas": REPLICAS, "semillas": [semillas[0], semillas[-1]],
        "limite_abandono": parametros["limite_abandono"],
        "nota": ("La simulación no depende del área; el área solo decide qué repartos caben. "
                 "Cada escenario corre el GA completo con su área y compara su reparto contra la base "
                 "con las mismas 100 semillas de la Fase 8."),
        "escenarios": salida,
    }
    with open(SALIDA / "sensibilidad_area.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=1)

    print(f"\n{'escenario':24} {'áreas BJ/R/D':>12} {'total':>6} {'reparto':>12} {'Δ ingreso':>22} {'abandono':>9}  84/5/1/2 cabe")
    for e in salida:
        a = e["area_por_unidad"]
        d = e["diferencia"]["ingreso"]
        print(f"{e['etiqueta']:24} {a['blackjack']:>4}/{a['ruleta']}/{a['dados']:<4} {e['area_total']:>6} "
              f"{clave(e['piso_elegido']):>12} {d['pct']:+6.1f}% [{d['pct_ic95'][0]:+.1f}, {d['pct_ic95'][1]:+.1f}] "
              f"{100 * e['mejorada']['prob_abandono']['media']:8.2f}%  {'sí' if e['reparto_principal_cabe'] else 'no'}")
    print(f"Archivo: {(SALIDA / 'sensibilidad_area.json').relative_to(esc.RAIZ)}  ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
