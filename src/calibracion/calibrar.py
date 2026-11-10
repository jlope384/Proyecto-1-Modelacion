"""Fase 6: calibración del piso con datos de 2023 y validación con 2024.

Uso (desde la raíz del repo):
    python src/calibracion/calibrar.py [--replicas 30] [--procesos 8]

Qué se fija con datos, qué se calibra y qué se valida:

  Entrada directa de datos (no se ajusta):
    - Nivel de llegadas: visitantes promedio por día y sucursal de Grand Korea
      Leisure 2023, por SESIONES_POR_VISITANTE (supuesto).
    - Composición del piso base: unidades por local de Nevada 2023 / 4.
    - Demanda por juego: proporcional a los puestos del piso base (supuesto).
    - Factores por día de la semana: GKL 2023.

  Único parámetro calibrado, con un solo indicador:
    - escala_bankroll_mesas <- participación de tragamonedas en el win de los
      cuatro juegos, Nevada 2023 (82.0%), medida como MEZCLA IMPLÍCITA: el
      win por unidad simulado de cada juego multiplicado por las unidades
      estatales de Nevada. Así se compara con la misma composición con la
      que Nevada calcula su mezcla (el piso base tiene más mesas por máquina
      que el estado, ver escenario.ESCALA_PISO). Con números aleatorios
      comunes el ingreso de las mesas es proporcional a la escala (la
      congestión no cambia), así que se resuelve casi en forma cerrada y se
      refina con unas pocas iteraciones.

  Validación (semillas distintas a las de calibración, datos que no se usaron
  para ajustar):
    - Win por unidad de cada mesa relativo a una máquina (2023 y 2024). No
      depende del tamaño ni de la composición del piso.
    - Mezcla implícita de blackjack, ruleta y dados (2023 y 2024) y de
      tragamonedas (2024).
    - Hold de tragamonedas contra el win percent de Nevada (2023 y 2024).
    - Factores por día de la semana y nivel de llegadas de 2024.

Salidas en resultados/calibracion/:
    parametros.json           parámetros que usan el GA y los experimentos
    validacion.csv            real contra simulado, error absoluto y relativo
    llegadas_dia_semana.csv   llegadas simuladas contra reales por día
    replicas_calibracion.csv  una fila por semilla de la corrida de validación
    resumen.json              MAE por grupo de métricas y salidas estimadas

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
from casino import llegadas, rng  # noqa: E402

SALIDA = esc.RESULTADOS / "calibracion"
SEMILLAS_CALIBRACION = 1001   # 1001, 1002, ...
SEMILLAS_VALIDACION = 2001    # 2001, 2002, ...  (independientes de las de calibración)
SEMILLAS_LLEGADAS = 3001
TOLERANCIA_MEZCLA = 1e-4
MAX_ITERACIONES = 6


def _simular(args):
    parametros, conteos, semilla = args
    return esc.simular(parametros, conteos, semilla)


def correr(parametros, conteos, semillas, procesos):
    with Pool(procesos) as pool:
        return pool.map(_simular, [(parametros, conteos, s) for s in semillas])


def ic95(valores):
    n = len(valores)
    m = statistics.fmean(valores)
    if n < 2:
        return m, 0.0, m, m
    de = statistics.stdev(valores)
    h = 1.96 * de / math.sqrt(n)
    return m, de, m - h, m + h


def mezcla_implicita(relativo, unidades_estatales):
    """
    Mezcla de ingreso que tendría el estado si cada unidad ganara lo que gana
    en el simulador: win_j = (win por unidad relativo a máquina)_j * unidades_j.
    """
    rel = dict(relativo, tragamonedas=1.0)
    win = {j: rel[j] * unidades_estatales[j] for j in esc.JUEGOS}
    total = sum(win.values())
    return {j: win[j] / total for j in esc.JUEGOS}


def agregados(corridas, conteos):
    """Totales sobre las réplicas (cocientes de sumas, como en nevada_referencia.py)."""
    ing = {j: sum(c["ingreso_por_juego"][j] for c in corridas) for j in esc.JUEGOS}
    apo = {j: sum(c["apostado_por_juego"][j] for c in corridas) for j in esc.JUEGOS}
    total = sum(ing.values())
    wpu = {j: ing[j] / conteos[j] for j in esc.JUEGOS}  # win por unidad (total de réplicas)
    return {
        "mezcla_piso": {j: ing[j] / total for j in esc.JUEGOS},
        "relativo_a_maquina": {j: wpu[j] / wpu["tragamonedas"] for j in esc.MESAS},
        "hold_tragamonedas_pct": 100.0 * ing["tragamonedas"] / apo["tragamonedas"],
    }


def calibrar_escala(parametros, conteos, objetivo, unidades, semillas, procesos):
    """
    Busca escala_bankroll_mesas tal que la mezcla implícita de tragamonedas
    sea `objetivo`. Con escala k el win de mesas es ~k * M1, así que
    share = S / (S + k * M1) -> k = S (1 - s) / (s M1), con S y M en win
    implícito (relativo a máquina por unidades estatales). Se itera porque la
    apuesta mínima de 1 y la quiebra con saldo < 1 hacen que la relación no
    sea exactamente lineal.
    """
    historial = []
    k = parametros["escala_bankroll_mesas"]
    for it in range(MAX_ITERACIONES):
        p = dict(parametros, escala_bankroll_mesas=k)
        ag = agregados(correr(p, conteos, semillas, procesos), conteos)
        S = unidades["tragamonedas"]
        M = sum(ag["relativo_a_maquina"][j] * unidades[j] for j in esc.MESAS)
        share = S / (S + M)
        historial.append({"iteracion": it, "escala": k, "mezcla_implicita_tragamonedas": share,
                          "mezcla_piso_tragamonedas": ag["mezcla_piso"]["tragamonedas"]})
        print(f"  iteración {it}: escala={k:.4f} mezcla implícita tragamonedas={share:.4%}")
        if abs(share - objetivo) < TOLERANCIA_MEZCLA:
            return k, historial
        if M <= 0:
            raise RuntimeError("el ingreso de mesas no es positivo; no se puede calibrar")
        k = k * (S * (1 - objetivo) / (objetivo * M))
    raise RuntimeError(f"la calibración no convergió en {MAX_ITERACIONES} iteraciones")


def fila(grupo, metrica, juego, periodo, real, simulado, rol, unidad):
    err = simulado - real
    return {"grupo": grupo, "metrica": metrica, "juego_o_dia": juego, "periodo_real": periodo,
            "rol": rol, "real": real, "simulado": simulado, "error_abs": err,
            "error_rel_pct": 100.0 * err / real if real else None, "unidad": unidad}


def llegadas_por_dia(parametros, nivel, factores, replicas):
    """
    Llegadas simuladas para cada día de la semana con los factores de 2023.
    Usa llegadas.generar (lo mismo que llama simular_dia al empezar), así que
    no hace falta correr el piso completo.
    """
    out = {}
    for i, dia in enumerate(esc.DIAS):
        f = esc.factor_llegadas(nivel, parametros["sesiones_por_visitante"], factores[dia]["factor"])
        conteos = []
        for r in range(replicas):
            gen = rng.Generador(metodo="inversa", semilla=SEMILLAS_LLEGADAS + 100 * i + r)
            t, _ = llegadas.generar(24, "inversa", generador=gen, factor=f)
            conteos.append(len(t))
        out[dia] = conteos
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--replicas", type=int, default=100)
    ap.add_argument("--procesos", type=int, default=8)
    args = ap.parse_args()
    if args.replicas < 30:
        print("AVISO: el documento de entrega pide al menos 30 réplicas por condición")

    t0 = time.time()
    SALIDA.mkdir(parents=True, exist_ok=True)
    cal, val = esc.leer_nevada("calibracion"), esc.leer_nevada("validacion")
    nivel_cal = esc.leer_gkl_nivel(esc.ANIO_CALIBRACION)
    nivel_val = esc.leer_gkl_nivel(esc.ANIO_VALIDACION)
    dias_cal = esc.leer_gkl_dia_semana(esc.ANIO_CALIBRACION)
    dias_val = esc.leer_gkl_dia_semana(esc.ANIO_VALIDACION)

    conteos = esc.piso_base()
    parametros = {
        "piso_base": conteos,
        "area_base": esc.area(conteos),
        "area_por_unidad": esc.AREA,
        "puestos_por_unidad": esc.PUESTOS,
        "pesos_demanda": esc.pesos_demanda(),
        "nivel_visitantes_dia": nivel_cal,
        "sesiones_por_visitante": esc.SESIONES_POR_VISITANTE,
        "factor_llegadas": esc.factor_llegadas(nivel_cal),
        "factores_dia_semana": {d: dias_cal[d]["factor"] for d in esc.DIAS},
        "escala_bankroll_mesas": 1.0,
        "limite_abandono": esc.LIMITE_ABANDONO,
    }
    print(f"Piso base (Nevada 2023 / {esc.ESCALA_PISO}): {conteos}, área {parametros['area_base']}")
    print(f"Llegadas: {nivel_cal:.1f} visitantes/día x {esc.SESIONES_POR_VISITANTE} sesiones "
          f"= {nivel_cal * esc.SESIONES_POR_VISITANTE:.0f} sesiones/día "
          f"(factor_llegadas {parametros['factor_llegadas']:.4f})")

    # -- 1. calibración de la escala de mesas -----------------------------
    objetivo = cal["mezcla_ingreso_4juegos"]["tragamonedas"]
    print(f"Calibrando escala_bankroll_mesas contra mezcla de tragamonedas 2023 = {objetivo:.4%}")
    sem_cal = [SEMILLAS_CALIBRACION + i for i in range(args.replicas)]
    k, hist = calibrar_escala(parametros, conteos, objetivo, cal["unidades_estatales"],
                              sem_cal, args.procesos)
    parametros["escala_bankroll_mesas"] = k

    # -- 2. validación con semillas nuevas --------------------------------
    sem_val = [SEMILLAS_VALIDACION + i for i in range(args.replicas)]
    corr = correr(parametros, conteos, sem_val, args.procesos)
    ag = agregados(corr, conteos)

    filas = []
    for periodo, ref, anio in (("calibracion", cal, 2023), ("validacion", val, 2024)):
        mez = mezcla_implicita(ag["relativo_a_maquina"], ref["unidades_estatales"])
        for j in esc.JUEGOS:
            rol = "calibrado" if (periodo == "calibracion" and j == "tragamonedas") else "validacion"
            filas.append(fila("mezcla_ingreso", "participación en el win de los 4 juegos (implícita)",
                              j, anio, 100 * ref["mezcla_ingreso_4juegos"][j], 100 * mez[j], rol, "%"))
        wpu_maq = ref["win_por_unidad_mes_miles"]["tragamonedas"]
        for j in esc.MESAS:
            filas.append(fila("win_por_unidad", "win por mesa / win por máquina", j, anio,
                              ref["win_por_unidad_mes_miles"][j] / wpu_maq,
                              ag["relativo_a_maquina"][j], "validacion", "veces"))
        filas.append(fila("hold", "hold de tragamonedas (win / jugado)", "tragamonedas", anio,
                          ref["win_pct"]["tragamonedas"], ag["hold_tragamonedas_pct"],
                          "validacion", "%"))

    # -- 2b. alternativa: una escala por mesa -----------------------------
    # Como el win de cada mesa es proporcional a su escala, la escala que
    # reproduce el win por unidad relativo de Nevada 2023 en cada juego sale
    # en forma cerrada. Son 3 parámetros para 3 indicadores (ajuste exacto,
    # sin validación propia salvo 2024); no es la calibración principal, sirve
    # para probar si el reparto del GA depende de este supuesto.
    escala_por_juego = {j: k * cal["win_por_unidad_mes_miles"][j]
                        / cal["win_por_unidad_mes_miles"]["tragamonedas"]
                        / ag["relativo_a_maquina"][j] for j in esc.MESAS}
    parametros["alternativa_escala_por_juego"] = escala_por_juego
    print("Alternativa (una escala por mesa, ajuste exacto a 2023): "
          + ", ".join(f"{j}={v:.2f}" for j, v in escala_por_juego.items()))

    # -- 3. llegadas por día de la semana ---------------------------------
    sim_dias = llegadas_por_dia(parametros, nivel_cal, dias_cal, args.replicas)
    media_sim = {d: statistics.fmean(v) for d, v in sim_dias.items()}
    prom_semana = statistics.fmean(media_sim.values())
    filas_dias = []
    for d in esc.DIAS:
        m, de, lo, hi = ic95(sim_dias[d])
        factor_sim = media_sim[d] / prom_semana
        filas_dias.append({
            "dia": d,
            "factor_real_2023": dias_cal[d]["factor"], "factor_real_2024": dias_val[d]["factor"],
            "factor_simulado": factor_sim,
            "visitantes_real_2023": dias_cal[d]["visitantes"] / 3,
            "visitantes_real_2024": dias_val[d]["visitantes"] / 3,
            "sesiones_real_2024": dias_val[d]["visitantes"] / 3 * esc.SESIONES_POR_VISITANTE,
            "sesiones_sim_media": m, "sesiones_sim_desv": de, "sesiones_sim_ic95_inf": lo,
            "sesiones_sim_ic95_sup": hi,
        })
        filas.append(fila("llegadas_dia", "factor del día (día / promedio semanal)", d, 2024,
                          dias_val[d]["factor"], factor_sim, "validacion", "veces"))
    sesiones_sim = statistics.fmean(c["llegadas"] for c in corr)
    filas.append(fila("llegadas_nivel", "sesiones por día y sucursal", "todas", 2024,
                      nivel_val * esc.SESIONES_POR_VISITANTE, sesiones_sim, "validacion",
                      "sesiones / día"))

    # -- 4. MAE por grupo (solo filas de validación) ----------------------
    mae = {}
    for g in ("mezcla_ingreso", "win_por_unidad", "hold", "llegadas_dia", "llegadas_nivel"):
        for anio in (2023, 2024):
            errs = [abs(f["error_abs"]) for f in filas
                    if f["grupo"] == g and f["periodo_real"] == anio and f["rol"] == "validacion"]
            rels = [abs(f["error_rel_pct"]) for f in filas
                    if f["grupo"] == g and f["periodo_real"] == anio and f["rol"] == "validacion"]
            if errs:
                mae[f"{g}_{anio}"] = {"mae": statistics.fmean(errs),
                                      "error_rel_medio_pct": statistics.fmean(rels), "n": len(errs),
                                      "unidad": next(f["unidad"] for f in filas if f["grupo"] == g)}

    # -- 5. salidas estimadas (sin referencia real) y consistencia --------
    estimadas = {}
    for nombre, fn in (("prob_abandono", lambda c: c["prob_abandono"]),
                       ("espera_promedio_min", lambda c: c["espera_promedio_min"]),
                       ("ingreso_total", lambda c: c["ingreso_total"])):
        m, de, lo, hi = ic95([fn(c) for c in corr])
        estimadas[nombre] = {"media": m, "desv": de, "ic95": [lo, hi]}
    for j in esc.JUEGOS:
        m, de, lo, hi = ic95([c["utilizacion"][j] for c in corr])
        estimadas[f"utilizacion_{j}"] = {"media": m, "desv": de, "ic95": [lo, hi]}
    conservacion = all(c["atendidos"] + c["abandonos"] == c["llegadas"] for c in corr)
    little = max(abs(c["little_L_obs"] - c["little_L_est"]) / c["little_L_obs"] for c in corr)

    # -- 6. escribir ------------------------------------------------------
    parametros["calibracion"] = {
        "parametro": "escala_bankroll_mesas",
        "indicador": "mezcla_ingreso_4juegos de tragamonedas, Nevada 2023",
        "objetivo": objetivo,
        "semillas": sem_cal,
        "iteraciones": hist,
    }
    parametros["procedencia"] = {
        "piso_base": "dato público de referencia (Nevada 2023, unidades por local / 4)",
        "pesos_demanda": "supuesto (demanda proporcional a los puestos del piso base)",
        "nivel_visitantes_dia": "dato real observado (GKL 2023, promedio por sucursal)",
        "sesiones_por_visitante": "supuesto",
        "factores_dia_semana": "dato real observado (GKL 2023)",
        "area_por_unidad": "estimación del equipo",
        "puestos_por_unidad": "supuesto (Proyecto 1)",
        "escala_bankroll_mesas": "calibrado contra Nevada 2023",
        "perfil_horario": "supuesto (llegadas.TASA_POR_HORA del Proyecto 1)",
    }
    with open(SALIDA / "parametros.json", "w", encoding="utf-8") as f:
        json.dump(parametros, f, ensure_ascii=False, indent=1)
    for nombre, datos in (("validacion.csv", filas), ("llegadas_dia_semana.csv", filas_dias)):
        with open(SALIDA / nombre, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(datos[0].keys()), lineterminator="\n")
            w.writeheader()
            w.writerows(datos)
    with open(SALIDA / "replicas_calibracion.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["semilla", "llegadas", "atendidos", "abandonos", "prob_abandono",
                    "espera_promedio_min", "ingreso_total"]
                   + [f"ingreso_{j}" for j in esc.JUEGOS] + [f"utilizacion_{j}" for j in esc.JUEGOS])
        for c in corr:
            w.writerow([c["semilla"], c["llegadas"], c["atendidos"], c["abandonos"],
                        c["prob_abandono"], c["espera_promedio_min"], c["ingreso_total"]]
                       + [c["ingreso_por_juego"][j] for j in esc.JUEGOS]
                       + [c["utilizacion"][j] for j in esc.JUEGOS])
    resumen = {
        "replicas": args.replicas,
        "semillas_validacion": sem_val,
        "escala_bankroll_mesas": k,
        "mezcla_del_piso_simulado": ag["mezcla_piso"],
        "mae": mae,
        "salidas_estimadas_sin_referencia": estimadas,
        "consistencia": {"conservacion_clientes": conservacion,
                         "little_error_rel_max": little},
        "segundos": time.time() - t0,
    }
    with open(SALIDA / "resumen.json", "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=1)

    # -- 7. reporte en consola --------------------------------------------
    print(f"\nescala_bankroll_mesas = {k:.4f}")
    print(f"{'grupo':16} {'juego/día':13} {'año':>4} {'rol':10} {'real':>10} {'simulado':>10} {'err rel':>8}")
    for f_ in filas:
        er = f"{f_['error_rel_pct']:+.1f}%" if f_["error_rel_pct"] is not None else "-"
        print(f"{f_['grupo']:16} {f_['juego_o_dia']:13} {f_['periodo_real']:>4} {f_['rol']:10} "
              f"{f_['real']:10.3f} {f_['simulado']:10.3f} {er:>8}")
    print("\nMAE (solo filas de validación):")
    for g, v in mae.items():
        print(f"  {g:22} MAE={v['mae']:.3f} {v['unidad']}  error rel medio={v['error_rel_medio_pct']:.1f}%  n={v['n']}")
    print("\nSalidas estimadas (sin referencia real):")
    for g, v in estimadas.items():
        print(f"  {g:26} {v['media']:.4f} (desv {v['desv']:.4f}, IC95 {v['ic95'][0]:.4f}-{v['ic95'][1]:.4f})")
    assert conservacion, "atendidos + abandonos != llegadas en alguna réplica"
    assert little < 0.05, f"Little no cuadra: error relativo {little:.3f}"
    print(f"\nConsistencia: conservación OK, Little error rel máx {little:.4f}")
    print(f"Archivos en {SALIDA.relative_to(esc.RAIZ)}/  ({time.time() - t0:.0f} s)")


if __name__ == "__main__":
    main()
