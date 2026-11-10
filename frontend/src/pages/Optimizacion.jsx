// Optimización: resultado del GA (GET /api/optimizacion/resultado) y corrida mini
// (POST /api/optimizacion/correr + GET /api/optimizacion/estado -> src/optimizacion/genetico.py --prueba).
import { useEffect, useRef, useState } from "react";
import { api, post } from "../api.js";
import { COLOR, Grafica, Lineas } from "../components/charts.jsx";
import { Aviso, Card, ConDatos, ErrorCaja, Etiqueta, Stat, Veredicto } from "../components/ui.jsx";
import { JUEGO, ic, num, pct, signo } from "../formato.js";

const NOMBRE_PARAM = {
  poblacion: "Población",
  generaciones_max: "Generaciones máximas",
  prob_cruce: "Prob. de cruce",
  prob_mutacion: "Prob. de mutación",
  torneo: "Tamaño del torneo",
  elite: "Élite",
  estancamiento: "Parada por estancamiento",
  replicas_fitness: "Réplicas por evaluación",
  replicas_reevaluacion: "Réplicas de re-evaluación",
  lambda_penalizacion: "Penalización λ",
};
const JUEGOS = ["tragamonedas", "blackjack", "ruleta", "dados"];

export default function Optimizacion() {
  return <ConDatos ruta="/api/optimizacion/resultado">{(d) => <Vista d={d} />}</ConDatos>;
}

function areaDe(c, a) {
  return JUEGOS.reduce((s, j) => s + c[j] * a[j], 0);
}

function Vista({ d }) {
  const h = d.historial;
  const c = d.comprobacion;
  const ok = c.area_igual && c.minimo_por_juego && c.abandono_reevaluado_dentro_del_limite && c.todos_los_evaluados_factibles;
  const dif = d.diferencia;
  return (
    <div className="row">
      <div className="side" style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        <section className="card" aria-label="Parámetros del algoritmo genético">
          <div className="ch">
            <span>PARÁMETROS DEL GA</span>
            <Etiqueta tipo="sintetico">Corrida completa</Etiqueta>
          </div>
          <div className="cb">
            {d.parametros.map((p) => (
              <div className="pf" key={p.clave}>
                <span>
                  {NOMBRE_PARAM[p.clave] || p.clave}
                  <small className="why">{p.justificacion}</small>
                </span>
                <input type="text" aria-label={NOMBRE_PARAM[p.clave] || p.clave} value={p.valor} readOnly />
              </div>
            ))}
            <p className="why" style={{ marginTop: 8 }}>
              {d.configuraciones_evaluadas} configuraciones evaluadas, {num(d.simulaciones)} días simulados en {num(d.segundos)} s. Representación:
              enteros [máquinas, blackjack, ruleta, dados]; selección por torneo, cruce de un punto, mutación ±1 y reparación al área fija.
            </p>
          </div>
        </section>
        <Mini />
      </div>

      <div className="main">
        <div className="stats">
          <Stat l="CAMBIO DE INGRESO" v={`${signo(dif.ingreso_pct, 1)}`} u="%" s={`${signo(dif.ingreso_media)} u.m./día · ${ic(dif.ingreso_ic95)}`} />
          <Stat l="CAMBIO DE ABANDONO" v={signo(dif.abandono_pp, 2)} u="pp" s="Mejorada menos base" chip={<Etiqueta tipo="estimado" />} />
          <Stat l="RÉPLICAS" v={d.base.replicas} s="Semillas nuevas, distintas a las del fitness" />
        </div>
        <Card titulo="CONVERGENCIA" extra={<Etiqueta tipo="sintetico" />}>
          <Grafica
            titulo="Mejor fitness y promedio de la población por generación"
            sub="Eje Y: fitness = ingreso medio menos penalización por abandono (millones de u.m. por día) · Eje X: generación. La media de la generación 0 cae fuera del eje por individuos penalizados."
            alto={280}
          >
            <Lineas
              etiquetas={h.map((x) => x.generacion)}
              series={[
                { etiqueta: "Mejor fitness acumulado", datos: h.map((x) => x.mejor_fitness_global / 1e6), color: COLOR.mejorada, puntos: true },
                { etiqueta: "Fitness promedio", datos: h.map((x) => x.media_fitness_gen / 1e6), color: COLOR.base, puntos: true },
              ]}
              xTitulo="Generación"
              yTitulo="Millones de u.m. por día"
              y={{ min: 0.4 }}
              formato={(v) => num(v, 3)}
            />
          </Grafica>
          <details className="tabla">
            <summary>Ver tabla</summary>
            <div className="tw">
              <table>
                <thead>
                  <tr>
                    <th>Gen.</th>
                    <th className="n">Mejor</th>
                    <th className="n">Promedio</th>
                    <th className="n">Distintos</th>
                    <th>Mejor reparto</th>
                  </tr>
                </thead>
                <tbody>
                  {h.map((x) => (
                    <tr key={x.generacion}>
                      <td>{x.generacion}</td>
                      <td className="n">{num(x.mejor_fitness_global)}</td>
                      <td className="n">{num(x.media_fitness_gen)}</td>
                      <td className="n">{x.diversidad}</td>
                      <td className="m">
                        {x.mejor_tragamonedas}/{x.mejor_blackjack}/{x.mejor_ruleta}/{x.mejor_dados}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </Card>

        <div className="cols">
          <Card titulo="BASE CONTRA MEJORADA" cuerpo={false} pie="Mesas por juego; tragamonedas en máquinas. Área en u.a.; 1 u.a. es una máquina. Métricas con 30 réplicas de semillas nuevas.">
            <div className="tw">
              <table>
                <thead>
                  <tr>
                    <th>Juego</th>
                    <th className="n">Base</th>
                    <th className="n">Mejorada</th>
                    <th className="n">Cambio</th>
                  </tr>
                </thead>
                <tbody>
                  {JUEGOS.map((j) => (
                    <tr key={j}>
                      <td>{JUEGO[j]}</td>
                      <td className="n">{d.base.conteos[j]}</td>
                      <td className="n">{d.mejorada.conteos[j]}</td>
                      <td className="n">{signo(d.mejorada.conteos[j] - d.base.conteos[j])}</td>
                    </tr>
                  ))}
                  <tr className="tot">
                    <td>Área usada</td>
                    <td className="n">{areaDe(d.base.conteos, d.area_por_unidad)}</td>
                    <td className="n">{c.area_solucion}</td>
                    <td className="n">{signo(c.area_solucion - areaDe(d.base.conteos, d.area_por_unidad))}</td>
                  </tr>
                  <tr className="tot">
                    <td>Área permitida</td>
                    <td className="n">{c.area_base}</td>
                    <td className="n">{c.area_base}</td>
                    <td className="n">—</td>
                  </tr>
                  <tr>
                    <td>Ingreso (u.m./día)</td>
                    <td className="n">{num(d.base.ingreso_media)}</td>
                    <td className="n">{num(d.mejorada.ingreso_media)}</td>
                    <td className="n">{signo(d.mejorada.ingreso_media - d.base.ingreso_media)}</td>
                  </tr>
                  <tr>
                    <td>Abandono</td>
                    <td className="n">{pct(d.base.abandono_media, 2)}</td>
                    <td className="n">{pct(d.mejorada.abandono_media, 2)}</td>
                    <td className="n">{signo(100 * (d.mejorada.abandono_media - d.base.abandono_media), 2)} pp</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
          <Card titulo="VERIFICACIÓN DE LA RESTRICCIÓN">
            <Aviso ok={ok} titulo={ok ? "RESTRICCIONES CUMPLIDAS" : "RESTRICCIÓN VIOLADA"}>
              Área {c.area_solucion} = {c.area_base}. Resultado de la comprobación hecha por código al terminar el GA
              (src/optimizacion/genetico.py), no un cálculo de esta pantalla.
            </Aviso>
            <div className="tw" style={{ marginTop: 14 }}>
              <table>
                <tbody>
                  {[
                    ["Área igual a la del piso base", c.area_igual],
                    ["Al menos una unidad por juego", c.minimo_por_juego],
                    ["Abandono re-evaluado ≤ 10 %", c.abandono_reevaluado_dentro_del_limite],
                    ["Todas las configuraciones evaluadas factibles", c.todos_los_evaluados_factibles],
                  ].map(([t, v]) => (
                    <tr key={t}>
                      <td>{t}</td>
                      <td>
                        <Veredicto ok={v} textoOk="CUMPLE" textoNo="NO CUMPLE" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        <Card titulo="RE-EVALUACIÓN DE CANDIDATOS" cuerpo={false} pie="Los mejores del GA se vuelven a simular con 30 semillas nuevas y se elige el de mayor ingreso que cumple el límite de abandono, para no quedarse con uno que solo tuvo suerte.">
          <div className="tw">
            <table>
              <thead>
                <tr>
                  <th>Reparto (máq./BJ/ruleta/dados)</th>
                  <th className="n">Fitness en el GA</th>
                  <th className="n">Ingreso re-evaluado</th>
                  <th className="n">Abandono</th>
                  <th>Límite</th>
                </tr>
              </thead>
              <tbody>
                {d.reevaluacion.map((r, i) => (
                  <tr key={i}>
                    <td>
                      {JUEGOS.map((j) => r.conteos[j]).join("/")}
                      {i === 0 && <span className="sub">piso base</span>}
                    </td>
                    <td className="n">{num(r.fitness_ga)}</td>
                    <td className="n">
                      {num(r.ingreso_media)}
                      <span className="sub">{ic(r.ingreso_ic95)}</span>
                    </td>
                    <td className="n">{pct(r.abandono_media, 2)}</td>
                    <td>
                      <Veredicto ok={r.abandono_media <= 0.1} textoOk="CUMPLE" textoNo="EXCEDE" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}

function Mini() {
  const [estado, setEstado] = useState(null);
  const [error, setError] = useState(null);
  const timer = useRef(null);

  const consultar = async () => {
    try {
      const e = await api("/api/optimizacion/estado");
      setEstado(e);
      if (e.estado === "corriendo") timer.current = setTimeout(consultar, 1500);
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    consultar();
    return () => clearTimeout(timer.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function correr() {
    setError(null);
    try {
      await post("/api/optimizacion/correr");
      clearTimeout(timer.current);
      timer.current = setTimeout(consultar, 500);
      setEstado({ estado: "corriendo", log: [] });
    } catch (e) {
      setError(e.message);
    }
  }

  const corriendo = estado && estado.estado === "corriendo";
  const r = estado && estado.resultado;
  return (
    <section className="card" aria-label="Versión mini del GA">
      <div className="ch">
        <span>VERSIÓN MINI EN VIVO</span>
      </div>
      <div className="cb">
        <button className="btn" disabled={corriendo} onClick={correr}>
          {corriendo ? `CORRIENDO… ${num(estado.segundos || 0)} s` : "CORRER VERSIÓN MINI"}
        </button>
        <p className="why" style={{ marginTop: 10 }}>
          Población 6, 3 generaciones, 3 réplicas por evaluación: unos 30 a 60 segundos. Sirve para mostrar que el algoritmo corre; el
          resultado que vale es el de la corrida completa.
        </p>
        {error && <ErrorCaja error={error} />}
        {estado && estado.estado === "error" && <ErrorCaja error="La corrida mini terminó con error. Revisa el registro." />}
        {r && (
          <div className="tw" style={{ marginTop: 12 }}>
            <table>
              <tbody>
                <tr>
                  <td>Reparto elegido</td>
                  <td className="n">{JUEGOS.map((j) => r.mejorada.conteos[j]).join("/")}</td>
                </tr>
                <tr>
                  <td>Cambio de ingreso</td>
                  <td className="n">{signo(r.diferencia.ingreso_pct, 1)} %</td>
                </tr>
                <tr>
                  <td>Área comprobada</td>
                  <td className="n">
                    <Veredicto ok={r.comprobacion.area_igual} textoOk="CUMPLE" textoNo="NO CUMPLE" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
        {estado && estado.log && estado.log.length > 0 && <pre className="log">{estado.log.join("\n")}</pre>}
      </div>
    </section>
  );
}
