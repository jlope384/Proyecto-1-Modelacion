// Armar piso: reparto del área fija entre juegos. La estimación es lineal en el
// cliente; el botón "Simular" manda la configuración al modelo (POST /api/piso).
import { useEffect, useMemo, useState } from "react";
import { post } from "../api.js";
import { COLOR } from "../components/charts.jsx";
import { Aviso, Card, Cargando, ErrorCaja, Etiqueta, Stat } from "../components/ui.jsx";
import { JUEGO, UNIDAD, num, pct, signo } from "../formato.js";

const COL = { tragamonedas: COLOR.base, blackjack: COLOR.mejorada, ruleta: "#ffffff", dados: "#f06ac8" };
const MINIMO = 1; // el modelo exige al menos una unidad por juego

/**
 * Si el área supera la capacidad, los demás juegos bajan en proporción a su
 * área para dejar espacio al que se movió (pivot). Algoritmo del handoff de
 * diseño, con el mínimo de una unidad por juego del modelo.
 */
function balancear(conteos, pesos, pivot, cap, juegos) {
  const c = { ...conteos };
  const area = (j) => c[j] * pesos[j];
  const total = () => juegos.reduce((a, j) => a + area(j), 0);
  if (total() <= cap + 1e-9) return c;
  const otros = juegos.filter((j) => j !== pivot);
  const oSum = otros.reduce((a, j) => a + area(j), 0);
  const libre = Math.max(0, cap - area(pivot));
  if (oSum > 0) {
    const f = libre / oSum;
    otros.forEach((j) => {
      c[j] = Math.max(MINIMO, Math.floor((c[j] * pesos[j] * f) / pesos[j] + 1e-9));
    });
  }
  const resto = otros.reduce((a, j) => a + area(j), 0);
  if (area(pivot) + resto > cap) c[pivot] = Math.max(MINIMO, Math.floor((cap - resto) / pesos[pivot] + 1e-9));
  return c;
}

export default function Armar({ config }) {
  const cfg = config.datos;
  const [conteos, setConteos] = useState(null);
  const [pesos, setPesos] = useState(null);
  const [sim, setSim] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    if (cfg && !conteos) {
      setConteos(cfg.piso_base);
      setPesos(cfg.area_por_unidad);
    }
  }, [cfg, conteos]);

  const juegos = cfg ? cfg.juegos : [];
  const cap = cfg ? cfg.area_base : 0;
  const win = cfg ? cfg.win_por_unidad_dia_base : null;

  const calc = useMemo(() => {
    if (!conteos || !pesos || !win) return null;
    const area = juegos.reduce((a, j) => a + conteos[j] * pesos[j], 0);
    const ingreso = juegos.reduce((a, j) => a + conteos[j] * win[j], 0);
    const ingresoBase = juegos.reduce((a, j) => a + cfg.piso_base[j] * win[j], 0);
    const puestos = juegos.reduce((a, j) => a + conteos[j] * cfg.puestos_por_unidad[j], 0);
    return { area, ingreso, ingresoBase, puestos, sobra: area > cap + 1e-9 };
  }, [conteos, pesos, win, juegos, cap, cfg]);

  if (config.cargando) return <Cargando />;
  if (config.error) return <ErrorCaja error={config.error} />;
  if (!win) return <ErrorCaja error="Faltan los experimentos (win por unidad). Corre: python src/experimentos/correr.py" />;
  if (!conteos || !pesos || !calc) return <Cargando />;

  const mover = (j, v) => {
    setSim(null);
    setConteos(balancear({ ...conteos, [j]: Math.max(MINIMO, v) }, pesos, j, cap, juegos));
  };
  const cambiarPeso = (j, d) => {
    setSim(null);
    const np = { ...pesos, [j]: Math.min(20, Math.max(1, pesos[j] + d)) };
    setPesos(np);
    setConteos(balancear(conteos, np, j, cap, juegos));
  };
  const preset = (c) => {
    setSim(null);
    setPesos(cfg.area_por_unidad);
    setConteos(c);
  };
  async function simular() {
    setCargando(true);
    setError(null);
    try {
      const r = await post("/api/piso", { conteos, semilla: 42 });
      const b = await post("/api/piso", { conteos: cfg.piso_base, semilla: 42 });
      setSim({ r, b });
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  const libre = cap - calc.area;
  const denom = Math.max(calc.area, cap);
  const pesosModelo = juegos.every((j) => pesos[j] === cfg.area_por_unidad[j]);

  return (
    <>
      <div className="stats">
        <Stat l="ÁREA USADA" v={num(calc.area)} u="u.a." s={`De ${num(cap)} disponibles`} />
        <Stat l={calc.sobra ? "EXCESO DE ÁREA" : "ÁREA LIBRE"} v={num(Math.abs(libre))} u="u.a." s={calc.sobra ? "Fuera del área base" : "Dentro del área base"} />
        <Stat l="PUESTOS" v={num(calc.puestos)} s="Asientos de todos los juegos" />
        <Stat
          l="INGRESO ESTIMADO"
          v={num(calc.ingreso)}
          u="u.m./día"
          s={`${signo(calc.ingreso - calc.ingresoBase)} contra la base (cuenta lineal, sin congestión)`}
        />
      </div>
      <div className="row">
        <section className="card side" style={{ flex: "1 1 440px", maxWidth: 560 }} aria-label="Juegos del piso">
          <div className="ch">
            <span>JUEGOS DEL PISO</span>
            <span className="btnrow" style={{ margin: 0 }}>
              <button className="ob" onClick={() => preset(cfg.piso_base)}>
                BASE
              </button>
              <button className="ob" onClick={() => preset(cfg.piso_mejorada)}>
                GA
              </button>
            </span>
          </div>
          <div className="cb">
            <p className="why" style={{ marginBottom: 14 }}>
              El área es fija. Si subes un juego, los demás bajan en proporción a su área: para ganar en uno hay que sacrificar otros.
              Cada juego conserva al menos una unidad.
            </p>
            {juegos.map((j) => {
              // deja espacio para el mínimo de una unidad de cada uno de los otros juegos
              const minOtros = juegos.filter((o) => o !== j).reduce((a, o) => a + MINIMO * pesos[o], 0);
              const max = Math.max(MINIMO, Math.floor((cap - minOtros) / pesos[j]));
              const d = conteos[j] - cfg.piso_base[j];
              return (
                <div className="gm" key={j}>
                  <div className="gh">
                    <span className="gn">{JUEGO[j]}</span>
                    <span className="gc">
                      {conteos[j]} <small>{UNIDAD[j]}</small>
                    </span>
                  </div>
                  <label className="sr" htmlFor={`sl-${j}`}>
                    Cantidad de {JUEGO[j].toLowerCase()}
                  </label>
                  <input
                    id={`sl-${j}`}
                    className="rng"
                    type="range"
                    min={MINIMO}
                    max={max}
                    step="1"
                    value={conteos[j]}
                    onChange={(e) => mover(j, parseInt(e.target.value, 10))}
                  />
                  <div className="gf">
                    <span className="chip c-sin">{j === "tragamonedas" ? "Unidad de referencia" : `1 mesa = ${pesos[j]} máquinas`}</span>
                    <span className="wc">
                      Peso
                      {j !== "tragamonedas" && (
                        <button className="stp" aria-label={`Bajar el peso de ${JUEGO[j]}`} onClick={() => cambiarPeso(j, -1)}>
                          −
                        </button>
                      )}
                      <b>{pesos[j]} u.a.</b>
                      {j !== "tragamonedas" && (
                        <button className="stp" aria-label={`Subir el peso de ${JUEGO[j]}`} onClick={() => cambiarPeso(j, 1)}>
                          +
                        </button>
                      )}
                    </span>
                    <span>Área: {num(conteos[j] * pesos[j])} u.a.</span>
                    <span>{d === 0 ? "Igual a la base" : `${signo(d)} contra base`}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <div className="main">
          <section className="card" aria-label="Ocupación del piso">
            <div className="fimg q0">
              <div className="fi" />
              <div className="fd" />
              <div className="ft">
                Piso principal<small>Un solo piso · área disponible {num(cap)} u.a.</small>
              </div>
            </div>
            <div className="cb">
              <div className="al">
                <span>OCUPACIÓN DEL ÁREA</span>
                <span>{num((100 * calc.area) / cap)} %</span>
              </div>
              <div className="stack">
                {juegos.map((j) => (
                  <div key={j} className="sg" title={JUEGO[j]} style={{ width: `${((100 * conteos[j] * pesos[j]) / denom).toFixed(2)}%`, background: COL[j] }} />
                ))}
              </div>
              <div className="legend">
                {juegos.map((j) => (
                  <span className="lg" key={j}>
                    <i style={{ background: COL[j] }} />
                    {JUEGO[j]}
                  </span>
                ))}
                <span className="lg">La parte vacía de la barra es área libre</span>
              </div>
              <div style={{ marginTop: 14 }}>
                {calc.sobra ? (
                  <Aviso ok={false} titulo="EXCEDE EL ÁREA">
                    Sobran {num(-libre)} u.a. por encima de {num(cap)}. Baja unidades o pesos.
                  </Aviso>
                ) : (
                  <Aviso ok titulo="CABE EN EL PISO">
                    Área libre: {num(libre)} u.a. de {num(cap)}.
                  </Aviso>
                )}
              </div>
              <hr />
              <button className="btn solid" disabled={cargando} onClick={simular}>
                {cargando ? "SIMULANDO…" : "SIMULAR ESTA CONFIGURACIÓN"}
              </button>
              <p className="why" style={{ marginTop: 10 }}>
                Corre el modelo completo (con colas y abandono) para esta configuración y para la base, con la misma semilla. Un solo día:
                para conclusiones usa la pestaña Escenarios, que promedia 30 o más réplicas.
              </p>
              {error && <ErrorCaja error={error} />}
              {sim && (
                <div className="tw" style={{ marginTop: 12 }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Un día, semilla 42</th>
                        <th className="n">Base</th>
                        <th className="n">Esta configuración</th>
                        <th className="n">Cambio</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>Ingreso simulado (u.m.)</td>
                        <td className="n">{num(sim.b.ingreso_total)}</td>
                        <td className="n">{num(sim.r.ingreso_total)}</td>
                        <td className="n">{signo(sim.r.ingreso_total - sim.b.ingreso_total)}</td>
                      </tr>
                      <tr>
                        <td>Abandono (estimado)</td>
                        <td className="n">{pct(sim.b.prob_abandono)}</td>
                        <td className="n">{pct(sim.r.prob_abandono)}</td>
                        <td className="n">{signo(100 * (sim.r.prob_abandono - sim.b.prob_abandono), 1)} pp</td>
                      </tr>
                      <tr>
                        <td>Espera media (min)</td>
                        <td className="n">{num(sim.b.espera_promedio_min, 2)}</td>
                        <td className="n">{num(sim.r.espera_promedio_min, 2)}</td>
                        <td className="n">{signo(sim.r.espera_promedio_min - sim.b.espera_promedio_min, 2)}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </section>

          <Card
            titulo="DESGLOSE POR JUEGO"
            extra={<Etiqueta tipo="estimado">Cuenta lineal</Etiqueta>}
            cuerpo={false}
            pie={`Peso = área de una unidad en u.a.; 1 u.a. es una tragamonedas. ${
              pesosModelo ? "Son los pesos del modelo (estimación del equipo)." : "Cambiaste los pesos: el GA usó otros."
            } Ingreso estimado = unidades × win por unidad y día de la simulación base (100 réplicas). No toma en cuenta la congestión: para eso, simula.`}
          >
            <div className="tw">
              <table>
                <thead>
                  <tr>
                    <th>Juego</th>
                    <th className="n">Cantidad</th>
                    <th className="n">Peso (u.a.)</th>
                    <th className="n">Área (u.a.)</th>
                    <th className="n">Win/unidad·día</th>
                    <th className="n">Ingreso est.</th>
                  </tr>
                </thead>
                <tbody>
                  {juegos.map((j) => (
                    <tr key={j}>
                      <td>
                        <span className="sw" style={{ background: COL[j] }} /> {JUEGO[j]}
                      </td>
                      <td className="n">{conteos[j]}</td>
                      <td className="n">{pesos[j]}</td>
                      <td className="n">{num(conteos[j] * pesos[j])}</td>
                      <td className="n">{num(win[j])}</td>
                      <td className="n">{num(conteos[j] * win[j])}</td>
                    </tr>
                  ))}
                  <tr className="tot">
                    <td>Total</td>
                    <td className="n" />
                    <td className="n" />
                    <td className="n">{num(calc.area)}</td>
                    <td className="n" />
                    <td className="n">{num(calc.ingreso)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
