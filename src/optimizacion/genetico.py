"""Fase 7: algoritmo genético con restricciones, escrito a mano.

Uso (desde la raíz del repo, después de src/calibracion/calibrar.py):
    python src/optimizacion/genetico.py --prueba        # corrida corta de humo
    python src/optimizacion/genetico.py                 # corrida completa
    python src/optimizacion/genetico.py --escala-por-juego --salida ga_escala_por_juego

Pregunta: con la misma área total del piso, ¿qué reparto de tragamonedas,
blackjack, ruleta y dados maximiza el ingreso diario sin que el abandono
pase de 10%?

Diseño
  Cromosoma   vector de enteros [tragamonedas, blackjack, ruleta, dados].
  Restricción área total igual a la del piso base (redistribución, no
              ampliación), con área por unidad de escenario.AREA. Como una
              máquina ocupa 1, las máquinas absorben exactamente el área
              que dejan las mesas: tragamonedas = A - sum(área_mesa * mesas).
              Además cada juego conserva al menos una unidad.
  Reparación  si las mesas no dejan espacio para el mínimo de máquinas, se
              quita una mesa al azar (con preferencia por la que más área
              ocupa) hasta que cabe; luego se recalculan las máquinas.
  Selección   torneo de tamaño k.
  Cruce       de un punto sobre los genes de mesas, con probabilidad pc.
  Mutación    sumar o restar 1 a cada gen de mesa con probabilidad pm.
  Elitismo    los mejores e pasan sin cambio.
  Fitness     ingreso diario promedio en R réplicas con las MISMAS semillas
              para todos los individuos (números aleatorios comunes, con
              flujos por cliente, ver piso.py) menos una penalización si el
              abandono promedio pasa del límite:
                  f = ingreso - lambda * ingreso_base * max(0, abandono - 0.10)
              con lambda = 10: cada punto porcentual de exceso cuesta 10% del
              ingreso base.
  Término     G generaciones o S generaciones seguidas sin mejora.
  Ruido       el fitness viene de una simulación. Para no quedarse con un
              individuo que solo tuvo suerte con esas semillas, al final se
              re-evalúan los mejores candidatos con semillas NUEVAS y se
              elige el mejor factible en esa re-evaluación.

Salidas en resultados/<salida>/ (por defecto resultados/optimizacion/):
    historial.csv       una fila por generación (convergencia)
    evaluaciones.csv    cada configuración evaluada y su fitness
    resultado.json      parámetros del GA, semillas, solución, comprobación
                        de restricciones y comparación base vs mejorada

Solo biblioteca estándar.
"""
import argparse
import csv
import json
import math
import random
import statistics
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modelo import escenario as esc  # noqa: E402

GENES = esc.JUEGOS          # orden del cromosoma
MESAS = esc.MESAS           # genes que muta el GA; tragamonedas se deriva

# Parámetros por defecto, con su justificación (ver docs-proyecto2/genetico.md)
POBLACION = 20              # pocas variables (3 libres): 20 cubre bien el espacio
GENERACIONES = 30
PROB_CRUCE = 0.9            # valor usual en GA de codificación entera
PROB_MUTACION = 0.3         # por gen; alta porque solo hay 3 genes libres
TORNEO = 3                  # presión de selección moderada
ELITE = 2
ESTANCAMIENTO = 8           # generaciones sin mejora para parar
REPLICAS_FITNESS = 10
REPLICAS_REEVALUACION = 30  # el documento pide >= 30 por condición
CANDIDATOS_REEVALUACION = 5
LAMBDA_PENALIZACION = 10.0
SEMILLA_GA = 7
SEMILLAS_FITNESS = 5001     # 5001..5000+R, comunes a todos los individuos
SEMILLAS_REEVALUACION = 6001


# ---------------------------------------------------------------------------
# Representación y restricciones
# ---------------------------------------------------------------------------


def a_tupla(conteos):
    return tuple(int(conteos[j]) for j in GENES)


def a_dict(cromosoma):
    return dict(zip(GENES, cromosoma))


def area(cromosoma):
    return esc.area(a_dict(cromosoma))


def factible(cromosoma, area_total, minimo=esc.MINIMO_UNIDADES):
    """Comprobación por código de las restricciones duras."""
    return (area(cromosoma) == area_total
            and all(isinstance(x, int) and x >= minimo for x in cromosoma))


def reparar(mesas, area_total, aleatorio, minimo=esc.MINIMO_UNIDADES):
    """
    Recibe {mesa: n} (puede violar límites) y devuelve un cromosoma factible:
    cada mesa >= minimo, y las máquinas llenan exactamente el área restante
    (>= minimo). Si no caben, quita mesas al azar, con probabilidad
    proporcional al área que ocupan, hasta que caben.
    """
    mesas = {j: max(minimo, int(mesas[j])) for j in MESAS}
    while True:
        libre = area_total - sum(esc.AREA[j] * mesas[j] for j in MESAS)
        if libre >= minimo * esc.AREA["tragamonedas"]:
            break
        candidatas = [j for j in MESAS if mesas[j] > minimo]
        if not candidatas:
            raise ValueError("el área no alcanza ni para el mínimo de cada juego")
        pesos = [esc.AREA[j] * mesas[j] for j in candidatas]
        mesas[aleatorio.choices(candidatas, weights=pesos)[0]] -= 1
    maquinas = libre // esc.AREA["tragamonedas"]
    return a_tupla(dict(mesas, tragamonedas=maquinas))


# ---------------------------------------------------------------------------
# Operadores
# ---------------------------------------------------------------------------


def torneo(poblacion, fitness, k, aleatorio):
    elegidos = aleatorio.sample(range(len(poblacion)), k)
    return poblacion[max(elegidos, key=lambda i: fitness[i])]


def cruce_un_punto(a, b, aleatorio):
    """Cruce de un punto sobre los genes de mesas (posiciones 1..3)."""
    ia, ib = list(a[1:]), list(b[1:])
    punto = aleatorio.randint(1, len(ia) - 1)
    return ia[:punto] + ib[punto:], ib[:punto] + ia[punto:]


def mutar(mesas_lista, pm, aleatorio):
    return [x + aleatorio.choice((-1, 1)) if aleatorio.random() < pm else x
            for x in mesas_lista]


def hijo(mesas_lista, area_total, aleatorio):
    return reparar(dict(zip(MESAS, mesas_lista)), area_total, aleatorio)


def poblacion_inicial(base, n, area_total, aleatorio):
    """El piso base más individuos al azar alrededor de él (0 a 3x sus mesas)."""
    pob = [base]
    vistos = {base}
    intentos = 0
    while len(pob) < n and intentos < 1000:
        intentos += 1
        mesas = {j: aleatorio.randint(esc.MINIMO_UNIDADES, 3 * base[GENES.index(j)] + 2)
                 for j in MESAS}
        c = reparar(mesas, area_total, aleatorio)
        if c not in vistos:
            vistos.add(c)
            pob.append(c)
    return pob


# ---------------------------------------------------------------------------
# Evaluación (simulación con números aleatorios comunes)
# ---------------------------------------------------------------------------


def _simular(args):
    parametros, cromosoma, semilla = args
    r = esc.simular(parametros, a_dict(cromosoma), semilla)
    return (cromosoma, semilla, r["ingreso_total"], r["prob_abandono"],
            r["espera_promedio_min"], r["utilizacion"])


def resumir(filas):
    ing = [f[2] for f in filas]
    ab = [f[3] for f in filas]
    n = len(filas)
    de = statistics.stdev(ing) if n > 1 else 0.0
    return {
        "ingreso_media": statistics.fmean(ing),
        "ingreso_desv": de,
        "ingreso_ic95": [statistics.fmean(ing) - 1.96 * de / math.sqrt(n),
                         statistics.fmean(ing) + 1.96 * de / math.sqrt(n)],
        "abandono_media": statistics.fmean(ab),
        "abandono_desv": statistics.stdev(ab) if n > 1 else 0.0,
        "espera_media_min": statistics.fmean(f[4] for f in filas),
        "utilizacion": {j: statistics.fmean(f[5][j] for f in filas) for j in GENES},
        "replicas": n,
    }


class Evaluador:
    """Evalúa cromosomas en paralelo y guarda en caché (mismas semillas -> mismo resultado)."""

    def __init__(self, parametros, semillas, pool, limite, lam):
        self.parametros = parametros
        self.semillas = semillas
        self.pool = pool
        self.limite = limite
        self.lam = lam
        self.ingreso_ref = None
        self.cache = {}
        self.simulaciones = 0

    def fitness(self, res):
        exceso = max(0.0, res["abandono_media"] - self.limite)
        return res["ingreso_media"] - self.lam * self.ingreso_ref * exceso

    def evaluar(self, cromosomas):
        nuevos = [c for c in dict.fromkeys(cromosomas) if c not in self.cache]
        if nuevos:
            trabajos = [(self.parametros, c, s) for c in nuevos for s in self.semillas]
            filas = self.pool.map(_simular, trabajos)
            self.simulaciones += len(trabajos)
            por_c = {}
            for f in filas:
                por_c.setdefault(f[0], []).append(f)
            for c, fs in por_c.items():
                self.cache[c] = resumir(fs)
        if self.ingreso_ref is None:
            raise RuntimeError("falta evaluar el piso base para fijar la penalización")
        return [self.fitness(self.cache[c]) for c in cromosomas]


# ---------------------------------------------------------------------------
# GA
# ---------------------------------------------------------------------------


def optimizar(evaluar, base, area_total, poblacion=POBLACION, generaciones=GENERACIONES,
              pc=PROB_CRUCE, pm=PROB_MUTACION, k_torneo=TORNEO, elite=ELITE,
              estancamiento=ESTANCAMIENTO, semilla=SEMILLA_GA, registro=None):
    """
    GA genérico: `evaluar(lista_de_cromosomas) -> lista de fitness`. Se separa
    de la simulación para poder probarlo con una función conocida.
    Devuelve (mejor_cromosoma, mejor_fitness, historial).
    """
    aleatorio = random.Random(semilla)
    pob = poblacion_inicial(base, poblacion, area_total, aleatorio)
    fit = evaluar(pob)
    mejor_c, mejor_f = max(zip(pob, fit), key=lambda x: x[1])
    historial = []
    sin_mejora = 0
    for g in range(generaciones + 1):
        historial.append({
            "generacion": g,
            "mejor_fitness_gen": max(fit),
            "media_fitness_gen": statistics.fmean(fit),
            "mejor_fitness_global": mejor_f,
            "mejor_cromosoma_global": mejor_c,
            "diversidad": len(set(pob)),
        })
        if registro:
            registro(historial[-1])
        if g == generaciones or sin_mejora >= estancamiento:
            break
        orden = sorted(range(len(pob)), key=lambda i: fit[i], reverse=True)
        nueva = [pob[i] for i in orden[:elite]]
        while len(nueva) < poblacion:
            p1 = torneo(pob, fit, k_torneo, aleatorio)
            p2 = torneo(pob, fit, k_torneo, aleatorio)
            if aleatorio.random() < pc:
                h1, h2 = cruce_un_punto(p1, p2, aleatorio)
            else:
                h1, h2 = list(p1[1:]), list(p2[1:])
            for h in (h1, h2):
                if len(nueva) < poblacion:
                    nueva.append(hijo(mutar(h, pm, aleatorio), area_total, aleatorio))
        pob = nueva
        fit = evaluar(pob)
        g_mejor_c, g_mejor_f = max(zip(pob, fit), key=lambda x: x[1])
        if g_mejor_f > mejor_f + 1e-9:
            mejor_c, mejor_f, sin_mejora = g_mejor_c, g_mejor_f, 0
        else:
            sin_mejora += 1
    return mejor_c, mejor_f, historial


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--prueba", action="store_true", help="corrida corta (población 6, 3 generaciones, 3 réplicas)")
    ap.add_argument("--poblacion", type=int, default=POBLACION)
    ap.add_argument("--generaciones", type=int, default=GENERACIONES)
    ap.add_argument("--replicas", type=int, default=REPLICAS_FITNESS)
    ap.add_argument("--replicas-reevaluacion", type=int, default=REPLICAS_REEVALUACION)
    ap.add_argument("--semilla", type=int, default=SEMILLA_GA)
    ap.add_argument("--procesos", type=int, default=8)
    ap.add_argument("--escala-por-juego", action="store_true",
                    help="usar la calibración alternativa (una escala por mesa)")
    ap.add_argument("--salida", default="optimizacion")
    args = ap.parse_args()
    if args.prueba:
        args.poblacion, args.generaciones, args.replicas = 6, 3, 3
        args.replicas_reevaluacion = 5
        if args.salida == "optimizacion":
            args.salida = "optimizacion_prueba"

    t0 = time.time()
    parametros = esc.cargar_parametros()
    if args.escala_por_juego:
        parametros["escala_bankroll_mesas"] = parametros["alternativa_escala_por_juego"]
    base = a_tupla(parametros["piso_base"])
    area_total = parametros["area_base"]
    limite = parametros["limite_abandono"]
    assert factible(base, area_total), "el piso base no cumple sus propias restricciones"

    salida = esc.RESULTADOS / args.salida
    salida.mkdir(parents=True, exist_ok=True)
    sem_fit = [SEMILLAS_FITNESS + i for i in range(args.replicas)]
    sem_re = [SEMILLAS_REEVALUACION + i for i in range(args.replicas_reevaluacion)]

    print(f"Piso base {a_dict(base)}  área {area_total}  límite abandono {limite:.0%}")
    print(f"GA: población {args.poblacion}, generaciones {args.generaciones}, réplicas {args.replicas}, "
          f"escala {'por juego' if args.escala_por_juego else 'única'}")

    with Pool(args.procesos) as pool:
        ev = Evaluador(parametros, sem_fit, pool, limite, LAMBDA_PENALIZACION)
        ev.ingreso_ref = 0.0
        ev.evaluar([base])
        ev.ingreso_ref = ev.cache[base]["ingreso_media"]

        def registro(h):
            c = h["mejor_cromosoma_global"]
            r = ev.cache[c]
            print(f"  gen {h['generacion']:2d}  mejor {a_dict(c)}  ingreso {r['ingreso_media']:,.0f}  "
                  f"abandono {r['abandono_media']:.2%}  media pob {h['media_fitness_gen']:,.0f}  "
                  f"distintos {h['diversidad']}  sims {ev.simulaciones}  {time.time() - t0:.0f}s")

        mejor, mejor_f, historial = optimizar(
            ev.evaluar, base, area_total, poblacion=args.poblacion,
            generaciones=args.generaciones, semilla=args.semilla, registro=registro)

        # -- re-evaluación de los mejores con semillas nuevas --------------
        ranking = sorted(ev.cache, key=lambda c: ev.fitness(ev.cache[c]), reverse=True)
        candidatos = list(dict.fromkeys([base] + ranking[:CANDIDATOS_REEVALUACION]))
        trabajos = [(parametros, c, s) for c in candidatos for s in sem_re]
        filas = pool.map(_simular, trabajos)
    re = {c: resumir([f for f in filas if f[0] == c]) for c in candidatos}

    factibles = [c for c in candidatos if re[c]["abandono_media"] <= limite]
    elegido = max(factibles, key=lambda c: re[c]["ingreso_media"]) if factibles else base
    # Diferencia pareada contra la base (mismas semillas -> CRN)
    ing_base = {f[1]: f[2] for f in filas if f[0] == base}
    difs = [f[2] - ing_base[f[1]] for f in filas if f[0] == elegido]
    d_media = statistics.fmean(difs)
    d_de = statistics.stdev(difs) if len(difs) > 1 else 0.0
    d_ic = [d_media - 1.96 * d_de / math.sqrt(len(difs)), d_media + 1.96 * d_de / math.sqrt(len(difs))]

    # -- comprobación por código de la restricción ------------------------
    assert factible(elegido, area_total), f"la solución viola la restricción: {elegido}"
    comprobacion = {
        "area_solucion": area(elegido), "area_base": area_total,
        "area_igual": area(elegido) == area_total,
        "minimo_por_juego": all(x >= esc.MINIMO_UNIDADES for x in elegido),
        "abandono_reevaluado_dentro_del_limite": re[elegido]["abandono_media"] <= limite,
        "todos_los_evaluados_factibles": all(factible(c, area_total) for c in ev.cache),
    }

    # -- escribir ---------------------------------------------------------
    with open(salida / "historial.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["generacion", "mejor_fitness_gen", "media_fitness_gen", "mejor_fitness_global",
                    "diversidad"] + [f"mejor_{j}" for j in GENES]
                   + ["mejor_ingreso", "mejor_abandono"])
        for h in historial:
            c = h["mejor_cromosoma_global"]
            w.writerow([h["generacion"], h["mejor_fitness_gen"], h["media_fitness_gen"],
                        h["mejor_fitness_global"], h["diversidad"], *c,
                        ev.cache[c]["ingreso_media"], ev.cache[c]["abandono_media"]])
    with open(salida / "evaluaciones.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(list(GENES) + ["area", "fitness", "ingreso_media", "ingreso_desv", "abandono_media",
                                  "espera_media_min"] + [f"utilizacion_{j}" for j in GENES])
        for c in ranking:
            r = ev.cache[c]
            w.writerow([*c, area(c), ev.fitness(r), r["ingreso_media"], r["ingreso_desv"],
                        r["abandono_media"], r["espera_media_min"]]
                       + [r["utilizacion"][j] for j in GENES])
    resultado = {
        "parametros_ga": {
            "poblacion": args.poblacion, "generaciones_max": args.generaciones,
            "generaciones_corridas": historial[-1]["generacion"],
            "prob_cruce": PROB_CRUCE, "prob_mutacion": PROB_MUTACION, "torneo": TORNEO,
            "elite": ELITE, "estancamiento": ESTANCAMIENTO, "lambda_penalizacion": LAMBDA_PENALIZACION,
            "semilla_ga": args.semilla, "replicas_fitness": args.replicas,
            "semillas_fitness": sem_fit, "replicas_reevaluacion": args.replicas_reevaluacion,
            "semillas_reevaluacion": sem_re,
            "escala_bankroll_mesas": parametros["escala_bankroll_mesas"],
        },
        "area_por_unidad": esc.AREA,
        "configuraciones_evaluadas": len(ev.cache),
        "simulaciones": ev.simulaciones + len(trabajos),
        "mejor_en_fitness": {"conteos": a_dict(mejor), "fitness": mejor_f, **ev.cache[mejor]},
        "reevaluacion": [{"conteos": a_dict(c), "fitness_ga": ev.fitness(ev.cache[c]), **re[c]}
                         for c in candidatos],
        "base": {"conteos": a_dict(base), **re[base]},
        "mejorada": {"conteos": a_dict(elegido), **re[elegido]},
        "diferencia_mejorada_menos_base": {
            "ingreso_media": d_media, "ingreso_desv": d_de, "ingreso_ic95": d_ic,
            "ingreso_pct": 100 * d_media / re[base]["ingreso_media"],
            "abandono_pp": 100 * (re[elegido]["abandono_media"] - re[base]["abandono_media"]),
        },
        "comprobacion_restricciones": comprobacion,
        "segundos": time.time() - t0,
    }
    with open(salida / "resultado.json", "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=1)

    print(f"\nRe-evaluación con {len(sem_re)} semillas nuevas:")
    for c in candidatos:
        r = re[c]
        marca = " <- elegido" if c == elegido else (" (base)" if c == base else "")
        print(f"  {a_dict(c)}  ingreso {r['ingreso_media']:,.0f} ± {r['ingreso_desv']:,.0f}  "
              f"abandono {r['abandono_media']:.2%}{marca}")
    print(f"Mejorada - base: {d_media:+,.0f} ({100 * d_media / re[base]['ingreso_media']:+.1f}%), "
          f"IC95 [{d_ic[0]:+,.0f}, {d_ic[1]:+,.0f}]")
    print(f"Restricciones: {comprobacion}")
    print(f"Archivos en {salida.relative_to(esc.RAIZ)}/  ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
