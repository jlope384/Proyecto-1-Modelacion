import { useState } from "react";
import { Bar, Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from "chart.js";
import { api } from "../api.js";

ChartJS.register(
  CategoryScale, LinearScale, BarElement, PointElement, LineElement, Tooltip, Legend
);

// La carrera va aparte porque su variable base es CONTINUA (triangular) y se
// valida con otro endpoint; las demás son discretas y pasan por /api/comparacion.
const JUEGOS_DISCRETOS = ["ruleta", "dados", "tragamonedas", "blackjack", "poker"];

const EJES = {
  ticks: { color: "#f2f2f2" },
  grid: { color: "rgba(244,234,216,0.1)" },
};

function opciones(tituloY, extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: "#f2f2f2" } } },
    scales: {
      x: EJES,
      y: { ...EJES, title: { display: true, text: tituloY, color: "#f2f2f2" } },
    },
    ...extra,
  };
}

function Grafica({ children }) {
  return <div className="grafica-caja">{children}</div>;
}

function Veredicto({ ok, children }) {
  return <p className={`resultado ${ok ? "gano" : "perdio"}`}>{children}</p>;
}

function pct(x, dec = 2) {
  return `${(x * 100).toFixed(dec)}%`;
}

const ORO = "rgba(212,175,55,0.75)";
const VERDE = "rgba(107,214,107,0.6)";
const ROJO = "rgba(255,138,128,0.7)";

export default function Modelos() {
  // ------------------------------------------------ 1. fuente uniforme
  const [nUniforme, setNUniforme] = useState(50000);
  const [uniforme, setUniforme] = useState(null);
  const [errorUniforme, setErrorUniforme] = useState(null);

  async function validarUniforme() {
    try {
      const r = await api("/api/validacion/uniforme", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ n: Number(nUniforme) }),
      });
      setUniforme(r);
      setErrorUniforme(null);
    } catch (e) {
      setErrorUniforme(e.message);
      setUniforme(null);
    }
  }

  // -------------------------------------------- 2. comparación de métodos
  const [juegoComp, setJuegoComp] = useState("ruleta");
  const [nComp, setNComp] = useState(30000);
  const [comparacion, setComparacion] = useState(null);
  const [errorComp, setErrorComp] = useState(null);
  const [cargandoComp, setCargandoComp] = useState(false);

  async function compararMetodos() {
    setCargandoComp(true);
    try {
      let r;
      if (juegoComp === "carreras") {
        // caso continuo: la triangular se valida con chi-cuadrado de
        // intervalos equiprobables y KS, no con el chi-cuadrado discreto
        const bruto = await api("/api/carreras/validacion", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ n: Number(nComp) }),
        });
        r = {
          continuo: true,
          resultados: bruto.resultados.map((f) => ({
            etiqueta_metodo: f.etiqueta_metodo,
            prueba: f.chi2,
            ks: f.ks,
            metricas: f.metricas,
          })),
          veredicto: {
            ...bruto.veredicto,
            mas_rapido:
              bruto.veredicto.razon_tiempo >= 1 ? "inversa" : "aceptacion_rechazo",
          },
          costo_teorico_aceptacion_rechazo:
            bruto.resultados[0].costo_teorico_aceptacion_rechazo,
        };
      } else {
        r = await api("/api/comparacion", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ juego: juegoComp, n: Number(nComp) }),
        });
      }
      setComparacion(r);
      setErrorComp(null);
    } catch (e) {
      setErrorComp(e.message);
      setComparacion(null);
    } finally {
      setCargandoComp(false);
    }
  }

  // ------------------------------------------------------- 3. llegadas
  const [horasLlegadas, setHorasLlegadas] = useState(24);
  const [metodoLlegadas, setMetodoLlegadas] = useState("inversa");
  const [llegadas, setLlegadas] = useState(null);
  const [errorLlegadas, setErrorLlegadas] = useState(null);

  async function simularLlegadas() {
    try {
      const r = await api("/api/llegadas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ horas: Number(horasLlegadas), metodo: metodoLlegadas }),
      });
      setLlegadas(r);
      setErrorLlegadas(null);
    } catch (e) {
      setErrorLlegadas(e.message);
      setLlegadas(null);
    }
  }

  // -------------------------------------------------------- 4. blackjack
  const [bjRondas, setBjRondas] = useState(15000);
  const [bjEstrategias, setBjEstrategias] = useState(null);
  const [bjZapato, setBjZapato] = useState(null);
  const [errorBj, setErrorBj] = useState(null);
  const [cargandoBj, setCargandoBj] = useState(false);

  async function analizarBlackjack() {
    setCargandoBj(true);
    try {
      const [est, zap] = await Promise.all([
        api("/api/simulacion/blackjack/estrategias", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rondas: Number(bjRondas) }),
        }),
        api("/api/blackjack/analisis-zapato", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ manos: 4000 }),
        }),
      ]);
      setBjEstrategias(est);
      setBjZapato(zap);
      setErrorBj(null);
    } catch (e) {
      setErrorBj(e.message);
      setBjEstrategias(null);
      setBjZapato(null);
    } finally {
      setCargandoBj(false);
    }
  }

  // --------------------------------------------------------- 5. carreras
  const [crLotes, setCrLotes] = useState(40);
  const [crSesgo, setCrSesgo] = useState(null);
  const [crSoborno, setCrSoborno] = useState(null);
  const [errorCr, setErrorCr] = useState(null);
  const [cargandoCr, setCargandoCr] = useState(false);

  async function analizarCarreras() {
    setCargandoCr(true);
    try {
      const [sesgo, soborno] = await Promise.all([
        api("/api/carreras/precision-cuotas", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ lotes: Number(crLotes), m_referencia: 1500 }),
        }),
        api("/api/carreras/soborno/analisis", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ repeticiones: 250, apuesta: 100 }),
        }),
      ]);
      setCrSesgo(sesgo);
      setCrSoborno(soborno);
      setErrorCr(null);
    } catch (e) {
      setErrorCr(e.message);
      setCrSesgo(null);
      setCrSoborno(null);
    } finally {
      setCargandoCr(false);
    }
  }

  // ----------------------------------------------------------- 6. póker
  const [pkManos, setPkManos] = useState(120);
  const [pkEquity, setPkEquity] = useState(null);
  const [pkAzar, setPkAzar] = useState(null);
  const [errorPk, setErrorPk] = useState(null);
  const [cargandoPk, setCargandoPk] = useState(false);

  async function analizarPoker() {
    setCargandoPk(true);
    try {
      const cuerpo = (tipo) => ({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          juego: "poker",
          rondas: Number(pkManos),
          apuesta: 10,
          tipo,
          semilla: 2024,
        }),
      });
      const [eq, az] = await Promise.all([
        api("/api/simulacion", cuerpo("equity")),
        api("/api/simulacion", cuerpo("azar")),
      ]);
      setPkEquity(eq);
      setPkAzar(az);
      setErrorPk(null);
    } catch (e) {
      setErrorPk(e.message);
      setPkEquity(null);
      setPkAzar(null);
    } finally {
      setCargandoPk(false);
    }
  }

  const minutosPoker = Math.round((Number(pkManos) * 2 * 124) / 1000);

  return (
    <section className="tab-panel">
      <h2>La casa por dentro: el motor que decide cada apuesta</h2>
      <p className="ayuda">
        Cada giro de la ruleta, cada carta del zapato y cada jugador que entra por la puerta salen
        del mismo motor de números aleatorios. Aquí se puede correr ese motor en vivo y ver que no
        hace trampa: la fuente de aleatoriedad propia, los dos métodos con que la casa genera sus
        resultados, cómo se modela la entrada de jugadores, y los tres juegos donde la simulación
        no solo reparte sino que además decide o pone precio.
      </p>

      {/* ------------------------------------------------ 1 */}
      <h3>1. El generador detrás de cada tirada</h3>
      <p className="ayuda">
        Ningún juego usa <code>random</code> de Python: todos beben de este generador congruencial
        lineal (LCG) propio. Antes de confiar en él para pagar o cobrar apuestas, hay que probar que
        se comporta como un U(0,1) de verdad — y compararlo contra el Mersenne Twister de Python, la
        referencia de la industria.
      </p>
      <div className="form-fila">
        <label>
          n uniformes
          <input
            type="number"
            min="100"
            max="500000"
            value={nUniforme}
            onChange={(e) => setNUniforme(e.target.value)}
          />
        </label>
        <button onClick={validarUniforme}>Validar generador</button>
      </div>
      {errorUniforme && <p className="resultado perdio">{errorUniforme}</p>}
      {uniforme && (
        <>
          <Veredicto ok={uniforme.veredicto.apto}>
            {uniforme.veredicto.apto
              ? `El generador de la casa pasa las ${uniforme.veredicto.pruebas_corridas} pruebas: se puede confiar en él para pagar apuestas.`
              : `El generador de la casa falla ${uniforme.veredicto.pruebas_rechazadas} de ${uniforme.veredicto.pruebas_corridas} pruebas: ${uniforme.veredicto.nombres_rechazados.join(", ")}.`}
          </Veredicto>
          <Grafica>
            <Bar
              data={{
                labels: uniforme.lcg_propio.pruebas[1].histograma.map((_, i) => i),
                datasets: [
                  {
                    label: "LCG propio",
                    data: uniforme.lcg_propio.pruebas[1].histograma,
                    backgroundColor: ORO,
                  },
                  {
                    label: "Mersenne Twister",
                    data: uniforme.mersenne_twister.pruebas[1].histograma,
                    backgroundColor: VERDE,
                  },
                ],
              }}
              options={opciones("Frecuencia por intervalo (20 tramos de U(0,1))")}
            />
          </Grafica>
          <div className="stats-grid">
            {uniforme.lcg_propio.pruebas.map((p) => (
              <div key={p.prueba} className="stat">
                <span className="stat-label">{p.prueba}</span>
                <span style={{ color: p.rechaza_h0 ? "#ff8a80" : "#6bd66b" }}>
                  p = {p.p_valor.toFixed(4)} {p.rechaza_h0 ? "✗" : "✓"}
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ------------------------------------------------ 2 */}
      <h3>2. Dos formas de decidir el mismo giro</h3>
      <p className="ayuda">
        La casa puede generar el resultado de cada juego de dos maneras distintas — transformada
        inversa o aceptación-rechazo — y las dos son igual de justas. Elegí un juego y comprobá cuál
        le sale más barata. El póker y el blackjack reparten sin reemplazo; la carrera es el único
        caso continuo, con la velocidad de cada caballo saliendo de una triangular.
      </p>
      <div className="form-fila">
        <label>
          Juego
          <select value={juegoComp} onChange={(e) => setJuegoComp(e.target.value)}>
            {JUEGOS_DISCRETOS.map((j) => (
              <option key={j} value={j}>{j}</option>
            ))}
            <option value="carreras">carreras (continuo)</option>
          </select>
        </label>
        <label>
          n
          <input type="number" min="100" max="300000" value={nComp} onChange={(e) => setNComp(e.target.value)} />
        </label>
        <button onClick={compararMetodos} disabled={cargandoComp}>
          {cargandoComp ? "Comparando…" : "Comparar métodos"}
        </button>
      </div>
      {errorComp && <p className="resultado perdio">{errorComp}</p>}
      {comparacion && (
        <>
          <Veredicto ok={comparacion.veredicto.ambos_pasan_chi2}>
            En {juegoComp}, los dos métodos pasan chi-cuadrado:{" "}
            {comparacion.veredicto.ambos_pasan_chi2 ? "sí" : "no"}. El más rápido es{" "}
            {comparacion.veredicto.mas_rapido}, y aceptación-rechazo le cuesta a la casa{" "}
            {comparacion.veredicto.razon_uniformes.toFixed(2)}x más uniformes por variable.
          </Veredicto>
          {comparacion.costo_teorico_aceptacion_rechazo && (
            <p className="ayuda">
              Costo teórico de aceptación-rechazo aquí: c ={" "}
              {comparacion.costo_teorico_aceptacion_rechazo.constante_mayoracion.toFixed(2)}, o sea{" "}
              {comparacion.costo_teorico_aceptacion_rechazo.uniformes_esperados_por_variable.toFixed(2)}{" "}
              uniformes por variable y{" "}
              {pct(comparacion.costo_teorico_aceptacion_rechazo.tasa_rechazo_esperada, 1)} de rechazo
              esperado.
            </p>
          )}
          {!comparacion.veredicto.ambos_pasan_chi2 && comparacion.veredicto.nota_chi2 && (
            <p className="ayuda">{comparacion.veredicto.nota_chi2}</p>
          )}
          <div className="grafica-par">
            <Grafica>
              <Bar
                data={{
                  labels: comparacion.resultados.map((r) => r.etiqueta_metodo),
                  datasets: [
                    {
                      label: "Uniformes por variable",
                      data: comparacion.resultados.map((r) => r.metricas.uniformes_por_variable),
                      backgroundColor: ORO,
                    },
                  ],
                }}
                options={opciones("Uniformes consumidos por variable")}
              />
            </Grafica>
            <Grafica>
              <Bar
                data={{
                  labels: comparacion.resultados.map((r) => r.etiqueta_metodo),
                  datasets: [
                    {
                      label: "Tasa de rechazo",
                      data: comparacion.resultados.map((r) => r.metricas.tasa_rechazo * 100),
                      backgroundColor: ROJO,
                    },
                  ],
                }}
                options={opciones("% de propuestas rechazadas")}
              />
            </Grafica>
          </div>
          <div className="stats-grid">
            {comparacion.resultados.map((r) => (
              <div key={r.etiqueta_metodo} className="stat">
                <span className="stat-label">{r.etiqueta_metodo}</span>
                <span>
                  chi² p = {r.prueba.p_valor.toFixed(4)}
                  {r.ks && <small> · KS p = {r.ks.p_valor.toFixed(4)}</small>}
                  <small> · {r.metricas.microsegundos_por_variable.toFixed(2)} µs/variable</small>
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ------------------------------------------------ 3 */}
      <h3>3. ¿A qué hora llena la casa el salón?</h3>
      <p className="ayuda">
        Los jugadores no llegan a un ritmo constante: el casino se llena entre las 9pm y la 1am y se
        vacía de madrugada. Esa tasa variable λ(t) se modela como un proceso de Poisson no
        homogéneo; simulá una corrida y compará cuántos jugadores entraron por hora contra lo
        esperado.
      </p>
      <div className="form-fila">
        <label>
          Horas simuladas
          <input
            type="number"
            min="1"
            max="720"
            value={horasLlegadas}
            onChange={(e) => setHorasLlegadas(e.target.value)}
          />
        </label>
        <label>
          Método
          <select value={metodoLlegadas} onChange={(e) => setMetodoLlegadas(e.target.value)}>
            <option value="inversa">Inversión de Λ(t)</option>
            <option value="aceptacion_rechazo">Adelgazamiento (thinning)</option>
          </select>
        </label>
        <button onClick={simularLlegadas}>Simular llegadas</button>
      </div>
      {errorLlegadas && <p className="resultado perdio">{errorLlegadas}</p>}
      {llegadas && (
        <>
          <Veredicto ok>
            {llegadas.total_llegadas} llegadas generadas (esperadas ≈{" "}
            {llegadas.esperado.toFixed(1)}), con {llegadas.metricas.uniformes_por_variable.toFixed(2)}{" "}
            uniformes por llegada
            {llegadas.metricas.tasa_rechazo > 0 &&
              ` y ${pct(llegadas.metricas.tasa_rechazo, 1)} de rechazo`}
            .
          </Veredicto>
          <Grafica>
            <Bar
              data={{
                labels: llegadas.llegadas_por_hora.map((_, h) => `${h}h`),
                datasets: [
                  {
                    label: "λ(t) esperada por hora",
                    data: llegadas.tasa_por_hora.slice(0, llegadas.llegadas_por_hora.length),
                    backgroundColor: ORO,
                  },
                  {
                    label: "Llegadas observadas (esta corrida)",
                    data: llegadas.llegadas_por_hora,
                    backgroundColor: VERDE,
                  },
                ],
              }}
              options={opciones("Llegadas por hora")}
            />
          </Grafica>
        </>
      )}

      {/* ------------------------------------------------ 4 */}
      <h3>4. Blackjack: la estrategia importa, y el zapato se desbalancea</h3>
      <p className="ayuda">
        En blackjack no hay forma cerrada para la ventaja de la casa: depende de cómo juegue el
        jugador, así que hay que estimarla simulando. Y como las cartas salen sin reemplazo, la
        distribución cambia mientras se reparte: el costo de aceptación-rechazo sube con ella,
        aunque nada cambie en el generador.
      </p>
      <div className="form-fila">
        <label>
          Manos por estrategia
          <input
            type="number"
            min="1000"
            max="100000"
            value={bjRondas}
            onChange={(e) => setBjRondas(e.target.value)}
          />
        </label>
        <button onClick={analizarBlackjack} disabled={cargandoBj}>
          {cargandoBj ? "Simulando…" : "Analizar blackjack"}
        </button>
      </div>
      {errorBj && <p className="resultado perdio">{errorBj}</p>}
      {bjEstrategias && (
        <>
          <Veredicto ok>
            La mejor estrategia es <b>{bjEstrategias.mejor}</b>, pero todas pierden: la ventaja de
            la casa se reduce, no se elimina. Todos los escenarios corren con la misma semilla para
            que la diferencia no dependa del azar.
          </Veredicto>
          <Grafica>
            <Bar
              data={{
                labels: bjEstrategias.resultados.map((f) => f.etiqueta),
                datasets: [
                  {
                    label: "Retorno sobre lo apostado (%)",
                    data: bjEstrategias.resultados.map((f) => f.retorno_sobre_apuesta * 100),
                    backgroundColor: bjEstrategias.resultados.map((f) =>
                      f.etiqueta === bjEstrategias.mejor ? VERDE : ORO
                    ),
                  },
                ],
              }}
              options={opciones("Retorno sobre lo apostado (%)")}
            />
          </Grafica>
        </>
      )}
      {bjZapato && (
        <>
          <p className="ayuda">{bjZapato.lectura}</p>
          <Grafica>
            <Bar
              data={{
                labels: bjZapato.tramos.map((t) => t.tramo),
                datasets: [
                  {
                    label: "Tasa de rechazo de aceptación-rechazo (%)",
                    data: bjZapato.tramos.map((t) => t.tasa_rechazo * 100),
                    backgroundColor: ROJO,
                  },
                  {
                    label: "p_max promedio (×100)",
                    data: bjZapato.tramos.map((t) => t.p_max_promedio * 100),
                    backgroundColor: ORO,
                  },
                ],
              }}
              options={opciones("% / p_max escalado")}
            />
          </Grafica>
        </>
      )}

      {/* ------------------------------------------------ 5 */}
      <h3>5. Carreras: poner precio simulando, y el sesgo que eso trae</h3>
      <p className="ayuda">
        La casa no conoce la probabilidad de cada caballo: la estima corriendo la carrera m veces y
        fija la cuota como (1−margen)/p. Pero el favorito es, por definición, el caballo con la p
        estimada más alta, así que se lo elige junto con su error: su cuota queda corta. Apostar al
        azar no tiene ese sesgo, y por eso sirve de control.
      </p>
      <div className="form-fila">
        <label>
          Lotes por valor de m
          <input
            type="number"
            min="10"
            max="200"
            value={crLotes}
            onChange={(e) => setCrLotes(e.target.value)}
          />
        </label>
        <button onClick={analizarCarreras} disabled={cargandoCr}>
          {cargandoCr ? "Simulando…" : "Analizar carreras"}
        </button>
      </div>
      {cargandoCr && (
        <p className="ayuda">
          Esto corre muchas carreras completas: puede tardar un minuto o más.
        </p>
      )}
      {errorCr && <p className="resultado perdio">{errorCr}</p>}
      {crSesgo && (
        <>
          <p className="ayuda">{crSesgo.lectura}</p>
          <Grafica>
            <Line
              data={{
                labels: crSesgo.resultados.map((f) => `m = ${f.m}`),
                datasets: [
                  {
                    label: "Favorito",
                    data: crSesgo.resultados.map((f) => f.favorito.sesgo_p),
                    borderColor: "#ff8a80",
                    backgroundColor: ROJO,
                    tension: 0.2,
                  },
                  {
                    label: "Tapado",
                    data: crSesgo.resultados.map((f) => f.tapado.sesgo_p),
                    borderColor: "#d4af37",
                    backgroundColor: ORO,
                    tension: 0.2,
                  },
                  {
                    label: "Azar (control)",
                    data: crSesgo.resultados.map((f) => f.azar.sesgo_p),
                    borderColor: "#6bd66b",
                    backgroundColor: VERDE,
                    tension: 0.2,
                  },
                ],
              }}
              options={opciones("p estimada por la casa − p de referencia")}
            />
          </Grafica>
        </>
      )}
      {crSoborno && (
        <>
          <p className="ayuda">{crSoborno.lectura}</p>
          <Grafica>
            <Bar
              data={{
                labels: crSoborno.resultados.map((f) => f.escenario),
                datasets: [
                  {
                    label: "Retorno sobre la apuesta (%)",
                    data: crSoborno.resultados.map((f) => f.retorno_sobre_apuesta * 100),
                    backgroundColor: crSoborno.resultados.map((f) =>
                      f.retorno_sobre_apuesta > 0 ? VERDE : ROJO
                    ),
                  },
                ],
              }}
              options={opciones("Retorno sobre la apuesta (%)")}
            />
          </Grafica>
          <div className="stats-grid">
            {crSoborno.resultados.map((f) => (
              <div key={f.escenario} className="stat">
                <span className="stat-label">
                  {f.escenario}
                  {f.costo_soborno > 0 && ` (costo ${f.costo_soborno})`}
                </span>
                <span>
                  {pct(f.retorno_sobre_apuesta, 1)}
                  <small>
                    {" "}· IC95 [{pct(f.ic95_retorno[0], 1)}, {pct(f.ic95_retorno[1], 1)}]
                    {f.difiere_del_nominal ? " · difiere del nominal" : " · no difiere del nominal"}
                  </small>
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {/* ------------------------------------------------ 6 */}
      <h3>6. Póker: aquí la simulación no reparte, decide</h3>
      <p className="ayuda">
        En los otros cinco juegos el azar solo determina el resultado. En póker además alimenta la
        decisión: cada bot estima su equity completando al azar las cartas que faltan y la compara
        contra las pot odds. Para comprobar que esa señal sirve de algo, se enfrenta un asiento que
        la usa contra uno que decide sin estimar nada.
      </p>
      <div className="form-fila">
        <label>
          Manos por escenario
          <input
            type="number"
            min="20"
            max="1000"
            value={pkManos}
            onChange={(e) => setPkManos(e.target.value)}
          />
        </label>
        <button onClick={analizarPoker} disabled={cargandoPk}>
          {cargandoPk ? "Simulando…" : "Enfrentar equity contra azar"}
        </button>
      </div>
      <p className="ayuda">
        Son dos corridas de {pkManos} manos y cada decisión dispara una estimación por Monte Carlo:
        calculá unos {minutosPoker} segundos.
      </p>
      {errorPk && <p className="resultado perdio">{errorPk}</p>}
      {pkEquity && pkAzar && (
        <>
          <Veredicto ok={pkEquity.retorno_sobre_apuesta > pkAzar.retorno_sobre_apuesta}>
            El asiento que estima equity rinde {pct(pkEquity.retorno_sobre_apuesta)} y el que decide
            al azar {pct(pkAzar.retorno_sobre_apuesta)}. Con cuatro asientos simétricos el retorno
            debería rondar cero; la brecha es lo que cuesta ignorar la señal de equity.
          </Veredicto>
          <div className="grafica-par">
            <Grafica>
              <Bar
                data={{
                  labels: ["Equity (Monte Carlo)", "Azar (control)"],
                  datasets: [
                    {
                      label: "Retorno sobre lo apostado (%)",
                      data: [
                        pkEquity.retorno_sobre_apuesta * 100,
                        pkAzar.retorno_sobre_apuesta * 100,
                      ],
                      backgroundColor: [VERDE, ROJO],
                    },
                  ],
                }}
                options={opciones("Retorno sobre lo apostado (%)")}
              />
            </Grafica>
            <Grafica>
              <Bar
                data={{
                  labels: ["Equity (Monte Carlo)", "Azar (control)"],
                  datasets: [
                    {
                      label: "Manos ganadas (%)",
                      data: [
                        pkEquity.prob_victoria * 100,
                        pkAzar.prob_victoria * 100,
                      ],
                      backgroundColor: [VERDE, ROJO],
                    },
                  ],
                }}
                options={opciones("% de manos ganadas")}
              />
            </Grafica>
          </div>
          <p className="ayuda">{pkEquity.nota}</p>
        </>
      )}
    </section>
  );
}
