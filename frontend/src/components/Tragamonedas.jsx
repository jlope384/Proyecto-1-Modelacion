import { useState } from "react";
import { api } from "../api.js";
import { nextRot } from "../utils/rotacion.js";
import { useToast } from "../hooks/useToast.js";
import Toast from "./Toast.jsx";

// Debe coincidir con el orden de SIMBOLOS en backend/casino/tragamonedas.py.
const SIMBOLOS = ["🍒", "🍋", "🔔", "⭐", "7️⃣"];
const RADIO = 62;

function IconoCereza() {
  return (
    <svg viewBox="0 0 24 24" width="34" height="34">
      <path d="M12 3c1 2 2 4 2 6" stroke="#4a7c3f" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      <path d="M14 4c1.4-1.1 2.6-1.4 3.6-1" stroke="#4a7c3f" strokeWidth="1.6" fill="none" strokeLinecap="round" />
      <circle cx="8.5" cy="16.5" r="4.3" fill="#c0392b" />
      <circle cx="15.5" cy="17.5" r="4.3" fill="#a3312f" />
    </svg>
  );
}

function IconoLimon() {
  return (
    <svg viewBox="0 0 24 24" width="34" height="34">
      <ellipse cx="12" cy="12" rx="8.2" ry="6.4" fill="#e8c93a" transform="rotate(-25 12 12)" />
      <path d="M3.5 8.5c-1-1-2-1-3-.3" stroke="#e8c93a" strokeWidth="2" fill="none" strokeLinecap="round" />
      <path d="M20.5 15.5c1 1 2 1 3 .3" stroke="#e8c93a" strokeWidth="2" fill="none" strokeLinecap="round" />
    </svg>
  );
}

function IconoCampana() {
  return (
    <svg viewBox="0 0 24 24" width="34" height="34">
      <rect x="10.5" y="1.5" width="3" height="2.5" rx="1" fill="#d4af37" />
      <path d="M12 3.5a5.5 5.5 0 0 0-5.5 5.5c0 5.2-2 6.2-2 7.2h15c0-1-2-2-2-7.2A5.5 5.5 0 0 0 12 3.5z" fill="#d4af37" />
      <path d="M9 17.2a3 3 0 0 0 6 0z" fill="#8a6d1c" />
    </svg>
  );
}

function IconoEstrella() {
  return (
    <svg viewBox="0 0 24 24" width="34" height="34">
      <path
        d="M12 2l2.9 6.6 7.1.7-5.4 4.7 1.6 7-6.2-3.8-6.2 3.8 1.6-7L2 9.3l7.1-.7z"
        fill="#d4af37"
      />
    </svg>
  );
}

function IconoSiete() {
  return <span className="tm-siete">7</span>;
}

const ICONOS = [IconoCereza, IconoLimon, IconoCampana, IconoEstrella, IconoSiete];

function rotBase(indice) {
  return (((-72 * indice) % 360) + 360) % 360;
}

function Rodillo({ angulo, girando }) {
  return (
    <div className="tm-ventana">
      <div
        className={`tm-tambor ${girando ? "tm-tambor--girando" : ""}`}
        style={girando ? undefined : { transform: `rotateX(${angulo}deg)` }}
      >
        {ICONOS.map((Icono, i) => (
          <div key={i} className="tm-cara" style={{ transform: `rotateX(${i * 72}deg) translateZ(${RADIO}px)` }}>
            <Icono />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Tragamonedas({ onSaldoActualizado }) {
  const [apuesta, setApuesta] = useState(10);
  const [angulos, setAngulos] = useState([0, 0, 0]);
  const [girando, setGirando] = useState(false);
  const [resultado, mostrarResultado] = useToast();

  async function jugar() {
    setGirando(true);
    try {
      const [r] = await Promise.all([
        api("/api/tragamonedas/jugar", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ apuesta: Number(apuesta) }),
        }),
        new Promise((res) => setTimeout(res, 650)),
      ]);
      setAngulos((prev) =>
        prev.map((a, i) => nextRot(a, rotBase(SIMBOLOS.indexOf(r.reels[i]))))
      );
      setGirando(false);
      onSaldoActualizado(r.saldo);
      setTimeout(() => {
        const tipo = r.gano ? "gano" : r.ganancia === 0 ? "empate" : "perdio";
        const texto = r.gano
          ? `¡Ganaste! (+${r.ganancia})`
          : r.ganancia === 0
          ? "Empate: se devuelve la apuesta."
          : `Perdiste. (${r.ganancia})`;
        mostrarResultado(texto, tipo);
      }, 950);
    } catch (e) {
      setGirando(false);
      mostrarResultado(e.message, "perdio");
    }
  }

  return (
    <section className="tab-panel">
      <h2>Tragamonedas</h2>
      <div className="tm-maquina">
        <div className="tm-cabina">
          <div className="tm-cupula" />
          <div className="tm-marquesina">
            <span className="tm-palo tm-palo--rojo">♦</span>
            <span className="tm-palo tm-palo--negro">♣</span>
            <h3>CASINO</h3>
            <span className="tm-palo tm-palo--negro">♠</span>
            <span className="tm-palo tm-palo--rojo">♥</span>
          </div>
          <div className="tm-pantalla">
            <Rodillo angulo={angulos[0]} girando={girando} />
            <Rodillo angulo={angulos[1]} girando={girando} />
            <Rodillo angulo={angulos[2]} girando={girando} />
          </div>
          <div className="tm-placa">JACKPOT</div>
        </div>
        <button
          onClick={jugar}
          disabled={girando}
          aria-label="Tirar de la palanca para girar"
          className={`tm-palanca ${girando ? "tm-palanca--tirada" : ""}`}
        >
          <span className="tm-palanca-vara" />
          <span className="tm-palanca-bola" />
        </button>
      </div>
      <div className="form-fila">
        <label>
          Apuesta
          <input type="number" min="1" value={apuesta} onChange={(e) => setApuesta(e.target.value)} />
        </label>
        <button className="boton-primario" onClick={jugar} disabled={girando}>
          {girando ? "Girando…" : "Girar"}
        </button>
      </div>
      <Toast resultado={resultado} />
    </section>
  );
}
