// Piezas comunes del panel: tarjetas, estadísticas, etiquetas de procedencia y veredictos.
import { useEffect, useState } from "react";
import { api } from "../api.js";

export const PROCEDENCIA = {
  real: { cls: "c-real", t: "Real observado" },
  publico: { cls: "c-pub", t: "Público de referencia" },
  estimado: { cls: "c-est", t: "Estimado" },
  sintetico: { cls: "c-sin", t: "Sintético" },
};

export function Etiqueta({ tipo, children }) {
  const p = PROCEDENCIA[tipo] || PROCEDENCIA.estimado;
  return <span className={`chip ${p.cls}`}>{children || p.t}</span>;
}

export function Card({ titulo, extra, pie, children, className = "", style, cuerpo = true, ...rest }) {
  return (
    <section className={`card ${className}`} style={style} {...rest}>
      {(titulo || extra) && (
        <div className="ch">
          <span>{titulo}</span>
          {extra}
        </div>
      )}
      {cuerpo ? <div className="cb">{children}</div> : children}
      {pie && <div className="cf">{pie}</div>}
    </section>
  );
}

export function Stat({ l, v, u, s, chip }) {
  return (
    <div className="stat">
      <div className="l">{l}</div>
      <div className="v">
        {v}
        {u && <small>{u}</small>}
      </div>
      <div className="s">
        {s && <span>{s}</span>}
        {chip}
      </div>
    </div>
  );
}

const ICONO_OK = <path d="M4 12.5l5 5L20 6.5" className="ic" />;
const ICONO_NO = <path d="M5 5l14 14M19 5L5 19" className="ic" />;

export function Veredicto({ ok, textoOk = "APROBADO", textoNo = "FALLADO" }) {
  return (
    <span className={`vd ${ok ? "vok" : "vno"}`}>
      <svg width="14" height="14" viewBox="0 0 24 24" aria-hidden="true">
        {ok ? ICONO_OK : ICONO_NO}
      </svg>
      {ok ? textoOk : textoNo}
    </span>
  );
}

export function Aviso({ ok, titulo, children }) {
  return (
    <div className={ok ? "big" : "warn"}>
      <svg width="40" height="40" viewBox="0 0 24 24" aria-hidden="true" style={{ flex: "none" }}>
        {ok ? <path d="M4 12.5l5 5L20 6.5" className="ic" style={{ strokeWidth: 2.2 }} /> : ICONO_NO}
      </svg>
      <div>
        <b>{titulo}</b>
        <span>{children}</span>
      </div>
    </div>
  );
}

export function Cargando({ texto = "Cargando…" }) {
  return (
    <div className="card">
      <div className="cb why" role="status">
        {texto}
      </div>
    </div>
  );
}

export function ErrorCaja({ error }) {
  return (
    <div className="warn" role="alert">
      <svg width="40" height="40" viewBox="0 0 24 24" aria-hidden="true" style={{ flex: "none" }}>
        {ICONO_NO}
      </svg>
      <div>
        <b>NO SE PUDIERON CARGAR LOS DATOS</b>
        <span>{error}</span>
      </div>
    </div>
  );
}

/** GET a la API con estado de carga y error. */
export function useApi(ruta) {
  const [estado, setEstado] = useState({ datos: null, error: null, cargando: true });
  useEffect(() => {
    let vivo = true;
    setEstado({ datos: null, error: null, cargando: true });
    api(ruta)
      .then((d) => vivo && setEstado({ datos: d, error: null, cargando: false }))
      .catch((e) => vivo && setEstado({ datos: null, error: e.message, cargando: false }));
    return () => {
      vivo = false;
    };
  }, [ruta]);
  return estado;
}

/** Envuelve una pantalla que depende de un GET: muestra carga o error en vez de quedar en blanco. */
export function ConDatos({ ruta, children }) {
  const { datos, error, cargando } = useApi(ruta);
  if (cargando) return <Cargando />;
  if (error) return <ErrorCaja error={error} />;
  return children(datos);
}
