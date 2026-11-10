"""Fase 9: gráficas del Proyecto 2 para el informe.

Uso (desde la raíz del repo):
    python src/visualizacion/graficas.py

Solo lee archivos de resultados/ (no simula nada) y escribe PNG en
resultados/graficas/. Necesita matplotlib (requirements.txt de la raíz).

Gráficas:
    1_llegadas_dia_semana.png     llegadas simuladas contra reales por día (GKL 2023 y 2024)
    2_comparacion_real.png        mezcla implícita y win por unidad: Nevada 2024, base y mejorada
    3_convergencia_ga.png         mejor fitness y media de la población por generación
    4_base_vs_mejorada.png        ingreso, abandono y utilización con IC 95 %
    5_sensibilidad.png            ingreso y abandono ante llegadas y paciencia
    6_diferencias_pareadas.png    mejora de ingreso (mejorada - base) en cada condición, IC 95 %
    7_sensibilidad_area.png       reparto del GA, mejora y abandono con mesas 25 % más chicas o más grandes
"""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
RES = RAIZ / "resultados"
SALIDA = RES / "graficas"

COLOR = {"base": "#7b52d6", "mejorada": "#1f9fd6", "real": "#2b2b2b", "real2": "#9a9a9a",
         "limite": "#c0287f"}
JUEGOS = ("tragamonedas", "blackjack", "ruleta", "dados")
NOMBRE = {"tragamonedas": "Tragamonedas", "blackjack": "Blackjack", "ruleta": "Ruleta", "dados": "Dados"}
DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")
DIA_CORTO = {"lunes": "Lun", "martes": "Mar", "miercoles": "Mié", "jueves": "Jue", "viernes": "Vie",
             "sabado": "Sáb", "domingo": "Dom"}

plt.rcParams.update({"figure.dpi": 130, "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False,
                     "axes.spines.right": False, "font.size": 10})


def leer_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def leer_csv(p):
    with open(p, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def err(m):
    """yerr de matplotlib a partir de {'media', 'ic95'}."""
    return [[m["media"] - m["ic95"][0]], [m["ic95"][1] - m["media"]]]


def guardar(fig, nombre):
    SALIDA.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(SALIDA / nombre, bbox_inches="tight")
    plt.close(fig)
    print(f"  {nombre}")


def g1_llegadas():
    filas = {f["dia"]: f for f in leer_csv(RES / "calibracion" / "llegadas_dia_semana.csv")}
    x = range(len(DIAS))
    w = 0.27
    fig, ax = plt.subplots(figsize=(8, 4))
    for k, (col, etiqueta, color) in enumerate((
            ("factor_real_2023", "Real 2023 (calibración)", COLOR["real2"]),
            ("factor_real_2024", "Real 2024 (validación)", COLOR["real"]),
            ("factor_simulado", "Simulado (100 réplicas)", COLOR["base"]))):
        ax.bar([i + (k - 1) * w for i in x], [float(filas[d][col]) for d in DIAS], w,
               label=etiqueta, color=color)
    ax.axhline(1, color="#555", lw=0.8, ls=":")
    ax.set_xticks(list(x), [DIA_CORTO[d] for d in DIAS])
    ax.set_ylabel("Factor del día (llegadas / promedio semanal)")
    ax.set_xlabel("Día de la semana")
    ax.set_title("Llegadas por día de la semana: Grand Korea Leisure contra simulación")
    ax.set_ylim(0.6, 1.45)
    ax.legend(loc="upper left", fontsize=9)
    guardar(fig, "1_llegadas_dia_semana.png")


def g2_comparacion():
    c = leer_json(RES / "experimentos" / "comparacion_real.json")
    filas = c["filas"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.2))
    mez = [f for f in filas if f["metrica"].startswith("Participación")]
    wpu = [f for f in filas if f["metrica"].startswith("Win por mesa")]
    for ax, fs, ylab, titulo in ((a1, mez, "Participación en el win (%)", "Mezcla de ingreso implícita"),
                                 (a2, wpu, "Win por mesa / win por máquina (veces)",
                                  "Win por unidad relativo a una máquina")):
        x = range(len(fs))
        w = 0.27
        for k, (col, etiqueta, color) in enumerate((("real", f"Nevada {c['periodo_validacion']}", COLOR["real"]),
                                                    ("base", "Simulación base", COLOR["base"]),
                                                    ("mejorada", "Simulación mejorada", COLOR["mejorada"]))):
            ax.bar([i + (k - 1) * w for i in x], [f[col] for f in fs], w, label=etiqueta, color=color)
        ax.set_xticks(list(x), [NOMBRE[f["juego_o_dia"]] for f in fs])
        ax.set_ylabel(ylab)
        ax.set_xlabel("Juego")
        ax.set_title(titulo)
        ax.legend(fontsize=8)
    for ax_, fs in ((a1, mez), (a2, wpu)):
        for i, f in enumerate(fs):
            for k, col in enumerate(("real", "base", "mejorada")):
                ax_.text(i + (k - 1) * 0.27, f[col], f"{f[col]:.1f}", ha="center", va="bottom", fontsize=7)
    fig.suptitle("Comparación con la referencia real (validación 2024)", fontweight="bold")
    guardar(fig, "2_comparacion_real.png")


def g3_convergencia():
    h = leer_csv(RES / "optimizacion" / "historial.csv")
    g = [int(f["generacion"]) for f in h]
    mejor = [float(f["mejor_fitness_global"]) / 1e6 for f in h]
    media = [float(f["media_fitness_gen"]) / 1e6 for f in h]
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ax.plot(g, mejor, lw=2.5, color=COLOR["mejorada"], label="Mejor fitness acumulado")
    ax.plot(g, media, lw=2.5, color=COLOR["base"], label="Media de la población")
    piso = 0.4
    ax.set_ylim(piso, max(mejor) * 1.05)
    if media[0] < piso:
        ax.annotate(f"gen 0: media {media[0]:.2f} M (individuos\npenalizados por abandono > 10 %)",
                    xy=(0.1, piso), xytext=(2.3, piso + 0.03), fontsize=8,
                    arrowprops={"arrowstyle": "->", "color": "#555"})
    ax.set_xlabel("Generación")
    ax.set_ylabel("Fitness (millones de u.m. por día)")
    ax.set_title("Convergencia del algoritmo genético")
    ax.legend(loc="lower right")
    guardar(fig, "3_convergencia_ga.png")


def _cond(e, cid, conf):
    return next(c for c in e["condiciones"] if c["condicion"] == cid and c["configuracion"] == conf)


def g4_base_vs_mejorada():
    e = leer_json(RES / "experimentos" / "escenarios.json")
    b, m = _cond(e, "principal", "base"), _cond(e, "principal", "mejorada")
    lim = 100 * e["meta"]["limite_abandono"]
    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(13, 4))
    for i, (c, k) in enumerate(((b, "base"), (m, "mejorada"))):
        mi = c["metricas"]["ingreso_total"]
        a1.bar(i, mi["media"] / 1e6, yerr=[[x / 1e6 for x in y] for y in err(mi)], color=COLOR[k], capsize=6)
        ma = c["metricas"]["prob_abandono"]
        a2.bar(i, 100 * ma["media"], yerr=[[100 * x for x in y] for y in err(ma)], color=COLOR[k], capsize=6)
    etq = [f"{n}\n{c['conteos']['tragamonedas']}/{c['conteos']['blackjack']}/{c['conteos']['ruleta']}/"
           f"{c['conteos']['dados']}" for n, c in (("Base", b), ("Mejorada", m))]
    a1.set_xticks([0, 1], etq)
    a1.set_xlabel("Configuración (máquinas/blackjack/ruleta/dados)")
    a1.set_ylabel("Ingreso diario (millones de u.m.)")
    a1.set_title(f"Ingreso diario ({b['replicas']} réplicas, IC 95 %)")
    a2.axhline(lim, color=COLOR["limite"], ls="--", label=f"Límite {lim:.0f} %")
    a2.set_xticks([0, 1], ["Base", "Mejorada"])
    a2.set_ylabel("Probabilidad de abandono (%)")
    a2.set_title("Abandono (estimado, sin referencia real)")
    a2.set_ylim(0, lim * 1.25)
    a2.legend(fontsize=8)
    x = range(len(JUEGOS))
    for k, c, dx in (("base", b, -0.2), ("mejorada", m, 0.2)):
        a3.bar([i + dx for i in x], [100 * c["metricas"][f"utilizacion_{j}"]["media"] for j in JUEGOS], 0.4,
               color=COLOR[k], label=k.capitalize())
    a3.set_xticks(list(x), [NOMBRE[j] for j in JUEGOS])
    a3.set_ylabel("Utilización promedio (%)")
    a3.set_title("Utilización por recurso")
    a3.legend(fontsize=8)
    fig.suptitle("Escenario base contra propuesta mejorada (mismas semillas)", fontweight="bold")
    guardar(fig, "4_base_vs_mejorada.png")


def g5_sensibilidad():
    e = leer_json(RES / "experimentos" / "escenarios.json")
    lim = 100 * e["meta"]["limite_abandono"]
    fig, ax = plt.subplots(2, 2, figsize=(11, 7.5))
    for col, clave, xlabel in ((0, "llegadas", "Factor de llegadas (x respecto a 2023)"),
                               (1, "paciencia", "Paciencia media en cola (min)")):
        s = e["sensibilidad"][clave]["serie"]
        xs = [p["valor"] for p in s]
        for k in ("base", "mejorada"):
            ing = [p[k]["ingreso_total"] for p in s]
            ab = [p[k]["prob_abandono"] for p in s]
            ax[0][col].plot(xs, [v["media"] / 1e6 for v in ing], lw=2.5, color=COLOR[k], label=k.capitalize(),
                            marker="o", ms=4)
            ax[0][col].fill_between(xs, [v["ic95"][0] / 1e6 for v in ing], [v["ic95"][1] / 1e6 for v in ing],
                                    color=COLOR[k], alpha=0.15)
            ax[1][col].plot(xs, [100 * v["media"] for v in ab], lw=2.5, color=COLOR[k], label=k.capitalize(),
                            marker="o", ms=4)
            ax[1][col].fill_between(xs, [100 * v["ic95"][0] for v in ab], [100 * v["ic95"][1] for v in ab],
                                    color=COLOR[k], alpha=0.15)
        ax[1][col].axhline(lim, color=COLOR["limite"], ls="--", label=f"Límite {lim:.0f} %")
        ax[0][col].set_ylabel("Ingreso diario (millones de u.m.)")
        ax[1][col].set_ylabel("Probabilidad de abandono (%)")
        for r in (0, 1):
            ax[r][col].set_xlabel(xlabel)
            ax[r][col].legend(fontsize=8)
        ax[0][col].set_title(f"Ingreso según {e['sensibilidad'][clave]['variable']}")
        ax[1][col].set_title(f"Abandono según {e['sensibilidad'][clave]['variable']}")
    fig.suptitle("Sensibilidad (bandas: IC 95 %; punto central con 100 réplicas, el resto con 30)",
                 fontweight="bold")
    guardar(fig, "5_sensibilidad.png")


def g6_diferencias():
    e = leer_json(RES / "experimentos" / "escenarios.json")
    pares = e["pares"]
    fig, ax = plt.subplots(figsize=(8, 0.55 * len(pares) + 1.4))
    for i, p in enumerate(reversed(pares)):
        d = p["ingreso"]
        color = COLOR["mejorada"] if p["mejorada_dentro_del_limite"] else COLOR["limite"]
        ax.errorbar(d["pct"], i, xerr=[[d["pct"] - d["pct_ic95"][0]], [d["pct_ic95"][1] - d["pct"]]],
                    fmt="o", color=color, capsize=5, lw=2)
    ax.axvline(0, color="#555", lw=1)
    ax.set_yticks(range(len(pares)), [f"{p['etiqueta']} (n={p['replicas']})" for p in reversed(pares)])
    ax.set_xlabel("Cambio de ingreso, mejorada - base (% del ingreso base)")
    ax.set_title("Mejora simulada por condición (IC 95 %, diferencias pareadas)")
    ax.plot([], [], "o", color=COLOR["mejorada"], label="Mejorada cumple abandono ≤ 10 %")
    ax.plot([], [], "o", color=COLOR["limite"], label="Mejorada excede el límite")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, frameon=False)
    guardar(fig, "6_diferencias_pareadas.png")


def g7_area():
    ruta = RES / "experimentos" / "sensibilidad_area.json"
    if not ruta.exists():
        print("  (sin sensibilidad_area.json: corre src/experimentos/sensibilidad_area.py)")
        return
    a = leer_json(ruta)
    es = a["escenarios"]
    lim = 100 * a["limite_abandono"]
    etq = [f"{e['etiqueta']}\nBJ/R/D = {e['area_por_unidad']['blackjack']}/{e['area_por_unidad']['ruleta']}/"
           f"{e['area_por_unidad']['dados']}\nGA: {'/'.join(str(e['piso_elegido'][j]) for j in JUEGOS)}" for e in es]
    x = range(len(es))
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6))
    for i, e in enumerate(es):
        d = e["diferencia"]["ingreso"]
        a1.bar(i, d["pct"], color=COLOR["mejorada"], yerr=[[d["pct"] - d["pct_ic95"][0]], [d["pct_ic95"][1] - d["pct"]]],
               capsize=6)
        a1.text(i, d["pct_ic95"][1] + 0.3, f"{d['pct']:+.1f} %", ha="center", fontsize=9)
    a1.axhline(0, color="#555", lw=1)
    a1.set_xticks(list(x), etq, fontsize=8)
    a1.set_ylabel("Mejora de ingreso (% del ingreso base)")
    a1.set_title(f"Mejora del reparto del GA ({a['replicas']} réplicas pareadas, IC 95 %)")
    for k, (col, nombre) in enumerate((("base", "Base"), ("mejorada", "Reparto del GA"))):
        vals = [100 * e[col]["prob_abandono"]["media"] for e in es]
        a2.bar([i + (k - 0.5) * 0.38 for i in x], vals, 0.38, color=COLOR[col], label=nombre)
    a2.axhline(lim, color=COLOR["limite"], ls="--", label=f"Límite {lim:.0f} %")
    a2.set_ylim(7, 11)
    a2.set_xticks(list(x), etq, fontsize=8)
    a2.set_ylabel("Probabilidad de abandono (%)")
    a2.set_title("Abandono (estimado, sin referencia real)")
    a2.legend(fontsize=8)
    fig.suptitle("Sensibilidad al área por unidad de las mesas (el GA se corre de nuevo en cada escenario)",
                 fontweight="bold")
    guardar(fig, "7_sensibilidad_area.png")


def main():
    print(f"Gráficas en {SALIDA.relative_to(RAIZ)}/")
    g1_llegadas()
    g2_comparacion()
    g3_convergencia()
    g4_base_vs_mejorada()
    g5_sensibilidad()
    g6_diferencias()
    g7_area()


if __name__ == "__main__":
    main()
