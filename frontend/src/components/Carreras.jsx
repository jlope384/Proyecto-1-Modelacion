import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useToast } from "../hooks/useToast.js";
import Toast from "./Toast.jsx";

function IconoCaballo() {
  return (
    <svg viewBox="0 0 100 70" className="cr-caballo-icono" aria-hidden="true" fill="currentColor">
      <polygon points="20,26 6,19 4,28 15,35 21,30" />
      <ellipse cx="42" cy="34" rx="22" ry="12" />
      <polygon points="58,26 78,6 85,10 70,28" />
      <polygon points="63,19 67,9 71,18" />
      <ellipse cx="80" cy="11" rx="7" ry="5.5" />
      <polygon points="82,8 86,1 88,9" />
      <polygon points="56,42 64,42 74,64 66,64" />
      <polygon points="46,42 54,42 54,64 48,64" />
      <polygon points="28,42 36,42 32,64 26,64" />
      <polygon points="18,42 26,42 12,64 6,64" />
    </svg>
  );
}

export default function Carreras({ onSaldoActualizado }) {
  const [estado, setEstado] = useState(null);
  const [apuesta, setApuesta] = useState(50);
  const [caballoElegido, setCaballoElegido] = useState(null);
  const [caballoRedbull, setCaballoRedbull] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [frame, setFrame] = useState(0);
  const [corriendo, setCorriendo] = useState(false);
  const [resultado, mostrarResultado] = useToast();

  useEffect(() => {
    api("/api/carreras/estado").then((r) => {
      setEstado(r);
      onSaldoActualizado(r.saldo);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!corriendo || !estado?.historial) return;
    if (frame >= estado.historial.length - 1) {
      setCorriendo(false);
      const gano = estado.caballo_apostado != null && estado.ganador === estado.caballo_apostado;
      const tipo = estado.caballo_apostado == null ? "empate" : gano ? "gano" : "perdio";
      mostrarResultado(estado.mensaje, tipo);
      return;
    }
    const t = setTimeout(() => setFrame((f) => f + 1), 40);
    return () => clearTimeout(t);
  }, [corriendo, frame, estado, mostrarResultado]);

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
      return r;
    } catch (e) {
      mostrarResultado(e.message, "perdio");
      return null;
    } finally {
      setCargando(false);
    }
  }

  async function nuevaCarrera() {
    setCaballoElegido(null);
    setCaballoRedbull(null);
    setFrame(0);
    setCorriendo(false);
    await llamar("/api/carreras/nueva");
  }

  async function apostar() {
    if (caballoElegido == null) return;
    await llamar("/api/carreras/apostar", { apuesta: Number(apuesta), caballo: caballoElegido });
  }

  async function correr() {
    setFrame(0);
    const r = await llamar("/api/carreras/correr");
    if (r) setCorriendo(true);
  }

  if (!estado) return null;

  if (!estado.hay_carrera) {
    return (
      <section className="tab-panel">
        <h2>Carrera de caballos</h2>
        <p className="ayuda">{estado.mensaje}</p>
        <div className="form-fila">
          <button className="boton-primario" disabled={cargando} onClick={nuevaCarrera}>
            Abrir carrera
          </button>
        </div>
      </section>
    );
  }

  const largo = estado.largo_pista;
  const posiciones = estado.historial ? estado.historial[Math.min(frame, estado.historial.length - 1)] : null;
  const yaAposto = estado.caballo_apostado != null;

  return (
    <section className="tab-panel">
      <h2>Carrera de caballos</h2>
      <p className="ayuda">{estado.mensaje}</p>

      <div className="cr-pista">
        {estado.caballos.map((c, i) => {
          const pct = posiciones ? Math.min(94, (posiciones[i] / largo) * 100) : 0;
          const esGanador = estado.corrida && estado.ganador === c.numero;
          return (
            <div key={c.numero} className="cr-carril">
              <div className="cr-carril-meta">
                #{c.numero} · cuota {c.cuota.toFixed(2)}
                {estado.dato_comprado?.includes(c.numero) && <span className="cr-etiqueta cr-etiqueta--dato">dato</span>}
                {estado.redbull_usado === c.numero && <span className="cr-etiqueta cr-etiqueta--redbull">redbull</span>}
                {c.numero === estado.caballo_apostado && <span className="cr-etiqueta cr-etiqueta--apuesta">tu apuesta</span>}
              </div>
              <div className="cr-carril-pista">
                <div
                  className={`cr-caballo ${esGanador ? "cr-caballo--ganador" : ""}`}
                  style={{ left: `${pct}%` }}
                >
                  <IconoCaballo />
                </div>
                <div className="cr-meta-linea" />
              </div>
            </div>
          );
        })}
      </div>

      {!estado.corrida && !yaAposto && (
        <>
          <div className="form-fila">
            <label>
              Caballo
              <select
                value={caballoElegido ?? ""}
                onChange={(e) => setCaballoElegido(Number(e.target.value))}
              >
                <option value="" disabled>
                  Elegir
                </option>
                {estado.caballos.map((c) => (
                  <option key={c.numero} value={c.numero}>
                    #{c.numero} (cuota {c.cuota.toFixed(2)})
                  </option>
                ))}
              </select>
            </label>
            <label>
              Apuesta
              <input type="number" min="1" value={apuesta} onChange={(e) => setApuesta(e.target.value)} />
            </label>
            <button className="boton-primario" disabled={cargando || caballoElegido == null} onClick={apostar}>
              Apostar
            </button>
          </div>

          <div className="form-fila">
            <button
              className="boton-primario"
              disabled={cargando || estado.dato_comprado != null}
              onClick={() => llamar("/api/carreras/soborno/dato")}
            >
              Comprar dato ({estado.costos.dato})
            </button>
            <label>
              Redbull para
              <select
                value={caballoRedbull ?? ""}
                onChange={(e) => setCaballoRedbull(Number(e.target.value))}
              >
                <option value="" disabled>
                  Elegir
                </option>
                {estado.caballos.map((c) => (
                  <option key={c.numero} value={c.numero}>
                    #{c.numero}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="boton-primario"
              disabled={cargando || estado.redbull_usado != null || caballoRedbull == null}
              onClick={() => llamar("/api/carreras/soborno/redbull", { caballo: caballoRedbull })}
            >
              Dar redbull ({estado.costos.redbull})
            </button>
          </div>
        </>
      )}

      {!estado.corrida && (
        <div className="form-fila">
          <button className="boton-primario" disabled={cargando} onClick={correr}>
            Correr carrera
          </button>
        </div>
      )}

      {estado.corrida && !corriendo && (
        <div className="form-fila">
          <button className="boton-primario" disabled={cargando} onClick={nuevaCarrera}>
            Nueva carrera
          </button>
        </div>
      )}

      <Toast resultado={resultado} />
    </section>
  );
}
