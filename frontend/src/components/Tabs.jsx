const TABS = [
  { id: "ruleta", label: "Ruleta" },
  { id: "dados", label: "Dados" },
  { id: "tragamonedas", label: "Tragamonedas" },
  { id: "simulacion", label: "Simulación" },
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
