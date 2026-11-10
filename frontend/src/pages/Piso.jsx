// El piso: simula un día con la configuración elegida (POST /api/piso -> casino/piso.py).
import { useEffect, useState } from "react";
import { post } from "../api.js";
import { Barras, COLOR, Grafica } from "../components/charts.jsx";
import { Card, Cargando, ErrorCaja, Etiqueta, Stat, Veredicto } from "../components/ui.jsx";
import { JUEGO, UNIDAD, num, pct } from "../formato.js";

const FRANJAS = Array.from({ length: 12 }, (_, i) => `${2 * i}–${2 * i + 2}`);
const porFranja = (v) => FRANJAS.map((_, i) => (v[2 * i] || 0) + (v[2 * i + 1] || 0));

export default function Piso({ config }) {
  const cfg = config.datos;
  const [conteos, setConteos] = useState(null);
  const [factor, setFactor] = useState(1.0);
  const [paciencia, setPaciencia] = useState(8);
  const [semilla, setSemilla] = useState(42);
  const [dia, setDia] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);

  async function simular(c = conteos) {
    setCargando(true);
    setError(null);
    try {
      setDia(await post("/api/piso", { conteos: c, factor_llegadas: factor, paciencia_media_min: paciencia, semilla }));
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  useEffect(() => {
    if (cfg && !conteos) {
      setConteos(cfg.piso_base);
      setPaciencia(cfg.paciencia_media_min);
      simular(cfg.piso_base);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cfg]);

  if (config.cargando) return <Cargando />;
  if (config.error) return <ErrorCaja error={config.error} />;
  if (!conteos) return <Cargando />;

  const area = cfg.juegos.reduce((a, j) => a + (conteos[j] || 0) * cfg.area_por_unidad[j], 0);
  const sobra = area > cfg.area_base;
  const cambiar = (j, v) => setConteos({ ...conteos, [j]: Math.max(1, parseInt(v, 10) || 1) });
  const esIgual = (o) => cfg.juegos.every((j) => o[j] === conteos[j]);

  return (
    <div className="row">
      <section className="card side" aria-label="Configuración del piso">
        <div className="ch">
          <span>CONFIGURACIÓN</span>
          <Etiqueta tipo={esIgual(cfg.piso_base) ? "publico" : "estimado"}>
            {esIgual(cfg.piso_base) ? "Base: Nevada 2023 / 4" : esIgual(cfg.piso_mejorada) ? "Mejorada por el GA" : "Configuración propia"}
          </Etiqueta>
        </div>
        <div className="cb">
          <div className="btnrow">
            <button className={esIgual(cfg.piso_base) ? "ob on" : "ob"} aria-pressed={esIgual(cfg.piso_base)} onClick={() => setConteos(cfg.piso_base)}>
              BASE
            </button>
            <button className={esIgual(cfg.piso_mejorada) ? "ob on" : "ob"} aria-pressed={esIgual(cfg.piso_mejorada)} onClick={() => setConteos(cfg.piso_mejorada)}>
              MEJORADA (GA)
            </button>
          </div>
          <div className="f h">
            <span>Juego</span>
            <span className="r">Unidades</span>
            <span className="r">Puestos</span>
          </div>
          {cfg.juegos.map((j) => (
            <div className="f" key={j}>
              <label htmlFor={`u-${j}`}>
                {JUEGO[j]}
                <span className="sub">{UNIDAD[j]}</span>
              </label>
              <input id={`u-${j}`} type="number" min="1" max="500" value={conteos[j]} onChange={(e) => cambiar(j, e.target.value)} />
              <span className="r ro" title="Puestos por unidad, supuesto del Proyecto 1">
                {cfg.puestos_por_unidad[j]}
              </span>
            </div>
          ))}
          <hr />
          <div className="pf">
            <label htmlFor="fa">
              Factor de llegadas<small>x respecto a 2023, de 0.5 a 2.0</small>
            </label>
            <input id="fa" type="number" step="0.1" min="0.5" max="2" value={factor} onChange={(e) => setFactor(parseFloat(e.target.value))} />
          </div>
          <div className="pf">
            <label htmlFor="pa">
              Paciencia media<small>minutos en cola</small>
            </label>
            <input id="pa" type="number" step="1" min="1" max="60" value={paciencia} onChange={(e) => setPaciencia(parseFloat(e.target.value))} />
          </div>
          <div className="pf">
            <label htmlFor="se">
              Semilla<small>reproducible</small>
            </label>
            <input id="se" type="number" value={semilla} onChange={(e) => setSemilla(parseInt(e.target.value, 10) || 0)} />
          </div>
          <hr />
          <div className="al">
            <span>ÁREA OCUPADA</span>
            <span>
              {num(area)} / {num(cfg.area_base)}
            </span>
          </div>
          <div className="trk">
            <div className={sobra ? "fill over" : "fill"} style={{ width: `${Math.min(100, (100 * area) / cfg.area_base)}%` }} />
          </div>
          <p className="why" style={{ margin: "8px 0 16px" }}>
            Área en máquinas equivalentes: blackjack {cfg.area_por_unidad.blackjack}, ruleta {cfg.area_por_unidad.ruleta}, dados{" "}
            {cfg.area_por_unidad.dados} (estimación del equipo).{" "}
            {sobra ? `Excede el área base en ${num(area - cfg.area_base)}: ya no es una redistribución.` : "Dentro del área base."}
          </p>
          <button className="btn solid" disabled={cargando} onClick={() => simular()}>
            {cargando ? "SIMULANDO…" : "SIMULAR UN DÍA"}
          </button>
        </div>
      </section>

      <div className="main">
        {error && <ErrorCaja error={error} />}
        {!dia && !error && <Cargando texto="Simulando el día base…" />}
        {dia && <Resultados dia={dia} />}
      </div>
    </div>
  );
}

function Resultados({ dia }) {
  const est = <Etiqueta tipo="estimado">Estimado, sin referencia real</Etiqueta>;
  const juegos = Object.keys(dia.por_juego);
  const little = dia.little;
  const errLittle = Math.abs(little.L_observado - little.L_estimado_por_little) / Math.max(little.L_observado, 1e-9);
  return (
    <>
      <div className="stats">
        <Stat l="INGRESO DEL DÍA" v={num(dia.ingreso_total)} u="u.m." s="Unidades monetarias del modelo" />
        <Stat l="ESPERA MEDIA" v={num(dia.espera_promedio_min, 2)} u="min" chip={est} />
        <Stat
          l="ABANDONO"
          v={num(100 * dia.prob_abandono, 1)}
          u="%"
          s={dia.prob_abandono <= dia.limite_abandono ? `Dentro del límite de ${pct(dia.limite_abandono, 0)}` : `Excede el límite de ${pct(dia.limite_abandono, 0)}`}
          chip={est}
        />
        <Stat l="UTILIZACIÓN" v={num(100 * dia.utilizacion_global, 0)} u="%" s="Puestos ocupados en promedio" />
        <Stat l="SESIONES" v={num(dia.llegadas)} u="" s={`${num(dia.atendidos)} atendidas · ${num(dia.abandonos)} abandonos`} />
        <Stat l="HOLD GLOBAL" v={num(100 * dia.hold_global, 2)} u="%" s="Ingreso ÷ apostado" />
      </div>
      <p className="why">
        Las cifras monetarias están en u.m.: el modelo no tiene unidad real. Los datos de Nevada están en dólares, así que se comparan por
        proporciones y por win por unidad, no en valor absoluto. Simulado en {num(dia.segundos, 1)} s con la semilla {dia.semilla}.
      </p>
      <div className="cols">
        <Card titulo="COLA Y ABANDONO" extra={<Etiqueta tipo="estimado" />}>
          <Grafica titulo="Cola promedio y abandonos por franja" sub="Eje Y: clientes · Eje X: hora del día, franjas de 2 h">
            <Barras
              etiquetas={FRANJAS}
              series={[
                { etiqueta: "Cola promedio (clientes)", datos: porFranja(dia.por_hora.cola_promedio).map((x) => x / 2), color: COLOR.base },
                { etiqueta: "Abandonos (clientes)", datos: porFranja(dia.por_hora.abandonos), color: COLOR.estimado },
              ]}
              xTitulo="Hora del día"
              yTitulo="Clientes"
              formato={(v) => num(v, 1)}
            />
          </Grafica>
          <details className="tabla">
            <summary>Ver tabla por franja</summary>
            <div className="tw">
              <table>
                <thead>
                  <tr>
                    <th>Franja (h)</th>
                    <th className="n">Llegadas</th>
                    <th className="n">Cola promedio</th>
                    <th className="n">Abandonos</th>
                  </tr>
                </thead>
                <tbody>
                  {FRANJAS.map((f, i) => (
                    <tr key={f}>
                      <td>{f}</td>
                      <td className="n">{num(porFranja(dia.por_hora.llegadas)[i])}</td>
                      <td className="n">{num(porFranja(dia.por_hora.cola_promedio)[i] / 2, 2)}</td>
                      <td className="n">{num(porFranja(dia.por_hora.abandonos)[i])}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </Card>
        <Card
          titulo="HOLD POR JUEGO"
          cuerpo={false}
          pie="Hold = ingreso ÷ apostado. Win por unidad = ingreso ÷ mesas o máquinas, en u.m. por día. El win por unidad relativo a una máquina es lo que se compara con Nevada."
        >
          <div className="tw">
            <table>
              <thead>
                <tr>
                  <th>Juego</th>
                  <th className="n">Unid.</th>
                  <th className="n">Apostado</th>
                  <th className="n">Ingreso</th>
                  <th className="n">Hold</th>
                  <th className="n">Win/unidad</th>
                  <th className="n">Utiliz.</th>
                </tr>
              </thead>
              <tbody>
                {juegos.map((j) => {
                  const g = dia.por_juego[j];
                  return (
                    <tr key={j}>
                      <td>{JUEGO[j]}</td>
                      <td className="n">{g.unidades}</td>
                      <td className="n">{num(g.apostado)}</td>
                      <td className="n">{num(g.ingreso)}</td>
                      <td className="n">{g.hold === null ? "—" : pct(g.hold, 2)}</td>
                      <td className="n">{num(g.win_por_unidad)}</td>
                      <td className="n">{pct(g.utilizacion, 0)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
      <Card titulo="CONSISTENCIA DEL DÍA SIMULADO">
        <div className="tw">
          <table>
            <tbody>
              <tr>
                <td>Ley de Little</td>
                <td className="m">
                  L observado {num(little.L_observado, 2)} · λ·W {num(little.L_estimado_por_little, 2)} · error {pct(errLittle, 2)}
                </td>
                <td>
                  <Veredicto ok={errLittle < 0.05} />
                </td>
              </tr>
              <tr>
                <td>Conservación de clientes</td>
                <td className="m">
                  {num(dia.llegadas)} llegadas = {num(dia.atendidos)} atendidos + {num(dia.abandonos)} abandonos
                </td>
                <td>
                  <Veredicto ok={dia.conservacion} />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
