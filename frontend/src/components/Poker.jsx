import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useToast } from "../hooks/useToast.js";
import Toast from "./Toast.jsx";
import Carta from "./Carta.jsx";

const NOMBRES_CATEGORIA = {
  escalera_color: "Escalera de color",
  poker: "Póker",
  full: "Full house",
  color: "Color",
  escalera: "Escalera",
  trio: "Trío",
  doble_par: "Doble par",
  par: "Par",
  carta_alta: "Carta alta",
};

function Asiento({ fila }) {
  return (
    <div
      className={`pk-asiento ${fila.es_humano ? "pk-asiento--humano" : ""} ${
        fila.en_mano === false ? "pk-asiento--retirado" : ""
      }`}
    >
      <div className="pk-asiento-cartas">
        {fila.cartas?.length
          ? fila.cartas.map((c, i) => (
              <Carta key={i} rango={c === "?" ? undefined : c.rango} palo={c === "?" ? undefined : c.palo} oculta={c === "?"} tamano="chica" />
            ))
          : null}
      </div>
      <div className="pk-asiento-info">
        {fila.boton && <span className="pk-boton">D</span>}
        <span>{fila.es_humano ? "Tú" : `Bot ${fila.asiento}`}</span>
        <span className="pk-stack">{fila.stack.toFixed(0)}</span>
      </div>
      {fila.aportado_calle > 0 && <div className="pk-apuesta-chip">{fila.aportado_calle.toFixed(0)}</div>}
      {fila.all_in && <div className="pk-etiqueta">ALL-IN</div>}
      {fila.categoria_mano && <div className="pk-etiqueta pk-etiqueta--categoria">{NOMBRES_CATEGORIA[fila.categoria_mano] ?? fila.categoria_mano}</div>}
    </div>
  );
}

export default function Poker({ onSaldoActualizado }) {
  const [estado, setEstado] = useState(null);
  const [monto, setMonto] = useState(500);
  const [montoSubida, setMontoSubida] = useState(0);
  const [cargando, setCargando] = useState(false);
  const [resultado, mostrarResultado] = useToast();

  useEffect(() => {
    api("/api/poker/estado").then((r) => {
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
      if (r.motivo_fin) {
        const humano = r.asientos.find((a) => a.es_humano);
        const neto = r.ganancias?.[humano?.asiento];
        mostrarResultado(r.mensaje, neto > 0 ? "gano" : neto < 0 ? "perdio" : "empate");
      }
    } catch (e) {
      mostrarResultado(e.message, "perdio");
    } finally {
      setCargando(false);
    }
  }

  if (!estado) return null;

  if (!estado.sentado) {
    return (
      <section className="tab-panel">
        <h2>Póker (Texas Hold'em)</h2>
        <p className="ayuda">{estado.mensaje}</p>
        <div className="form-fila">
          <label>
            Fichas a comprar
            <input type="number" min="1" value={monto} onChange={(e) => setMonto(e.target.value)} />
          </label>
          <button className="boton-primario" disabled={cargando} onClick={() => llamar("/api/poker/comprar", { monto: Number(monto) })}>
            Sentarse
          </button>
        </div>
        <Toast resultado={resultado} />
      </section>
    );
  }

  const humano = estado.asientos.find((a) => a.es_humano);
  const manoTerminada = estado.mano_en_curso === false;
  const esperandoHumano = estado.mano_en_curso && estado.turno === humano?.asiento;
  const aPagar = humano ? Math.max(0, (estado.apuesta_actual ?? 0) - (humano.aportado_calle ?? 0)) : 0;
  const subidaMinima = (estado.apuesta_actual ?? 0) + (estado.ciega_grande ?? 10);

  return (
    <section className="tab-panel">
      <h2>Póker (Texas Hold'em)</h2>
      <p className="ayuda">{estado.mensaje}</p>

      <div className="pk-mesa">
        {estado.calle && (
          <div className="pk-centro">
            <div className="pk-board">
              {estado.board.map((c, i) => (
                <Carta key={i} rango={c.rango} palo={c.palo} />
              ))}
            </div>
            <div className="pk-bote">Bote: {estado.bote?.toFixed(0)}</div>
          </div>
        )}
        <div className="pk-asientos">
          {estado.asientos.map((a) => (
            <Asiento key={a.asiento} fila={a} />
          ))}
        </div>
      </div>

      {!estado.mano_en_curso && (
        <div className="form-fila">
          <button className="boton-primario" disabled={cargando} onClick={() => llamar("/api/poker/nueva")}>
            {manoTerminada ? "Repartir siguiente mano" : "Repartir mano"}
          </button>
          <button className="boton-secundario" disabled={cargando} onClick={() => llamar("/api/poker/retirarse")}>
            Retirarse de la mesa
          </button>
        </div>
      )}

      {esperandoHumano && (
        <div className="form-fila">
          <button className="boton-primario" disabled={cargando} onClick={() => llamar("/api/poker/accion", { accion: "fold" })}>
            Retirarse
          </button>
          {aPagar <= 0 ? (
            <button className="boton-primario" disabled={cargando} onClick={() => llamar("/api/poker/accion", { accion: "check" })}>
              Pasar
            </button>
          ) : (
            <button className="boton-primario" disabled={cargando} onClick={() => llamar("/api/poker/accion", { accion: "call" })}>
              Igualar ({aPagar.toFixed(0)})
            </button>
          )}
          <label>
            Subir a
            <input
              type="number"
              min={subidaMinima}
              value={montoSubida || subidaMinima}
              onChange={(e) => setMontoSubida(Number(e.target.value))}
            />
          </label>
          <button
            className="boton-primario"
            disabled={cargando}
            onClick={() => llamar("/api/poker/accion", { accion: "raise", monto: montoSubida || subidaMinima })}
          >
            Subir
          </button>
        </div>
      )}

      <Toast resultado={resultado} />
    </section>
  );
}
