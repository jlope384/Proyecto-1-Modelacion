import { useState } from "react";
import { api } from "../api.js";

export default function Ruleta({ onSaldoActualizado }) {
  const [apuesta, setApuesta] = useState(10);
  const [tipo, setTipo] = useState("color");
  const [valorColor, setValorColor] = useState("rojo");
  const [valorParidad, setValorParidad] = useState("par");
  const [valorNumero, setValorNumero] = useState(7);
  const [resultado, setResultado] = useState(null);

  const valorActual =
    tipo === "color" ? valorColor : tipo === "paridad" ? valorParidad : valorNumero;

  async function jugar() {
    try {
      const r = await api("/api/ruleta/jugar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ apuesta: Number(apuesta), tipo, valor: valorActual }),
      });
      onSaldoActualizado(r.saldo);
      setResultado({
        texto: `Salió ${r.numero} (${r.color}). ${r.gano ? "¡Ganaste!" : "Perdiste."} (${r.ganancia >= 0 ? "+" : ""}${r.ganancia})`,
        gano: r.gano,
      });
    } catch (e) {
      setResultado({ texto: e.message, gano: false });
    }
  }

  return (
    <section className="tab-panel">
      <h2>Ruleta europea (0-36)</h2>
      <div className="form-fila">
        <label>
          Apuesta
          <input type="number" min="1" value={apuesta} onChange={(e) => setApuesta(e.target.value)} />
        </label>
        <label>
          Tipo
          <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
            <option value="color">Color</option>
            <option value="paridad">Par / Impar</option>
            <option value="numero">Número exacto</option>
          </select>
        </label>
        <label>
          Valor
          {tipo === "color" && (
            <select value={valorColor} onChange={(e) => setValorColor(e.target.value)}>
              <option value="rojo">Rojo</option>
              <option value="negro">Negro</option>
            </select>
          )}
          {tipo === "paridad" && (
            <select value={valorParidad} onChange={(e) => setValorParidad(e.target.value)}>
              <option value="par">Par</option>
              <option value="impar">Impar</option>
            </select>
          )}
          {tipo === "numero" && (
            <input
              type="number"
              min="0"
              max="36"
              value={valorNumero}
              onChange={(e) => setValorNumero(e.target.value)}
            />
          )}
        </label>
        <button onClick={jugar}>Girar 🎡</button>
      </div>
      {resultado && (
        <p className={`resultado ${resultado.gano ? "gano" : "perdio"}`}>{resultado.texto}</p>
      )}
    </section>
  );
}
