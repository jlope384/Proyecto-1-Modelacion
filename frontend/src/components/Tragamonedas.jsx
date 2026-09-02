import { useState } from "react";
import { api } from "../api.js";

export default function Tragamonedas({ onSaldoActualizado }) {
  const [apuesta, setApuesta] = useState(10);
  const [reels, setReels] = useState([]);
  const [resultado, setResultado] = useState(null);

  async function jugar() {
    try {
      const r = await api("/api/tragamonedas/jugar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ apuesta: Number(apuesta) }),
      });
      onSaldoActualizado(r.saldo);
      setReels(r.reels);
      setResultado({
        texto: `${r.gano ? "¡Ganaste!" : "Perdiste."} (${r.ganancia >= 0 ? "+" : ""}${r.ganancia})`,
        gano: r.gano,
      });
    } catch (e) {
      setResultado({ texto: e.message, gano: false });
    }
  }

  return (
    <section className="tab-panel">
      <h2>Tragamonedas</h2>
      <div className="form-fila">
        <label>
          Apuesta
          <input type="number" min="1" value={apuesta} onChange={(e) => setApuesta(e.target.value)} />
        </label>
        <button onClick={jugar}>Girar 🎰</button>
      </div>
      {reels.length > 0 && <p className="reels">{reels.join(" ")}</p>}
      {resultado && (
        <p className={`resultado ${resultado.gano ? "gano" : "perdio"}`}>{resultado.texto}</p>
      )}
    </section>
  );
}
