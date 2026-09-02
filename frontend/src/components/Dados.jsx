import { useState } from "react";
import { api } from "../api.js";

const SUMAS = Array.from({ length: 11 }, (_, i) => i + 2); // 2..12

export default function Dados({ onSaldoActualizado }) {
  const [apuesta, setApuesta] = useState(10);
  const [tipo, setTipo] = useState("suma");
  const [valorSuma, setValorSuma] = useState(7);
  const [valorParidad, setValorParidad] = useState("par");
  const [resultado, setResultado] = useState(null);

  const valorActual = tipo === "suma" ? valorSuma : valorParidad;

  async function jugar() {
    try {
      const r = await api("/api/dados/jugar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ apuesta: Number(apuesta), tipo, valor: valorActual }),
      });
      onSaldoActualizado(r.saldo);
      setResultado({
        texto: `Salió ${r.dado1} + ${r.dado2} = ${r.suma}. ${r.gano ? "¡Ganaste!" : "Perdiste."} (${r.ganancia >= 0 ? "+" : ""}${r.ganancia})`,
        gano: r.gano,
      });
    } catch (e) {
      setResultado({ texto: e.message, gano: false });
    }
  }

  return (
    <section className="tab-panel">
      <h2>Dados</h2>
      <div className="form-fila">
        <label>
          Apuesta
          <input type="number" min="1" value={apuesta} onChange={(e) => setApuesta(e.target.value)} />
        </label>
        <label>
          Tipo
          <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
            <option value="suma">Suma exacta</option>
            <option value="par_impar">Par / Impar</option>
          </select>
        </label>
        <label>
          Valor
          {tipo === "suma" ? (
            <select value={valorSuma} onChange={(e) => setValorSuma(e.target.value)}>
              {SUMAS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          ) : (
            <select value={valorParidad} onChange={(e) => setValorParidad(e.target.value)}>
              <option value="par">Par</option>
              <option value="impar">Impar</option>
            </select>
          )}
        </label>
        <button onClick={jugar}>Tirar 🎲</button>
      </div>
      {resultado && (
        <p className={`resultado ${resultado.gano ? "gano" : "perdio"}`}>{resultado.texto}</p>
      )}
    </section>
  );
}
