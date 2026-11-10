import { useState } from "react";
import logo from "./assets/logo.jpg";
import { useApi } from "./components/ui.jsx";
import Armar from "./pages/Armar.jsx";
import DatosReales from "./pages/DatosReales.jsx";
import Escenarios from "./pages/Escenarios.jsx";
import Fuentes from "./pages/Fuentes.jsx";
import Optimizacion from "./pages/Optimizacion.jsx";
import Piso from "./pages/Piso.jsx";
import Validacion from "./pages/Validacion.jsx";

const TABS = [
  { id: "piso", label: "El piso" },
  { id: "maq", label: "Armar piso" },
  { id: "datos", label: "Datos reales" },
  { id: "opt", label: "Optimización" },
  { id: "esc", label: "Escenarios" },
  { id: "val", label: "Validación" },
  { id: "fuentes", label: "Fuentes" },
];

const HEROES = {
  piso: {
    eyebrow: "SIMULACIÓN · UN DÍA DE OPERACIÓN",
    title: "EL PISO DEL CASINO",
    lead: "Elige mesas, máquinas y condiciones de llegada, simula un día completo y mira el ingreso, la espera, el abandono y la utilización.",
  },
  maq: {
    eyebrow: "UN PISO, ÁREA FIJA",
    title: "ARMA EL PISO",
    lead: "Reparte el área entre los cuatro juegos. Cada mesa ocupa el área de varias máquinas: para ganar en un juego hay que sacrificar otros.",
  },
  datos: {
    eyebrow: "REFERENCIA · MUNDO REAL",
    title: "DATOS REALES CONTRA SIMULACIÓN",
    lead: "Nevada 2024 y Grand Korea Leisure 2024, datos que no se usaron para calibrar. Cada cifra declara de dónde viene.",
  },
  opt: {
    eyebrow: "ALGORITMO GENÉTICO CON RESTRICCIONES",
    title: "OPTIMIZACIÓN DEL REPARTO",
    lead: "Resultado precalculado del GA: convergencia, reparto mejorado y verificación por código de la restricción de área.",
  },
  esc: {
    eyebrow: "100 Y 30 RÉPLICAS · IC DE 95 %",
    title: "ESCENARIOS Y SENSIBILIDAD",
    lead: "Base, mejorada y variaciones de los supuestos con las mismas semillas. Toda mejora mostrada es simulada, no observada.",
  },
  val: {
    eyebrow: "PRUEBAS DE CORRECCIÓN",
    title: "VALIDACIÓN DEL MODELO",
    lead: "Generador de números, distribución de cada juego, ley de Little, conservación de clientes y hold por juego.",
  },
  fuentes: {
    eyebrow: "TRANSPARENCIA",
    title: "FUENTES Y REPRODUCCIÓN",
    lead: "Datasets usados, supuestos del modelo, uso de inteligencia artificial y comandos para correr todo desde un entorno limpio.",
  },
};

export default function App() {
  const [tab, setTab] = useState("piso");
  const config = useApi("/api/config");
  const pos = TABS.findIndex((t) => t.id === tab);
  const hero = HEROES[tab];

  return (
    <div className="app">
      <div className="stage">
        <div className="top">
          <div className="brand">
            <div className="lgbox">
              <img src={logo} alt="Logo del casino" />
            </div>
            <div>
              <b>EL PISO</b>
              <small>CASINO · PANEL DE ANÁLISIS</small>
            </div>
          </div>
          <nav className="nav" aria-label="Secciones">
            {TABS.map((t) => (
              <button key={t.id} className={tab === t.id ? "tab on" : "tab"} aria-pressed={tab === t.id} onClick={() => setTab(t.id)}>
                {t.label}
              </button>
            ))}
          </nav>
        </div>

        <header className="hero">
          <div className={`herobg p${pos}`} />
          <div className="herodk" />
          <img className="logoart" src={logo} alt="" />
          <div className="hero-in">
            <div className="eyebrow">{hero.eyebrow}</div>
            <h1 className="h1">{hero.title}</h1>
            <p className="lead">{hero.lead}</p>
          </div>
        </header>
      </div>

      <div className="body">
        <div className={`pagebg b${pos}`} />
        <div className="pagedk" />
        <main className="wrap">
          {tab === "piso" && <Piso config={config} />}
          {tab === "maq" && <Armar config={config} />}
          {tab === "datos" && <DatosReales />}
          {tab === "opt" && <Optimizacion />}
          {tab === "esc" && <Escenarios config={config} />}
          {tab === "val" && <Validacion />}
          {tab === "fuentes" && <Fuentes />}
        </main>
      </div>

      <footer className="foot">Proyecto 2 · CC3074 Modelización y Simulación · UVG 2026</footer>
    </div>
  );
}
