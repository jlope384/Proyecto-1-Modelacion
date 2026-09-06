import { useMemo, useState } from "react";
import { api } from "../api.js";
import { useToast } from "../hooks/useToast.js";
import Toast from "./Toast.jsx";

// Orden físico real de los números en el disco de una ruleta europea.
const NUMEROS_DISCO = [
  0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24,
  16, 33, 1, 20, 14, 31, 9, 22, 18, 29, 7, 28, 12, 35, 3, 26,
];
const NUM_ROJOS = new Set([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]);
const PASO_GRADOS = 360 / NUMEROS_DISCO.length;
const COLOR_HEX = { rojo: "#a3312f", negro: "#161616", verde: "#1f6b45" };
const FICHAS = [
  { valor: 1, clase: "rl-ficha--roja" },
  { valor: 5, clase: "rl-ficha--azul" },
  { valor: 10, clase: "rl-ficha--naranja" },
  { valor: 25, clase: "rl-ficha--morada" },
  { valor: 100, clase: "rl-ficha--dorada" },
];

function colorDe(numero) {
  if (numero === 0) return "verde";
  return NUM_ROJOS.has(numero) ? "rojo" : "negro";
}

function anguloParaNumero(numero) {
  const indice = NUMEROS_DISCO.indexOf(numero);
  return indice * PASO_GRADOS + PASO_GRADOS / 2;
}

// El disco se pinta con un único conic-gradient: 37 cuñas reales, sin recortes manuales.
const GRADIENTE_DISCO = `conic-gradient(from 0deg, ${NUMEROS_DISCO.map((n, i) => {
  const desde = (i * PASO_GRADOS).toFixed(3);
  const hasta = ((i + 1) * PASO_GRADOS).toFixed(3);
  return `${COLOR_HEX[colorDe(n)]} ${desde}deg ${hasta}deg`;
}).join(", ")})`;

export default function Ruleta({ onSaldoActualizado }) {
  const [apuesta, setApuesta] = useState(10);
  const [tipo, setTipo] = useState("color");
  const [valorColor, setValorColor] = useState("rojo");
  const [valorParidad, setValorParidad] = useState("par");
  const [valorNumero, setValorNumero] = useState(7);
  const [resultado, mostrarResultado] = useToast();
  const [historial, setHistorial] = useState([]);
  const [girando, setGirando] = useState(false);
  const [anguloBola, setAnguloBola] = useState(0);

  const valorActual =
    tipo === "color" ? valorColor : tipo === "paridad" ? valorParidad : valorNumero;

  const numeros = useMemo(
    () => NUMEROS_DISCO.map((n) => ({ n, angulo: anguloParaNumero(n), color: colorDe(n) })),
    []
  );

  async function jugar() {
    if (girando) return;
    setGirando(true);
    try {
      const r = await api("/api/ruleta/jugar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ apuesta: Number(apuesta), tipo, valor: valorActual }),
      });

      // Deja girar la rueda un momento antes de frenar exactamente en el número real.
      setTimeout(() => {
        setAnguloBola((a) => a - (360 * 4 + anguloParaNumero(r.numero)));
        setGirando(false);
        onSaldoActualizado(r.saldo);
        mostrarResultado(
          `Salió ${r.numero} (${r.color}). ${r.gano ? "¡Ganaste!" : "Perdiste."} (${r.ganancia >= 0 ? "+" : ""}${r.ganancia})`,
          r.gano ? "gano" : "perdio"
        );
        setHistorial((h) => [{ numero: r.numero, color: r.color }, ...h].slice(0, 14));
      }, 1500);
    } catch (e) {
      setGirando(false);
      mostrarResultado(e.message, "perdio");
    }
  }

  return (
    <section className="tab-panel">
      <h2>Ruleta europea (0-36)</h2>

      <div className="rl-mesa">
        <div className="rl-rueda">
          <div className={`rl-disco ${girando ? "rl-disco--girando" : ""}`} style={{ background: GRADIENTE_DISCO }}>
            {numeros.map(({ n, angulo, color }) => (
              <span key={n} className="rl-numero-slot" style={{ transform: `rotate(${angulo}deg)` }}>
                <span className={`rl-numero rl-numero--${color}`}>{n}</span>
              </span>
            ))}
            <span className="rl-manivela">
              <span className="rl-manivela-brazo" />
              <span className="rl-manivela-extremo rl-manivela-extremo--izq" />
              <span className="rl-manivela-extremo rl-manivela-extremo--der" />
            </span>
          </div>
          <div className="rl-borde" />
          <div
            className={`rl-bola-pista ${girando ? "rl-bola-pista--girando" : ""}`}
            style={girando ? undefined : { transform: `rotate(${anguloBola}deg)` }}
          >
            <span className="rl-bola" />
          </div>
          <div className="rl-eje" />
        </div>

        <div className="rl-panel-lateral">
          {historial.length > 0 && (
            <div className="rl-ticker">
              {historial.map((h, i) => (
                <span key={i} className={`rl-ticker-num rl-ticker-num--${h.color}`}>
                  {h.numero}
                </span>
              ))}
            </div>
          )}

          <div className="rl-fichas">
            {FICHAS.map((f) => (
              <button
                key={f.valor}
                type="button"
                className={`rl-ficha ${f.clase} ${Number(apuesta) === f.valor ? "rl-ficha--activa" : ""}`}
                onClick={() => setApuesta(f.valor)}
                aria-pressed={Number(apuesta) === f.valor}
              >
                {f.valor}
              </button>
            ))}
          </div>

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
            <button className="boton-primario" onClick={jugar} disabled={girando}>
              {girando ? "Girando..." : "Girar"}
            </button>
          </div>
        </div>
      </div>
      <Toast resultado={resultado} />
    </section>
  );
}
