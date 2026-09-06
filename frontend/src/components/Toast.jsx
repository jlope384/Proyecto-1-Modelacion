function IconoCheck() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22">
      <path d="M5 13l4 4L19 7" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function IconoCruz() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22">
      <path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

function IconoIgual() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22">
      <path d="M5 9h14M5 15h14" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
    </svg>
  );
}

const ICONOS = { gano: IconoCheck, perdio: IconoCruz, empate: IconoIgual };

export default function Toast({ resultado }) {
  if (!resultado) return null;
  const Icono = ICONOS[resultado.tipo] ?? IconoCruz;
  return (
    <div className="toast-overlay">
      <div key={resultado.id} className={`toast toast--${resultado.tipo}`}>
        <span className="toast-icono">
          <Icono />
        </span>
        <span>{resultado.texto}</span>
      </div>
    </div>
  );
}
