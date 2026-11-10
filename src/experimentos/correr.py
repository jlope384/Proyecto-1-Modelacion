"""Fase 8: experimentos del Proyecto 2 (base, mejorada y sensibilidad).

Uso (desde la raíz del repo):
    python src/experimentos/correr.py [--procesos 4] [--grupos principal llegadas paciencia calibracion]
    python src/experimentos/correr.py --resumir           # solo reconstruye las salidas desde replicas.jsonl

Necesita antes `src/calibracion/calibrar.py` (parámetros calibrados) y
`src/optimizacion/genetico.py` (piso mejorado).

Qué compara:
  base       piso de Nevada 2023 / 4 (100 máquinas, 4 blackjack, 1 ruleta, 1 dados)
  mejorada   reparto que encontró el GA con la misma área (resultado.json)

Las dos configuraciones corren con las mismas semillas y con
`flujos_por_cliente=True`, así que reciben los mismos clientes con la misma
suerte (números aleatorios comunes): la diferencia pareada es la que mide
la mejora, no la diferencia de medias.

Grupos de condiciones:
  principal    base contra mejorada, 100 réplicas (semillas 7001-7100)
  llegadas     factor de llegadas 0.8, 1.2 (+20%) y 1.4, 30 réplicas cada una
  paciencia    paciencia media 4 min (50%) y 12 min (150%), 30 réplicas cada una
  calibracion  calibración alternativa por juego (una escala por mesa), 100 réplicas

Las semillas (7001 en adelante) no se cruzan con las de calibración (1001-),
validación (2001-), llegadas (3001-), fitness del GA (5001-) ni re-evaluación (6001-).

Cada réplica se guarda en resultados/experimentos/replicas.jsonl y las que ya
existen no se repiten, así que se puede correr por grupos y retomar.

Salidas en resultados/experimentos/:
    replicas.jsonl       una línea por (condición, configuración, semilla), con todos los datos
    replicas.csv         las mismas réplicas en plano
    escenarios.json      resumen por condición, diferencias pareadas, sensibilidad y consistencia
    comparacion_real.json  tabla Real / Base / Mejorada con las métricas que tienen referencia real

Solo biblioteca estándar.
"""
import argparse
import csv
import json
import math
import statistics
import sys
import time
from multiprocessing import Pool
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modelo import escenario as esc  # noqa: E402

SALIDA = esc.RESULTADOS / "experimentos"
REPLICAS_JSONL = SALIDA / "replicas.jsonl"
RESULTADO_GA = esc.RESULTADOS / "optimizacion" / "resultado.json"

SEMILLA_INICIAL = 7001
REPLICAS_PRINCIPAL = 100
REPLICAS_SENSIBILIDAD = 30
REPLICAS_CALIBRACION = 100

FACTORES_LLEGADAS = (0.8, 1.2, 1.4)
PACIENCIAS_MIN = (4.0, 12.0)
PACIENCIA_BASE_MIN = 8.0  # PACIENCIA_MEDIA_MIN de backend/casino/piso.py

GRUPOS = ("principal", "llegadas", "paciencia", "calibracion")


# ---------------------------------------------------------------------------
# Definición de condiciones
# ---------------------------------------------------------------------------


def definir_condiciones(parametros):
    """Lista de condiciones; cada una se corre con las dos configuraciones del piso."""
    f0 = parametros["factor_llegadas"]
    cond = [{"id": "principal", "grupo": "principal", "variable": None, "valor": None,
             "etiqueta": "Condiciones calibradas", "replicas": REPLICAS_PRINCIPAL, "cambios": {}}]
    for m in FACTORES_LLEGADAS:
        cond.append({"id": f"llegadas_x{m}", "grupo": "llegadas", "variable": "factor de llegadas",
                     "valor": m, "etiqueta": f"Llegadas x{m} ({(m - 1) * 100:+.0f}%)",
                     "replicas": REPLICAS_SENSIBILIDAD,
                     "cambios": {"factor_llegadas": f0 * m}})
    for p in PACIENCIAS_MIN:
        cond.append({"id": f"paciencia_{p:g}", "grupo": "paciencia", "variable": "paciencia media (min)",
                     "valor": p, "etiqueta": f"Paciencia {p:g} min ({p / PACIENCIA_BASE_MIN * 100:.0f}%)",
                     "replicas": REPLICAS_SENSIBILIDAD,
                     "cambios": {"paciencia_media_min": p}})
    cond.append({"id": "calibracion_por_juego", "grupo": "calibracion",
                 "variable": "calibración de mesas", "valor": "una escala por juego",
                 "etiqueta": "Calibración alternativa por juego", "replicas": REPLICAS_CALIBRACION,
                 "cambios": {"escala_bankroll_mesas": parametros["alternativa_escala_por_juego"]}})
    return cond


def semillas(c):
    return [SEMILLA_INICIAL + i for i in range(c["replicas"])]


def layouts(parametros):
    with open(RESULTADO_GA, encoding="utf-8") as f:
        ga = json.load(f)
    return {"base": dict(parametros["piso_base"]), "mejorada": dict(ga["mejorada"]["conteos"])}


# ---------------------------------------------------------------------------
# Ejecución
# ---------------------------------------------------------------------------


def _simular(args):
    parametros, cond_id, layout, conteos, cambios, semilla = args
    r = esc.simular(parametros, conteos, semilla, **cambios)
    r["condicion"] = cond_id
    r["configuracion"] = layout
    return r


def leer_replicas():
    if not REPLICAS_JSONL.exists():
        return []
    with open(REPLICAS_JSONL, encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]


def correr_grupos(parametros, grupos, procesos):
    hechas = {(r["condicion"], r["configuracion"], r["semilla"]) for r in leer_replicas()}
    lay = layouts(parametros)
    trabajos = []
    for c in definir_condiciones(parametros):
        if c["grupo"] not in grupos:
            continue
        for nombre, conteos in lay.items():
            for s in semillas(c):
                if (c["id"], nombre, s) not in hechas:
                    trabajos.append((parametros, c["id"], nombre, conteos, c["cambios"], s))
    if not trabajos:
        print("Nada que correr: las réplicas de esos grupos ya existen.")
        return
    print(f"{len(trabajos)} simulaciones nuevas, {procesos} procesos")
    SALIDA.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with Pool(procesos) as pool, open(REPLICAS_JSONL, "a", encoding="utf-8") as f:
        for i, r in enumerate(pool.imap_unordered(_simular, trabajos, chunksize=2), 1):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            if i % 25 == 0 or i == len(trabajos):
                print(f"  {i}/{len(trabajos)}  {time.time() - t0:.0f} s")


# ---------------------------------------------------------------------------
# Estadística
# ---------------------------------------------------------------------------


def resumen(valores):
    n = len(valores)
    m = statistics.fmean(valores)
    de = statistics.stdev(valores) if n > 1 else 0.0
    h = 1.96 * de / math.sqrt(n) if n > 1 else 0.0
    return {"media": m, "desv": de, "ic95": [m - h, m + h], "n": n}


def metricas_de(filas):
    por_dia = lambda k: [f[k] for f in filas]  # noqa: E731
    out = {
        "ingreso_total": resumen(por_dia("ingreso_total")),
        "prob_abandono": resumen(por_dia("prob_abandono")),
        "espera_promedio_min": resumen(por_dia("espera_promedio_min")),
        "llegadas": resumen(por_dia("llegadas")),
        "atendidos": resumen(por_dia("atendidos")),
        "abandonos": resumen(por_dia("abandonos")),
    }
    for j in esc.JUEGOS:
        out[f"utilizacion_{j}"] = resumen([f["utilizacion"][j] for f in filas])
        out[f"ingreso_{j}"] = resumen([f["ingreso_por_juego"][j] for f in filas])
    return out


def diferencia_pareada(filas_mej, filas_base):
    """mejorada - base con las mismas semillas. Devuelve media, desviación e IC95."""
    base = {f["semilla"]: f for f in filas_base}
    pares = [(f, base[f["semilla"]]) for f in filas_mej if f["semilla"] in base]
    d_ing = resumen([m["ingreso_total"] - b["ingreso_total"] for m, b in pares])
    d_ab = resumen([100 * (m["prob_abandono"] - b["prob_abandono"]) for m, b in pares])
    d_es = resumen([m["espera_promedio_min"] - b["espera_promedio_min"] for m, b in pares])
    ing_base = statistics.fmean(b["ingreso_total"] for _, b in pares)
    d_ing["pct"] = 100 * d_ing["media"] / ing_base
    d_ing["pct_ic95"] = [100 * d_ing["ic95"][0] / ing_base, 100 * d_ing["ic95"][1] / ing_base]
    return {"replicas": len(pares), "ingreso": d_ing, "abandono_pp": d_ab, "espera_min": d_es}


# ---------------------------------------------------------------------------
# Resumen y salidas
# ---------------------------------------------------------------------------


def agregados_juego(filas, conteos):
    """Mezcla del piso, win por unidad relativo a máquina y hold de tragamonedas (como calibrar.py)."""
    ing = {j: sum(f["ingreso_por_juego"][j] for f in filas) for j in esc.JUEGOS}
    apo = {j: sum(f["apostado_por_juego"][j] for f in filas) for j in esc.JUEGOS}
    wpu = {j: ing[j] / conteos[j] for j in esc.JUEGOS}
    return {
        "relativo_a_maquina": {j: wpu[j] / wpu["tragamonedas"] for j in esc.MESAS},
        "hold_tragamonedas_pct": 100.0 * ing["tragamonedas"] / apo["tragamonedas"],
    }


def mezcla_implicita(relativo, unidades_estatales):
    rel = dict(relativo, tragamonedas=1.0)
    win = {j: rel[j] * unidades_estatales[j] for j in esc.JUEGOS}
    total = sum(win.values())
    return {j: win[j] / total for j in esc.JUEGOS}


def fila_real(metrica, unidad, juego, real, base, mejorada, fuente, etiqueta="publico", nota=""):
    f = {"metrica": metrica, "juego_o_dia": juego, "unidad": unidad, "real": real,
         "base": base, "mejorada": mejorada, "etiqueta": etiqueta, "fuente": fuente, "nota": nota}
    if real is not None:
        f["error_abs_base"] = base - real
        f["error_rel_base_pct"] = 100 * (base - real) / real if real else None
    f["cambio_abs"] = mejorada - base
    f["cambio_pct"] = 100 * (mejorada - base) / base if base else None
    return f


def tabla_real(filas_base, filas_mej, lay, parametros):
    """
    Tabla Real / Base / Mejorada para las métricas con referencia real
    (validación 2024) y las salidas sin referencia, etiquetadas como estimadas.
    """
    val = esc.leer_nevada("validacion")
    dias_val = esc.leer_gkl_dia_semana(esc.ANIO_VALIDACION)
    nivel_val = esc.leer_gkl_nivel(esc.ANIO_VALIDACION)
    ag_b = agregados_juego(filas_base, lay["base"])
    ag_m = agregados_juego(filas_mej, lay["mejorada"])
    mez_b = mezcla_implicita(ag_b["relativo_a_maquina"], val["unidades_estatales"])
    mez_m = mezcla_implicita(ag_m["relativo_a_maquina"], val["unidades_estatales"])
    nev = "Nevada GCB, informes mensuales 2024"
    gkl = "Grand Korea Leisure, visitantes diarios 2024"
    filas = []
    for j in esc.JUEGOS:
        filas.append(fila_real("Participación en el win de los 4 juegos (implícita)", "%", j,
                               100 * val["mezcla_ingreso_4juegos"][j], 100 * mez_b[j], 100 * mez_m[j], nev,
                               nota="Win por unidad simulado por las unidades estatales de Nevada"))
    wpu_maq = val["win_por_unidad_mes_miles"]["tragamonedas"]
    for j in esc.MESAS:
        filas.append(fila_real("Win por mesa / win por máquina", "veces", j,
                               val["win_por_unidad_mes_miles"][j] / wpu_maq,
                               ag_b["relativo_a_maquina"][j], ag_m["relativo_a_maquina"][j], nev))
    filas.append(fila_real("Hold de tragamonedas (win / jugado)", "%", "tragamonedas",
                           val["win_pct"]["tragamonedas"], ag_b["hold_tragamonedas_pct"],
                           ag_m["hold_tragamonedas_pct"], nev))
    # Llegadas: la configuración del piso no las cambia, base y mejorada comparten la misma serie.
    llegadas_media = statistics.fmean(f["llegadas"] for f in filas_base)
    filas.append(fila_real("Sesiones por día y sucursal (promedio)", "sesiones / día", "todas",
                           nivel_val * parametros["sesiones_por_visitante"], llegadas_media,
                           statistics.fmean(f["llegadas"] for f in filas_mej), gkl, etiqueta="real",
                           nota="El modelo se calibró con 2023; 2024 tuvo más visitantes"))
    # Salidas sin referencia real
    for nombre, k, unidad, esc_ in (("Probabilidad de abandono", "prob_abandono", "%", 100.0),
                                    ("Espera promedio", "espera_promedio_min", "min", 1.0),
                                    ("Ingreso diario del casino", "ingreso_total", "u.m.", 1.0)):
        b = statistics.fmean(f[k] for f in filas_base) * esc_
        m = statistics.fmean(f[k] for f in filas_mej) * esc_
        filas.append(fila_real(nombre, unidad, "piso", None, b, m, "Salida del modelo",
                               etiqueta="estimado", nota="Sin referencia real: supuesto del modelo"))
    # MAE solo de las filas con referencia real y rol de validación (sin la de llegadas por nivel)
    reales = [f for f in filas if f["real"] is not None and f["metrica"] != "Sesiones por día y sucursal (promedio)"]
    mae = {}
    for g in sorted({f["metrica"] for f in reales}):
        xs = [f for f in reales if f["metrica"] == g]
        mae[g] = {"mae_base": statistics.fmean(abs(f["error_abs_base"]) for f in xs),
                  "error_rel_medio_base_pct": statistics.fmean(abs(f["error_rel_base_pct"]) for f in xs),
                  "mae_mejorada": statistics.fmean(abs(f["mejorada"] - f["real"]) for f in xs),
                  "unidad": xs[0]["unidad"], "n": len(xs)}
    return {"periodo_validacion": esc.ANIO_VALIDACION, "filas": filas, "mae": mae,
            "nota": ("La referencia real no cambia entre base y mejorada: la mejora es una predicción "
                     "simulada, no algo observado en un casino.")}


def ruta_relativa(p):
    return str(Path(p).relative_to(esc.RAIZ))


def resumir_todo(parametros):
    filas = leer_replicas()
    if not filas:
        raise SystemExit("No hay réplicas: corre primero los grupos.")
    lay = layouts(parametros)
    conds = definir_condiciones(parametros)
    por = {}
    for r in filas:
        por.setdefault((r["condicion"], r["configuracion"]), []).append(r)
    for k in por:
        por[k].sort(key=lambda r: r["semilla"])

    condiciones, pares = [], []
    for c in conds:
        if (c["id"], "base") not in por or (c["id"], "mejorada") not in por:
            continue
        completo = all(len(por[(c["id"], n)]) == c["replicas"] for n in ("base", "mejorada"))
        for nombre in ("base", "mejorada"):
            fs = por[(c["id"], nombre)]
            condiciones.append({
                "id": f"{c['id']}:{nombre}", "condicion": c["id"], "grupo": c["grupo"],
                "configuracion": nombre, "conteos": lay[nombre], "area": esc.area(lay[nombre]),
                "variable": c["variable"], "valor": c["valor"], "etiqueta": c["etiqueta"],
                "replicas": len(fs), "completo": completo,
                "semillas": [fs[0]["semilla"], fs[-1]["semilla"]],
                "metricas": metricas_de(fs),
            })
        d = diferencia_pareada(por[(c["id"], "mejorada")], por[(c["id"], "base")])
        d.update({"condicion": c["id"], "grupo": c["grupo"], "variable": c["variable"],
                  "valor": c["valor"], "etiqueta": c["etiqueta"],
                  "abandono_base": statistics.fmean(f["prob_abandono"] for f in por[(c["id"], "base")]),
                  "abandono_mejorada": statistics.fmean(f["prob_abandono"] for f in por[(c["id"], "mejorada")])})
        d["mejora_significativa"] = d["ingreso"]["ic95"][0] > 0
        d["mejorada_dentro_del_limite"] = d["abandono_mejorada"] <= parametros["limite_abandono"]
        d["base_dentro_del_limite"] = d["abandono_base"] <= parametros["limite_abandono"]
        pares.append(d)

    # Series de sensibilidad: el punto central (1.0 y 8 min) sale de la condición principal.
    def punto(cid, nombre):
        return metricas_de(por[(cid, nombre)])

    def serie(grupo, central_valor):
        cs = [c for c in conds if c["grupo"] == grupo and (c["id"], "base") in por]
        puntos = [{"valor": central_valor, "condicion": "principal"}] + \
                 [{"valor": c["valor"], "condicion": c["id"]} for c in cs]
        puntos.sort(key=lambda p: p["valor"])
        out = []
        for p in puntos:
            out.append({"valor": p["valor"], "condicion": p["condicion"],
                        "base": punto(p["condicion"], "base"), "mejorada": punto(p["condicion"], "mejorada")})
        return out

    sensibilidad = {}
    if any(c["grupo"] == "llegadas" and (c["id"], "base") in por for c in conds):
        sensibilidad["llegadas"] = {"variable": "factor de llegadas", "unidad": "x respecto a 2023",
                                    "serie": serie("llegadas", 1.0)}
    if any(c["grupo"] == "paciencia" and (c["id"], "base") in por for c in conds):
        sensibilidad["paciencia"] = {"variable": "paciencia media", "unidad": "min",
                                     "serie": serie("paciencia", PACIENCIA_BASE_MIN)}

    # Consistencia interna sobre todas las réplicas
    conserv = all(r["atendidos"] + r["abandonos"] == r["llegadas"] for r in filas)
    little = max(abs(r["little_L_obs"] - r["little_L_est"]) / r["little_L_obs"] for r in filas)
    consistencia = {"replicas_totales": len(filas), "conservacion_clientes": conserv,
                    "little_error_rel_max": little, "little_tolerancia": 0.05,
                    "little_ok": little < 0.05}

    principal_b, principal_m = por[("principal", "base")], por[("principal", "mejorada")]
    meta = {
        "limite_abandono": parametros["limite_abandono"],
        "piso_base": lay["base"], "piso_mejorada": lay["mejorada"],
        "area_base": esc.area(lay["base"]), "area_mejorada": esc.area(lay["mejorada"]),
        "replicas_principal": REPLICAS_PRINCIPAL, "replicas_sensibilidad": REPLICAS_SENSIBILIDAD,
        "replicas_calibracion_alternativa": REPLICAS_CALIBRACION,
        "semilla_inicial": SEMILLA_INICIAL,
        "unidad_ingreso": "u.m. (unidades monetarias del modelo; no son USD)",
        "fuente_ga": ruta_relativa(RESULTADO_GA),
        "nota": ("La mejora es una predicción de la simulación, no una mejora observada. "
                 "Espera y abandono no tienen referencia real."),
    }
    escenarios = {"meta": meta, "condiciones": condiciones, "pares": pares,
                  "sensibilidad": sensibilidad, "consistencia": consistencia}
    comparacion = tabla_real(principal_b, principal_m, lay, parametros)

    SALIDA.mkdir(parents=True, exist_ok=True)
    with open(SALIDA / "escenarios.json", "w", encoding="utf-8") as f:
        json.dump(escenarios, f, ensure_ascii=False, indent=1)
    with open(SALIDA / "comparacion_real.json", "w", encoding="utf-8") as f:
        json.dump(comparacion, f, ensure_ascii=False, indent=1)
    with open(SALIDA / "replicas.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["condicion", "configuracion", "semilla", "llegadas", "atendidos", "abandonos",
                    "prob_abandono", "espera_promedio_min", "ingreso_total"]
                   + [f"ingreso_{j}" for j in esc.JUEGOS] + [f"utilizacion_{j}" for j in esc.JUEGOS])
        for r in sorted(filas, key=lambda r: (r["condicion"], r["configuracion"], r["semilla"])):
            w.writerow([r["condicion"], r["configuracion"], r["semilla"], r["llegadas"], r["atendidos"],
                        r["abandonos"], r["prob_abandono"], r["espera_promedio_min"], r["ingreso_total"]]
                       + [r["ingreso_por_juego"][j] for j in esc.JUEGOS]
                       + [r["utilizacion"][j] for j in esc.JUEGOS])
    return escenarios, comparacion


def imprimir(escenarios):
    print(f"\nRéplicas totales: {escenarios['consistencia']['replicas_totales']}")
    print(f"{'condición':26} {'n':>4} {'Δ ingreso (mejorada - base)':>30} {'abandono base → mej.':>24} {'límite':>8}")
    for p in escenarios["pares"]:
        d = p["ingreso"]
        ok = "ok" if p["mejorada_dentro_del_limite"] else "excede"
        print(f"{p['etiqueta']:26} {p['replicas']:4d} {d['media']:+12,.0f} ({d['pct']:+.1f}%) "
              f"[{d['pct_ic95'][0]:+.1f}, {d['pct_ic95'][1]:+.1f}]%  "
              f"{100 * p['abandono_base']:5.2f}% → {100 * p['abandono_mejorada']:5.2f}%  {ok:>8}")
    c = escenarios["consistencia"]
    print(f"\nConsistencia: conservación {'OK' if c['conservacion_clientes'] else 'FALLA'}, "
          f"Little error rel máx {c['little_error_rel_max']:.4f}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--grupos", nargs="+", choices=GRUPOS, default=list(GRUPOS))
    ap.add_argument("--resumir", action="store_true", help="solo reconstruir salidas desde replicas.jsonl")
    args = ap.parse_args()
    parametros = esc.cargar_parametros()
    if not args.resumir:
        correr_grupos(parametros, set(args.grupos), args.procesos)
    escenarios, _ = resumir_todo(parametros)
    imprimir(escenarios)
    assert escenarios["consistencia"]["conservacion_clientes"], "atendidos + abandonos != llegadas"
    assert escenarios["consistencia"]["little_ok"], "la ley de Little no cuadra"
    print(f"Archivos en {ruta_relativa(SALIDA)}/")


if __name__ == "__main__":
    main()
