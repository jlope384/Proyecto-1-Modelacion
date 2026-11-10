import { useEffect, useState } from "react";
import Header from "./components/Header.jsx";
import Tabs from "./components/Tabs.jsx";
import Piso from "./components/Piso.jsx";
import Ruleta from "./components/Ruleta.jsx";
import Dados from "./components/Dados.jsx";
import Tragamonedas from "./components/Tragamonedas.jsx";
import Blackjack from "./components/Blackjack.jsx";
import Simulacion from "./components/Simulacion.jsx";
import Modelos from "./components/Modelos.jsx";
import { api } from "./api.js";

export default function App() {
  const [saldo, setSaldo] = useState(1000);
  const [tabActivo, setTabActivo] = useState("piso");

  useEffect(() => {
    api("/api/estado").then((r) => setSaldo(r.saldo));
  }, []);

  async function reiniciar() {
    const r = await api("/api/reiniciar", { method: "POST" });
    setSaldo(r.saldo);
  }

  return (
    <>
      <Header saldo={saldo} onReiniciar={reiniciar} />
      <Tabs activo={tabActivo} onCambiar={setTabActivo} />
      <main>
        {tabActivo === "piso" && <Piso />}
        {tabActivo === "ruleta" && <Ruleta onSaldoActualizado={setSaldo} />}
        {tabActivo === "dados" && <Dados onSaldoActualizado={setSaldo} />}
        {tabActivo === "tragamonedas" && <Tragamonedas onSaldoActualizado={setSaldo} />}
        {tabActivo === "blackjack" && <Blackjack onSaldoActualizado={setSaldo} />}
        {tabActivo === "simulacion" && <Simulacion />}
        {tabActivo === "modelos" && <Modelos />}
      </main>
    </>
  );
}
