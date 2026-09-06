import { useState } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from "chart.js";
import { api } from "../api.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

export default function Simulacion() {
  const [juego, setJuego] = useState("ruleta");
  const [rondas, setRondas] = useState(1000);
  const [apuesta, setApuesta] = useState(10);
  const [ruletaTipo, setRuletaTipo] = useState("color");
  const [ruletaValor, setRuletaValor] = useState("rojo");
  const [dadosTipo, setDadosTipo] = useState("suma");
  const [dadosValor, setDadosValor] = useState("7");
  const [resultado, setResultado] = useState(null);
  const [error, setError] = useState(null);

  async function ejecutar() {
    const cuerpo = { juego, rondas: Number(rondas), apuesta: Number(apuesta) };
    if (juego === "ruleta") {
      cuerpo.tipo = ruletaTipo;
      cuerpo.valor = ruletaValor;
    } else if (juego === "dados") {
      cuerpo.tipo = dadosTipo;
      cuerpo.valor = dadosValor;
    }

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
    }
  }

  const datosGrafica = resultado && {
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

  return (
    <section className="tab-panel">
      <h2>Simulación Monte Carlo</h2>
      <p className="ayuda">
        Corre muchas rondas automáticas para ver el comportamiento del casino a largo plazo (no
        afecta tu saldo real).
      </p>
      <div className="form-fila">
        <label>
          Juego
          <select value={juego} onChange={(e) => setJuego(e.target.value)}>
            <option value="ruleta">Ruleta</option>
            <option value="dados">Dados</option>
            <option value="tragamonedas">Tragamonedas</option>
          </select>
        </label>
        <label>
          Rondas
          <input
            type="number"
            min="1"
            max="100000"
            value={rondas}
            onChange={(e) => setRondas(e.target.value)}
          />
        </label>
        <label>
          Apuesta fija
          <input type="number" min="1" value={apuesta} onChange={(e) => setApuesta(e.target.value)} />
        </label>
      </div>

      {juego === "ruleta" && (
        <div className="form-fila">
          <label>
            Tipo
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
            Tipo
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

      <button className="boton-primario" onClick={ejecutar}>Ejecutar simulación</button>

      {error && <p className="resultado perdio">{error}</p>}

      {resultado && (
        <div>
          <div className="stats-grid">
            <div className="stat">
              <span className="stat-label">Rondas</span>
              <span>{resultado.rondas}</span>
            </div>
            <div className="stat">
              <span className="stat-label">Victorias</span>
              <span>
                {resultado.victorias} / {resultado.derrotas} derrotas
              </span>
            </div>
            <div className="stat">
              <span className="stat-label">Prob. de ganar</span>
              <span>{(resultado.prob_victoria * 100).toFixed(2)}%</span>
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
              <span>{(resultado.retorno_sobre_apuesta * 100).toFixed(2)}%</span>
            </div>
          </div>
          <Line
            data={datosGrafica}
            options={{
              responsive: true,
              plugins: { legend: { labels: { color: "#f2f2f2" } } },
              scales: {
                x: {
                  ticks: { color: "#f2f2f2" },
                  title: { display: true, text: "Ronda (muestreada)", color: "#f2f2f2" },
                },
                y: {
                  ticks: { color: "#f2f2f2" },
                  title: { display: true, text: "Saldo", color: "#f2f2f2" },
                },
              },
            }}
          />
        </div>
      )}
    </section>
  );
}
