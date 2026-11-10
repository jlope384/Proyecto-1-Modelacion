import { useState } from "react";
import { Bar, Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
} from "chart.js";
import { api } from "../api.js";

ChartJS.register(
  CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Legend
);

const JUEGOS = {
  ruleta: { label: "Ruleta", rondas: 5000, max: 100000 },
  dados: { label: "Dados", rondas: 5000, max: 100000 },
  tragamonedas: { label: "Tragamonedas", rondas: 5000, max: 100000 },
  blackjack: { label: "Blackjack", rondas: 20000, max: 100000 },
};

const ESTRATEGIAS = {
  blackjack: [
    ["basica", "Estrategia básica"],
    ["dealer", "Imitar al dealer"],
    ["umbral", "Umbral fijo"],
  ],
};

// Nombres legibles para el desglose que devuelve cada juego
const RESULTADOS = {
  blackjack: "Desenlace de la mano",
};

const ETIQUETA_DESGLOSE = {
  gana: "Gana", pierde: "Pierde", empate: "Empate", se_paso: "Se pasó",
  dealer_se_paso: "Dealer se pasó", blackjack: "Blackjack",
};

const EJES = {
  ticks: { color: "#f2f2f2" },
  grid: { color: "rgba(244,234,216,0.1)" },
};

function opciones(tituloY, tituloX) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: "#f2f2f2" } } },
    scales: {
      x: { ...EJES, title: tituloX ? { display: true, text: tituloX, color: "#f2f2f2" } : undefined },
      y: { ...EJES, title: { display: true, text: tituloY, color: "#f2f2f2" } },
    },
  };
}

function pct(x, dec = 2) {
  return `${(x * 100).toFixed(dec)}%`;
}

export default function Simulacion() {
  const [juego, setJuego] = useState("ruleta");
  const [rondas, setRondas] = useState(JUEGOS.ruleta.rondas);
  const [apuesta, setApuesta] = useState(10);
  const [metodo, setMetodo] = useState("inversa");
  const [semilla, setSemilla] = useState("");

  const [ruletaTipo, setRuletaTipo] = useState("color");
  const [ruletaValor, setRuletaValor] = useState("rojo");
  const [dadosTipo, setDadosTipo] = useState("suma");
  const [dadosValor, setDadosValor] = useState("7");
  const [bjEstrategia, setBjEstrategia] = useState("basica");
  const [bjUmbral, setBjUmbral] = useState(17);

  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);

  const cfg = JUEGOS[juego];

  function cambiarJuego(nuevo) {
    setJuego(nuevo);
    setRondas(JUEGOS[nuevo].rondas);
    setResultado(null);
    setError(null);
  }

  async function ejecutar() {
    const cuerpo = {
      juego,
      rondas: Number(rondas),
      apuesta: Number(apuesta),
      metodo,
    };
    if (semilla !== "") cuerpo.semilla = Number(semilla);

    if (juego === "ruleta") {
      cuerpo.tipo = ruletaTipo;
      cuerpo.valor = ruletaValor;
    } else if (juego === "dados") {
      cuerpo.tipo = dadosTipo;
      cuerpo.valor = dadosValor;
    } else if (juego === "blackjack") {
      cuerpo.tipo = bjEstrategia;
      cuerpo.valor = bjUmbral;
    }

    setCargando(true);
    try {
      const r = await api("/api/simulacion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cuerpo),
      });
      setResultado(r);
      setError(null);
    } catch (e) {
      setError(e.message);
      setResultado(null);
    } finally {
      setCargando(false);
    }
  }

  const datosSaldo = resultado && {
    labels: resultado.historial.map((_, i) => i),
    datasets: [
      {
        label: "Saldo simulado",
        data: resultado.historial,
        borderColor: "#d4af37",
        backgroundColor: "rgba(212,175,55,0.15)",
        fill: true,
        pointRadius: 0,
        tension: 0.15,
      },
    ],
  };

  const desglose = resultado && resultado.desglose
    ? Object.entries(resultado.desglose).sort((a, b) => b[1] - a[1])
    : null;

  return (
    <section className="tab-panel">
      <h2>Simulación Monte Carlo</h2>
      <p className="ayuda">
        Corre muchas rondas automáticas para ver el comportamiento del casino a largo plazo (no
        afecta tu saldo real). Donde existe forma cerrada, el retorno simulado se contrasta contra
        el teórico; en blackjack no la hay, así que esta simulación <em>es</em> la
        forma de estimarlo.
      </p>

      <div className="form-fila">
        <label>
          Juego
          <select value={juego} onChange={(e) => cambiarJuego(e.target.value)}>
            {Object.entries(JUEGOS).map(([id, j]) => (
              <option key={id} value={id}>{j.label}</option>
            ))}
          </select>
        </label>
        <label>
          Rondas
          <input
            type="number"
            min="1"
            max={cfg.max}
            value={rondas}
            onChange={(e) => setRondas(e.target.value)}
          />
        </label>
        <label>
          Apuesta fija
          <input type="number" min="1" value={apuesta} onChange={(e) => setApuesta(e.target.value)} />
        </label>
        <label>
          Método de generación
          <select value={metodo} onChange={(e) => setMetodo(e.target.value)}>
            <option value="inversa">Transformada inversa</option>
            <option value="aceptacion_rechazo">Aceptación-rechazo</option>
          </select>
        </label>
        <label>
          Semilla (opcional)
          <input
            type="number"
            placeholder="al azar"
            value={semilla}
            onChange={(e) => setSemilla(e.target.value)}
          />
        </label>
      </div>

      {juego === "ruleta" && (
        <div className="form-fila">
          <label>
            Tipo de apuesta
            <select value={ruletaTipo} onChange={(e) => setRuletaTipo(e.target.value)}>
              <option value="color">Color</option>
              <option value="paridad">Par / Impar</option>
              <option value="numero">Número exacto</option>
            </select>
          </label>
          <label>
            Valor
            <input type="text" value={ruletaValor} onChange={(e) => setRuletaValor(e.target.value)} />
          </label>
        </div>
      )}

      {juego === "dados" && (
        <div className="form-fila">
          <label>
            Tipo de apuesta
            <select value={dadosTipo} onChange={(e) => setDadosTipo(e.target.value)}>
              <option value="suma">Suma exacta</option>
              <option value="par_impar">Par / Impar</option>
            </select>
          </label>
          <label>
            Valor
            <input type="text" value={dadosValor} onChange={(e) => setDadosValor(e.target.value)} />
          </label>
        </div>
      )}

      {juego === "blackjack" && (
        <div className="form-fila">
          <label>
            Estrategia del jugador
            <select value={bjEstrategia} onChange={(e) => setBjEstrategia(e.target.value)}>
              {ESTRATEGIAS.blackjack.map(([id, l]) => (
                <option key={id} value={id}>{l}</option>
              ))}
            </select>
          </label>
          {bjEstrategia === "umbral" && (
            <label>
              Pedir mientras el total sea menor a
              <input
                type="number"
                min="12"
                max="21"
                value={bjUmbral}
                onChange={(e) => setBjUmbral(e.target.value)}
              />
            </label>
          )}
        </div>
      )}

      <button className="boton-primario" onClick={ejecutar} disabled={cargando}>
        {cargando ? "Simulando…" : "Ejecutar simulación"}
      </button>

      {error && <p className="resultado perdio">{error}</p>}

      {resultado && (
        <div>
          <div className="stats-grid">
            <div className="stat">
              <span className="stat-label">Rondas</span>
              <span>{resultado.rondas.toLocaleString()}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Victorias / empates / derrotas</span>
              <span>
                {resultado.victorias} / {resultado.empates} / {resultado.derrotas}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Prob. de ganar</span>
              <span>
                {pct(resultado.prob_victoria)}
                {resultado.prob_victoria_teorica !== undefined && (
                  <small> · teórica {pct(resultado.prob_victoria_teorica)}</small>
                )}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Saldo final</span>
              <span>{resultado.saldo_final.toFixed(2)}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Ganancia neta</span>
              <span>{resultado.ganancia_neta.toFixed(2)}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Retorno / apostado</span>
              <span>
                {pct(resultado.retorno_sobre_apuesta)}
                {resultado.retorno_teorico !== undefined && (
                  <small> · teórico {pct(resultado.retorno_teorico)}</small>
                )}
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Método</span>
              <span>
                {resultado.etiqueta_metodo}
                <small>
                  {" "}· {resultado.metricas_generador.uniformes_por_variable.toFixed(2)} uniformes
                  por variable
                  {resultado.metricas_generador.tasa_rechazo > 0 &&
                    ` · ${pct(resultado.metricas_generador.tasa_rechazo, 1)} rechazo`}
                </small>
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Semilla · duración</span>
              <span>
                {resultado.semilla}
                <small> · {resultado.segundos.toFixed(2)} s</small>
              </span>
            </div>
          </div>

          {resultado.retorno_teorico !== undefined && (
            <p className={`resultado ${Math.abs(resultado.diferencia_vs_teorico) < 0.02 ? "gano" : "perdio"}`}>
              Simulado {pct(resultado.retorno_sobre_apuesta)} contra {pct(resultado.retorno_teorico)}{" "}
              teórico: {Math.abs(resultado.diferencia_vs_teorico * 100).toFixed(2)} puntos
              porcentuales de diferencia.
            </p>
          )}

          {resultado.nota && <p className="ayuda">{resultado.nota}</p>}

          <div className="grafica-caja">
            <Line
              data={datosSaldo}
              options={opciones("Saldo", "Ronda (muestreada)")}
            />
          </div>

          {desglose && desglose.length > 0 && (
            <div className="grafica-caja">
              <Bar
                data={{
                  labels: desglose.map(([k]) => ETIQUETA_DESGLOSE[k] || k),
                  datasets: [
                    {
                      label: RESULTADOS[juego] || "Desglose",
                      data: desglose.map(([, v]) => v),
                      backgroundColor: "rgba(212,175,55,0.7)",
                    },
                  ],
                }}
                options={opciones("Rondas")}
              />
            </div>
          )}

          {resultado.zapato && (
            <p className="ayuda">
              El zapato se rebarajó {resultado.zapato.veces_barajado} veces en el transcurso de la
              simulación, tras repartir {resultado.zapato.cartas_repartidas.toLocaleString()} cartas.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
