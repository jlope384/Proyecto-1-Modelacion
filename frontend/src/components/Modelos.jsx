import { useState } from "react";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";
import { api } from "../api.js";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const JUEGOS = ["ruleta", "dados", "tragamonedas", "blackjack"];

const EJES = {
  ticks: { color: "#f2f2f2" },
  grid: { color: "rgba(244,234,216,0.1)" },
};

function opciones(tituloY) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: "#f2f2f2" } } },
    scales: {
      x: EJES,
      y: { ...EJES, title: { display: true, text: tituloY, color: "#f2f2f2" } },
    },
  };
}

function Grafica({ children }) {
  return <div className="grafica-caja">{children}</div>;
}

function Veredicto({ ok, children }) {
  return <p className={`resultado ${ok ? "gano" : "perdio"}`}>{children}</p>;
}

export default function Modelos() {
  // --- Fuente uniforme (LCG vs Mersenne Twister) ---
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

  // --- Comparación inversa vs aceptación-rechazo por juego ---
  const [juegoComp, setJuegoComp] = useState("ruleta");
  const [nComp, setNComp] = useState(30000);
  const [comparacion, setComparacion] = useState(null);
  const [errorComp, setErrorComp] = useState(null);

  async function compararMetodos() {
    try {
      const r = await api("/api/comparacion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ juego: juegoComp, n: Number(nComp) }),
      });
      setComparacion(r);
      setErrorComp(null);
    } catch (e) {
      setErrorComp(e.message);
      setComparacion(null);
    }
  }

  // --- Llegadas de jugadores (proceso de Poisson) ---
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

  return (
    <section className="tab-panel">
      <h2>La casa por dentro: el motor que decide cada apuesta</h2>
      <p className="ayuda">
        Cada giro de la ruleta, cada tirada de dados y cada jugador que entra por la puerta salen
        del mismo motor de números aleatorios. Aquí se puede correr ese motor en vivo y ver que no
        hace trampa: la fuente de aleatoriedad propia, los dos métodos con que la casa genera sus
        resultados, y cómo se modela la entrada de jugadores al casino.
      </p>

      {/* --- Fuente uniforme --- */}
      <h3>1. El generador detrás de cada tirada</h3>
      <p className="ayuda">
        Ruleta, dados y tragamonedas no usan <code>random</code> de Python: todos beben de este
        generador congruencial lineal (LCG) propio. Antes de confiar en él para pagar o cobrar
        apuestas, hay que probar que se comporta como un U(0,1) de verdad — y compararlo contra el
        Mersenne Twister de Python, la referencia de la industria.
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
                    backgroundColor: "rgba(212,175,55,0.7)",
                  },
                  {
                    label: "Mersenne Twister",
                    data: uniforme.mersenne_twister.pruebas[1].histograma,
                    backgroundColor: "rgba(107,214,107,0.5)",
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

      {/* --- Comparación de métodos --- */}
      <h3>2. Dos formas de decidir el mismo giro</h3>
      <p className="ayuda">
        La casa puede generar el resultado de cada juego de dos maneras distintas —
        transformada inversa o aceptación-rechazo — y las dos son igual de justas. Elegí un juego
        y comprobá cuál le sale más barata a la casa.
      </p>
      <div className="form-fila">
        <label>
          Juego
          <select value={juegoComp} onChange={(e) => setJuegoComp(e.target.value)}>
            {JUEGOS.map((j) => (
              <option key={j} value={j}>
                {j}
              </option>
            ))}
          </select>
        </label>
        <label>
          n
          <input type="number" min="100" max="300000" value={nComp} onChange={(e) => setNComp(e.target.value)} />
        </label>
        <button onClick={compararMetodos}>Comparar métodos</button>
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
          {!comparacion.veredicto.ambos_pasan_chi2 && (
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
                      backgroundColor: "rgba(212,175,55,0.7)",
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
                      backgroundColor: "rgba(255,138,128,0.7)",
                    },
                  ],
                }}
                options={opciones("% de propuestas rechazadas")}
              />
            </Grafica>
          </div>
        </>
      )}

      {/* --- Llegadas (Poisson) --- */}
      <h3>3. ¿A qué hora llena la casa el salón?</h3>
      <p className="ayuda">
        Los jugadores no llegan a un ritmo constante: el casino se llena entre las 9pm y la 1am y
        se vacía de madrugada. Esa tasa variable λ(t) se modela como un proceso de Poisson no
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
              ` y ${(llegadas.metricas.tasa_rechazo * 100).toFixed(1)}% de rechazo`}
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
                    backgroundColor: "rgba(212,175,55,0.7)",
                  },
                  {
                    label: "Llegadas observadas (esta corrida)",
                    data: llegadas.llegadas_por_hora,
                    backgroundColor: "rgba(107,214,107,0.5)",
                  },
                ],
              }}
              options={opciones("Llegadas por hora")}
            />
          </Grafica>
        </>
      )}
    </section>
  );
}
