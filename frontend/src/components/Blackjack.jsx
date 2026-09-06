import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useToast } from "../hooks/useToast.js";
import Toast from "./Toast.jsx";
import Carta, { paloPorIndice } from "./Carta.jsx";

const TIPO_TOAST = {
  gana: "gano",
  blackjack: "gano",
  dealer_se_paso: "gano",
  pierde: "perdio",
  se_paso: "perdio",
  empate: "empate",
};

function Mano({ titulo, cartas, total, blanda, oculta }) {
  return (
    <div className="bj-mano">
      <div className="bj-mano-titulo">
        {titulo}
        {!oculta && <span className="bj-total">{total}{blanda ? " (blanda)" : ""}</span>}
      </div>
      <div className="bj-cartas">
        {cartas.map((c, i) => (
          <Carta key={i} rango={c === "?" ? undefined : c} palo={paloPorIndice(i)} oculta={c === "?"} />
        ))}
      </div>
    </div>
  );
}

export default function Blackjack({ onSaldoActualizado }) {
  const [estado, setEstado] = useState(null);
  const [apuesta, setApuesta] = useState(10);
  const [cargando, setCargando] = useState(false);
  const [resultado, mostrarResultado] = useToast();

  useEffect(() => {
    api("/api/blackjack/estado").then((r) => {
      setEstado(r);
      onSaldoActualizado(r.saldo);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function llamar(ruta, cuerpo) {
    setCargando(true);
    try {
      const r = await api(ruta, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: cuerpo ? JSON.stringify(cuerpo) : undefined,
      });
      setEstado(r);
      onSaldoActualizado(r.saldo);
      if (r.resultado) {
        mostrarResultado(r.mensaje, TIPO_TOAST[r.resultado] ?? "empate");
      }
    } catch (e) {
      mostrarResultado(e.message, "perdio");
    } finally {
      setCargando(false);
    }
  }

  if (!estado) return null;

  const manoLista = estado.mano_jugador && estado.mano_jugador.length > 0;

  return (
    <section className="tab-panel">
      <h2>Blackjack</h2>
      <p className="ayuda">{estado.mensaje}</p>

      <div className="bj-mesa">
        {manoLista && (
          <>
            <Mano
              titulo="Dealer"
              cartas={estado.mano_dealer}
              total={estado.total_dealer}
              oculta={estado.carta_dealer_oculta}
            />
            <Mano
              titulo="Tu mano"
              cartas={estado.mano_jugador}
              total={estado.total_jugador}
              blanda={estado.mano_jugador_blanda}
            />
          </>
        )}
      </div>

      {!estado.en_juego && (
        <div className="form-fila">
          <label>
            Apuesta
            <input
              type="number"
              min="1"
              value={apuesta}
              onChange={(e) => setApuesta(e.target.value)}
            />
          </label>
          <button
            className="boton-primario"
            disabled={cargando}
            onClick={() => llamar("/api/blackjack/nueva", { apuesta: Number(apuesta) })}
          >
            {manoLista ? "Repartir de nuevo" : "Repartir"}
          </button>
        </div>
      )}

      {estado.en_juego && (
        <div className="form-fila">
          <button className="boton-primario" disabled={cargando} onClick={() => llamar("/api/blackjack/pedir")}>
            Pedir
          </button>
          <button className="boton-primario" disabled={cargando} onClick={() => llamar("/api/blackjack/plantarse")}>
            Plantarse
          </button>
          {estado.puede_doblar && (
            <button className="boton-primario" disabled={cargando} onClick={() => llamar("/api/blackjack/doblar")}>
              Doblar
            </button>
          )}
        </div>
      )}

      <Toast resultado={resultado} />
    </section>
  );
}
