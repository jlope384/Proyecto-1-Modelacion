import { useState } from "react";
import { api } from "../api.js";
import { nextRot } from "../utils/rotacion.js";
import { useToast } from "../hooks/useToast.js";
import Toast from "./Toast.jsx";

const SUMAS = Array.from({ length: 11 }, (_, i) => i + 2); // 2..12

// Caras opuestas suman 7: front=1, back=6, right=2, left=5, top=3, bottom=4.
const PUNTOS_ACTIVOS = {
  1: [5],
  2: [1, 9],
  3: [1, 5, 9],
  4: [1, 3, 7, 9],
  5: [1, 3, 5, 7, 9],
  6: [1, 3, 4, 6, 7, 9],
};

// Rotación que trae cada cara al frente (inversa de la transform propia de esa cara).
const ROT_BASE = {
  1: { x: 0, y: 0 },
  2: { x: 0, y: -90 },
  3: { x: -90, y: 0 },
  4: { x: 90, y: 0 },
  5: { x: 0, y: 90 },
  6: { x: 180, y: 0 },
};

function Cara({ valor, clase }) {
  return (
    <div className={`dado-cara ${clase}`}>
      {Array.from({ length: 9 }, (_, i) => (
        <span
          key={i}
          className="dado-punto"
          style={{ opacity: PUNTOS_ACTIVOS[valor].includes(i + 1) ? 1 : 0 }}
        />
      ))}
    </div>
  );
}

function Dado({ rot, girando }) {
  return (
    <div className="dado-perspectiva">
      <div
        className={`dado-cubo ${girando ? "dado-cubo--girando" : ""}`}
        style={girando ? undefined : { transform: `rotateX(${rot.x}deg) rotateY(${rot.y}deg)` }}
      >
        <Cara valor={1} clase="dado-cara--front" />
        <Cara valor={6} clase="dado-cara--back" />
        <Cara valor={2} clase="dado-cara--right" />
        <Cara valor={5} clase="dado-cara--left" />
        <Cara valor={3} clase="dado-cara--top" />
        <Cara valor={4} clase="dado-cara--bottom" />
      </div>
    </div>
  );
}

export default function Dados({ onSaldoActualizado }) {
  const [apuesta, setApuesta] = useState(10);
  const [tipo, setTipo] = useState("suma");
  const [valorSuma, setValorSuma] = useState(7);
  const [valorParidad, setValorParidad] = useState("par");
  const [resultado, mostrarResultado] = useToast();
  const [girando, setGirando] = useState(false);
  const [rot1, setRot1] = useState({ x: 0, y: 0 });
  const [rot2, setRot2] = useState({ x: 0, y: 0 });

  const valorActual = tipo === "suma" ? valorSuma : valorParidad;

  async function jugar() {
    setGirando(true);
    try {
      const [r] = await Promise.all([
        api("/api/dados/jugar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ apuesta: Number(apuesta), tipo, valor: valorActual }),
        }),
        new Promise((res) => setTimeout(res, 650)),
      ]);
      setRot1((prev) => ({ x: nextRot(prev.x, ROT_BASE[r.dado1].x), y: nextRot(prev.y, ROT_BASE[r.dado1].y) }));
      setRot2((prev) => ({ x: nextRot(prev.x, ROT_BASE[r.dado2].x), y: nextRot(prev.y, ROT_BASE[r.dado2].y) }));
      setGirando(false);
      onSaldoActualizado(r.saldo);
      setTimeout(() => {
        mostrarResultado(
          `Salió ${r.dado1} + ${r.dado2} = ${r.suma}. ${r.gano ? "¡Ganaste!" : "Perdiste."} (${r.ganancia >= 0 ? "+" : ""}${r.ganancia})`,
          r.gano ? "gano" : "perdio"
        );
      }, 900);
    } catch (e) {
      setGirando(false);
      mostrarResultado(e.message, "perdio");
    }
  }

  return (
    <section className="tab-panel">
      <h2>Dados</h2>
      <div className="dados-mesa">
        <Dado rot={rot1} girando={girando} />
        <Dado rot={rot2} girando={girando} />
      </div>
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
        <button className="boton-primario" onClick={jugar} disabled={girando}>
          {girando ? "Tirando…" : "Tirar"}
        </button>
      </div>
      <Toast resultado={resultado} />
    </section>
  );
}
