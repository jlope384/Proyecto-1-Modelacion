const TABS = [
  { id: "piso", label: "El piso" },
  { id: "ruleta", label: "Ruleta" },
  { id: "dados", label: "Dados" },
  { id: "tragamonedas", label: "Tragamonedas" },
  { id: "blackjack", label: "Blackjack" },
  { id: "carreras", label: "Carreras" },
  { id: "poker", label: "Póker" },
  { id: "simulacion", label: "Simulación" },
  { id: "modelos", label: "La casa por dentro" },
];

export default function Tabs({ activo, onCambiar }) {
  return (
    <nav className="tabs">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          className={`tab-btn ${activo === tab.id ? "activo" : ""}`}
          onClick={() => onCambiar(tab.id)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  );
}
