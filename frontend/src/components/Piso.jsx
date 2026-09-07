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

function Stat({ label, children }) {
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span>{children}</span>
    </div>
  );
}

const JUEGOS_LABEL = {
  tragamonedas: "Tragamonedas",
  ruleta: "Ruleta",
  blackjack: "Blackjack",
  dados: "Dados",
};

function histograma(valores, bins = 12) {
  if (!valores || valores.length === 0) return { labels: [], data: [] };
  const max = Math.max(...valores, 0.01);
  const ancho = max / bins;
  const conteo = new Array(bins).fill(0);
  valores.forEach((v) => {
    const idx = Math.min(bins - 1, Math.max(0, Math.floor(v / ancho)));
    conteo[idx] += 1;
  });
  return {
    labels: conteo.map((_, i) => `${(i * ancho).toFixed(1)}`),
    data: conteo,
  };
}

export default function Piso() {
  // --- Un día de operación ---
  const [horas, setHoras] = useState(24);
  const [metodo, setMetodo] = useState("inversa");
  const [semilla, setSemilla] = useState("");
  const [dia, setDia] = useState(null);
  const [errorDia, setErrorDia] = useState(null);
  const [cargandoDia, setCargandoDia] = useState(false);

  async function simularDia() {
    setCargandoDia(true);
    try {
      const r = await api("/api/piso", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          horas: Number(horas),
          metodo,
          semilla: semilla ? Number(semilla) : undefined,
        }),
      });
      setDia(r);
      setErrorDia(null);
    } catch (e) {
      setErrorDia(e.message);
      setDia(null);
    } finally {
      setCargandoDia(false);
    }
  }

  // --- Comparación de métodos a nivel de sistema ---
  const [replicas, setReplicas] = useState(10);
  const [comparacion, setComparacion] = useState(null);
  const [errorComp, setErrorComp] = useState(null);
  const [cargandoComp, setCargandoComp] = useState(false);

  async function compararMetodos() {
    setCargandoComp(true);
    try {
      const r = await api("/api/piso/comparacion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ horas: Number(horas), replicas: Number(replicas) }),
      });
      setComparacion(r);
      setErrorComp(null);
    } catch (e) {
      setErrorComp(e.message);
      setComparacion(null);
    } finally {
      setCargandoComp(false);
    }
  }

  const juegos = dia ? Object.keys(dia.utilizacion) : [];
  const hist = dia ? histograma(dia.esperas_min) : { labels: [], data: [] };

  return (
    <section className="tab-panel">
      <h2>El piso: clientes que llegan, hacen fila y se van</h2>
      <p className="ayuda">
        Esta es la simulación del sistema, no de un juego suelto: jugadores llegan por un proceso
        de Poisson no homogéneo, se sientan en una mesa o máquina con capacidad limitada, juegan
        rondas reales contra el juego que les tocó, y salen por quiebra, por meta, porque se les
        acabó el tiempo o porque se cansaron de esperar. De ahí salen el tiempo de espera, la
        longitud de fila y la probabilidad de congestión.
      </p>

      <div className="form-fila">
        <label>
          Horas simuladas
          <input
            type="number"
            min="1"
            max="168"
            value={horas}
            onChange={(e) => setHoras(e.target.value)}
          />
        </label>
        <label>
          Método
          <select value={metodo} onChange={(e) => setMetodo(e.target.value)}>
            <option value="inversa">Transformada inversa</option>
            <option value="aceptacion_rechazo">Aceptación-rechazo</option>
          </select>
        </label>
        <label>
          Semilla (opcional)
          <input
            type="number"
            placeholder="aleatoria"
            value={semilla}
            onChange={(e) => setSemilla(e.target.value)}
          />
        </label>
        <button onClick={simularDia} disabled={cargandoDia}>
          {cargandoDia ? "Simulando…" : "Simular día"}
        </button>
      </div>
      {errorDia && <p className="resultado perdio">{errorDia}</p>}

      {dia && (
        <>
          <div className="stats-grid">
            <Stat label="Llegaron">{dia.llegadas_totales}</Stat>
            <Stat label="Atendidos">{dia.atendidos}</Stat>
            <Stat label="Abandonaron la cola">{dia.abandonos}</Stat>
            <Stat label="P(congestión)">{(dia.prob_congestion * 100).toFixed(1)}%</Stat>
            <Stat label="P(abandono)">{(dia.prob_abandono * 100).toFixed(1)}%</Stat>
            <Stat label="Espera promedio">{dia.espera_promedio_min.toFixed(2)} min</Stat>
            <Stat label="Tiempo en el sistema">{dia.tiempo_sistema_promedio_min.toFixed(1)} min</Stat>
            <Stat label="Clientes en el piso (L)">{dia.clientes_promedio_sistema.toFixed(1)}</Stat>
            <Stat label="Ingreso del casino">
              Q{dia.ingreso_total.toLocaleString("es-GT", { maximumFractionDigits: 0 })}
            </Stat>
          </div>

          <Veredicto
            ok={
              Math.abs(dia.little.L_observado - dia.little.L_estimado_por_little) /
                Math.max(dia.little.L_observado, 1e-9) <
              0.05
            }
          >
            Chequeo de Little: L observado = {dia.little.L_observado.toFixed(2)}, λ_efectiva·W ={" "}
            {dia.little.L_estimado_por_little.toFixed(2)} — el motor de eventos es consistente.
          </Veredicto>

          <div className="grafica-par">
            <Grafica>
              <Bar
                data={{
                  labels: dia.llegadas_por_hora.map((_, h) => `${h}h`),
                  datasets: [
                    {
                      label: "λ(t) esperada",
                      data: dia.tasa_por_hora,
                      backgroundColor: "rgba(212,175,55,0.7)",
                    },
                    {
                      label: "Llegadas observadas",
                      data: dia.llegadas_por_hora,
                      backgroundColor: "rgba(107,214,107,0.5)",
                    },
                  ],
                }}
                options={opciones("Llegadas por hora")}
              />
            </Grafica>
            <Grafica>
              <Bar
                data={{
                  labels: dia.cola_promedio_por_hora.map((_, h) => `${h}h`),
                  datasets: [
                    {
                      label: "Clientes en cola (promedio)",
                      data: dia.cola_promedio_por_hora,
                      backgroundColor: "rgba(255,138,128,0.7)",
                    },
                  ],
                }}
                options={opciones("Longitud de fila por hora")}
              />
            </Grafica>
          </div>

          <div className="grafica-par">
            <Grafica>
              <Bar
                data={{
                  labels: hist.labels,
                  datasets: [
                    {
                      label: "Clientes",
                      data: hist.data,
                      backgroundColor: "rgba(212,175,55,0.7)",
                    },
                  ],
                }}
                options={opciones("Distribución de la espera en cola (min)")}
              />
            </Grafica>
            <Grafica>
              <Bar
                data={{
                  labels: juegos.map((j) => JUEGOS_LABEL[j]),
                  datasets: [
                    {
                      label: "Utilización",
                      data: juegos.map((j) => dia.utilizacion[j] * 100),
                      backgroundColor: "rgba(107,214,107,0.6)",
                    },
                    {
                      label: "Ingreso del casino (Q, /1000)",
                      data: juegos.map((j) => dia.ingreso_por_juego[j] / 1000),
                      backgroundColor: "rgba(212,175,55,0.7)",
                    },
                  ],
                }}
                options={opciones("Utilización (%) e ingreso por juego")}
              />
            </Grafica>
          </div>
        </>
      )}

      {/* --- Comparación de métodos a nivel de sistema --- */}
      <h3>¿Importa el método de generación para las conclusiones del sistema?</h3>
      <p className="ayuda">
        Se corren varios días completos con cada método, misma semilla por réplica, y se comparan
        los intervalos de confianza al 95%: si los dos métodos generan de la misma distribución,
        la espera en cola y el ingreso del casino deben coincidir. Lo que SÍ debe cambiar es el
        costo: uniformes consumidos por cliente atendido y la tasa de rechazo.
      </p>
      <div className="form-fila">
        <label>
          Réplicas por método
          <input
            type="number"
            min="2"
            max="30"
            value={replicas}
            onChange={(e) => setReplicas(e.target.value)}
          />
        </label>
        <button onClick={compararMetodos} disabled={cargandoComp}>
          {cargandoComp ? "Corriendo réplicas… (puede tardar ~20s)" : "Comparar métodos"}
        </button>
      </div>
      {errorComp && <p className="resultado perdio">{errorComp}</p>}

      {comparacion && (
        <>
          {(() => {
            const inv = comparacion.resultados.inversa;
            const ar = comparacion.resultados.aceptacion_rechazo;
            const solapan =
              inv.espera_cola_min.ic95[0] <= ar.espera_cola_min.ic95[1] &&
              ar.espera_cola_min.ic95[0] <= inv.espera_cola_min.ic95[1];
            return (
              <Veredicto ok={solapan}>
                {solapan
                  ? "Los intervalos de confianza de espera en cola se solapan: el método de generación no cambia las conclusiones del sistema."
                  : "Los intervalos NO se solapan con esta cantidad de réplicas; conviene correr más réplicas."}{" "}
                Aceptación-rechazo gasta {ar.uniformes_por_atendido.toFixed(0)} uniformes por
                cliente atendido contra {inv.uniformes_por_atendido.toFixed(0)} de la inversa (
                {(ar.uniformes_por_atendido / inv.uniformes_por_atendido).toFixed(1)}× más), con{" "}
                {(ar.tasa_rechazo * 100).toFixed(1)}% de rechazo.
              </Veredicto>
            );
          })()}

          <div className="stats-grid">
            {Object.values(comparacion.resultados).map((r) => (
              <div key={r.metodo} className="stat">
                <span className="stat-label">{r.etiqueta} — espera en cola</span>
                <span>
                  {r.espera_cola_min.media.toFixed(2)} min [{r.espera_cola_min.ic95[0].toFixed(2)},{" "}
                  {r.espera_cola_min.ic95[1].toFixed(2)}]
                </span>
              </div>
            ))}
            {Object.values(comparacion.resultados).map((r) => (
              <div key={r.metodo + "-ing"} className="stat">
                <span className="stat-label">{r.etiqueta} — ingreso</span>
                <span>
                  Q{r.ingreso_total.media.toLocaleString("es-GT", { maximumFractionDigits: 0 })}
                </span>
              </div>
            ))}
          </div>

          <div className="grafica-par">
            <Grafica>
              <Bar
                data={{
                  labels: Object.values(comparacion.resultados).map((r) => r.etiqueta),
                  datasets: [
                    {
                      label: "Uniformes por cliente atendido",
                      data: Object.values(comparacion.resultados).map((r) => r.uniformes_por_atendido),
                      backgroundColor: "rgba(212,175,55,0.7)",
                    },
                  ],
                }}
                options={opciones("Costo: uniformes consumidos por cliente")}
              />
            </Grafica>
            <Grafica>
              <Bar
                data={{
                  labels: Object.values(comparacion.resultados).map((r) => r.etiqueta),
                  datasets: [
                    {
                      label: "Segundos por día simulado",
                      data: Object.values(comparacion.resultados).map((r) => r.segundos_por_dia),
                      backgroundColor: "rgba(255,138,128,0.7)",
                    },
                  ],
                }}
                options={opciones("Costo: segundos por día simulado")}
              />
            </Grafica>
          </div>
        </>
      )}
    </section>
  );
}
