const SUIT_PATHS = {
  picas: "M12 2C7 7 2 11 2 15a5 5 0 0 0 8.5 3.6c-.3 1.7-1 3-2 4.4h7c-1-1.4-1.7-2.7-2-4.4A5 5 0 0 0 22 15c0-4-5-8-10-13z",
  corazones:
    "M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z",
  diamantes: "M12 2L22 12L12 22L2 12Z",
  treboles:
    "M12 2a3.5 3.5 0 0 1 3.4 4.3A3.5 3.5 0 1 1 17 12.8c-.6.9-1.5 1.5-2.6 1.7.4 1.6 1.2 3 2.3 4.3.4.5 0 1.2-.6 1.2H8c-.6 0-1-.7-.6-1.2 1.1-1.3 1.9-2.7 2.3-4.3a4 4 0 0 1-2.6-1.7A3.5 3.5 0 1 1 8.6 6.3 3.5 3.5 0 0 1 12 2z",
};

const PALOS_ROJOS = new Set(["corazones", "diamantes"]);
const CICLO_PALOS = ["picas", "corazones", "treboles", "diamantes"];

// Blackjack no registra palo (solo rango); se asigna uno decorativo estable por posición.
export function paloPorIndice(i) {
  return CICLO_PALOS[i % 4];
}

function IconoPalo({ palo, className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden="true">
      <path d={SUIT_PATHS[palo]} />
    </svg>
  );
}

export default function Carta({ rango, palo, oculta = false, animar = true, tamano }) {
  const claseAnim = animar ? "carta--repartida" : "";
  const claseTamano = tamano ? `carta--${tamano}` : "";

  if (oculta || rango === "?" || !rango) {
    return (
      <div className={`carta carta--oculta ${claseAnim} ${claseTamano}`} aria-label="Carta oculta">
        <div className="carta-dorso" />
      </div>
    );
  }

  const roja = PALOS_ROJOS.has(palo);
  return (
    <div
      className={`carta ${roja ? "carta--roja" : "carta--negra"} ${claseAnim} ${claseTamano}`}
      aria-label={`${rango} de ${palo}`}
    >
      <span className="carta-rango carta-rango--tl">{rango}</span>
      <IconoPalo palo={palo} className="carta-palo carta-palo--centro" />
      <span className="carta-rango carta-rango--br">{rango}</span>
    </div>
  );
}
