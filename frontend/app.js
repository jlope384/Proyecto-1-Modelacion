const saldoSpan = document.getElementById("saldo");

function actualizarSaldo(valor) {
  saldoSpan.textContent = Math.round(valor * 100) / 100;
}

async function api(ruta, opciones) {
  const respuesta = await fetch(ruta, opciones);
  const cuerpo = await respuesta.json();
  if (!respuesta.ok) {
    throw new Error(cuerpo.error || "Error desconocido");
  }
  return cuerpo;
}

async function cargarEstado() {
  const estado = await api("/api/estado");
  actualizarSaldo(estado.saldo);
}

document.getElementById("btn-reiniciar").addEventListener("click", async () => {
  const estado = await api("/api/reiniciar", { method: "POST" });
  actualizarSaldo(estado.saldo);
});

// --- Tabs ---
document.querySelectorAll(".tab-btn").forEach((boton) => {
  boton.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("activo"));
    document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("activo"));
    boton.classList.add("activo");
    document.getElementById(`tab-${boton.dataset.tab}`).classList.add("activo");
  });
});

function mostrarResultado(elemento, texto, gano) {
  elemento.textContent = texto;
  elemento.classList.remove("gano", "perdio");
  elemento.classList.add(gano ? "gano" : "perdio");
}

// --- Ruleta ---
const ruletaTipo = document.getElementById("ruleta-tipo");
const ruletaValorColor = document.getElementById("ruleta-valor-color");
const ruletaValorParidad = document.getElementById("ruleta-valor-paridad");
const ruletaValorNumero = document.getElementById("ruleta-valor-numero");

function actualizarCamposRuleta() {
  ruletaValorColor.hidden = ruletaTipo.value !== "color";
  ruletaValorParidad.hidden = ruletaTipo.value !== "paridad";
  ruletaValorNumero.hidden = ruletaTipo.value !== "numero";
}
ruletaTipo.addEventListener("change", actualizarCamposRuleta);
actualizarCamposRuleta();

function valorRuletaSeleccionado() {
  if (ruletaTipo.value === "color") return ruletaValorColor.value;
  if (ruletaTipo.value === "paridad") return ruletaValorParidad.value;
  return ruletaValorNumero.value;
}

document.getElementById("ruleta-jugar").addEventListener("click", async () => {
  const apuesta = Number(document.getElementById("ruleta-apuesta").value);
  const resultadoEl = document.getElementById("ruleta-resultado");
  try {
    const r = await api("/api/ruleta/jugar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ apuesta, tipo: ruletaTipo.value, valor: valorRuletaSeleccionado() }),
    });
    actualizarSaldo(r.saldo);
    mostrarResultado(
      resultadoEl,
      `Salió ${r.numero} (${r.color}). ${r.gano ? "¡Ganaste!" : "Perdiste."} (${r.ganancia >= 0 ? "+" : ""}${r.ganancia})`,
      r.gano
    );
  } catch (e) {
    mostrarResultado(resultadoEl, e.message, false);
  }
});

// --- Dados ---
const dadosTipo = document.getElementById("dados-tipo");
const dadosValorSuma = document.getElementById("dados-valor-suma");
const dadosValorParidad = document.getElementById("dados-valor-paridad");

for (let suma = 2; suma <= 12; suma++) {
  const opcion = document.createElement("option");
  opcion.value = suma;
  opcion.textContent = suma;
  if (suma === 7) opcion.selected = true;
  dadosValorSuma.appendChild(opcion);
}

function actualizarCamposDados() {
  dadosValorSuma.hidden = dadosTipo.value !== "suma";
  dadosValorParidad.hidden = dadosTipo.value !== "par_impar";
}
dadosTipo.addEventListener("change", actualizarCamposDados);
actualizarCamposDados();

function valorDadosSeleccionado() {
  return dadosTipo.value === "suma" ? dadosValorSuma.value : dadosValorParidad.value;
}

document.getElementById("dados-jugar").addEventListener("click", async () => {
  const apuesta = Number(document.getElementById("dados-apuesta").value);
  const resultadoEl = document.getElementById("dados-resultado");
  try {
    const r = await api("/api/dados/jugar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ apuesta, tipo: dadosTipo.value, valor: valorDadosSeleccionado() }),
    });
    actualizarSaldo(r.saldo);
    mostrarResultado(
      resultadoEl,
      `Salió ${r.dado1} + ${r.dado2} = ${r.suma}. ${r.gano ? "¡Ganaste!" : "Perdiste."} (${r.ganancia >= 0 ? "+" : ""}${r.ganancia})`,
      r.gano
    );
  } catch (e) {
    mostrarResultado(resultadoEl, e.message, false);
  }
});

// --- Tragamonedas ---
document.getElementById("slots-jugar").addEventListener("click", async () => {
  const apuesta = Number(document.getElementById("slots-apuesta").value);
  const reelsEl = document.getElementById("slots-reels");
  const resultadoEl = document.getElementById("slots-resultado");
  try {
    const r = await api("/api/tragamonedas/jugar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ apuesta }),
    });
    actualizarSaldo(r.saldo);
    reelsEl.textContent = r.reels.join(" ");
    mostrarResultado(
      resultadoEl,
      `${r.gano ? "¡Ganaste!" : "Perdiste."} (${r.ganancia >= 0 ? "+" : ""}${r.ganancia})`,
      r.gano
    );
  } catch (e) {
    mostrarResultado(resultadoEl, e.message, false);
  }
});

// --- Simulación ---
const simJuego = document.getElementById("sim-juego");
const simExtraRuleta = document.getElementById("sim-extra-ruleta");
const simExtraDados = document.getElementById("sim-extra-dados");

function actualizarCamposSimulacion() {
  simExtraRuleta.hidden = simJuego.value !== "ruleta";
  simExtraDados.hidden = simJuego.value !== "dados";
}
simJuego.addEventListener("change", actualizarCamposSimulacion);
actualizarCamposSimulacion();

let grafica = null;

document.getElementById("sim-ejecutar").addEventListener("click", async () => {
  const juego = simJuego.value;
  const rondas = Number(document.getElementById("sim-rondas").value);
  const apuesta = Number(document.getElementById("sim-apuesta").value);

  const cuerpo = { juego, rondas, apuesta };
  if (juego === "ruleta") {
    cuerpo.tipo = document.getElementById("sim-ruleta-tipo").value;
    cuerpo.valor = document.getElementById("sim-ruleta-valor").value;
  } else if (juego === "dados") {
    cuerpo.tipo = document.getElementById("sim-dados-tipo").value;
    cuerpo.valor = document.getElementById("sim-dados-valor").value;
  }

  try {
    const r = await api("/api/simulacion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cuerpo),
    });

    document.getElementById("sim-resultados").hidden = false;
    document.getElementById("stat-rondas").textContent = r.rondas;
    document.getElementById("stat-victorias").textContent = `${r.victorias} / ${r.derrotas} derrotas`;
    document.getElementById("stat-prob").textContent = `${(r.prob_victoria * 100).toFixed(2)}%`;
    document.getElementById("stat-saldo-final").textContent = r.saldo_final.toFixed(2);
    document.getElementById("stat-ganancia").textContent = r.ganancia_neta.toFixed(2);
    document.getElementById("stat-retorno").textContent = `${(r.retorno_sobre_apuesta * 100).toFixed(2)}%`;

    const ctx = document.getElementById("grafica-saldo").getContext("2d");
    if (grafica) grafica.destroy();
    grafica = new Chart(ctx, {
      type: "line",
      data: {
        labels: r.historial.map((_, i) => i),
        datasets: [{
          label: "Saldo simulado",
          data: r.historial,
          borderColor: "#d4af37",
          backgroundColor: "rgba(212,175,55,0.15)",
          fill: true,
          pointRadius: 0,
          tension: 0.15,
        }],
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: "#f4ead8" } } },
        scales: {
          x: { ticks: { color: "#f4ead8" }, title: { display: true, text: "Ronda (muestreada)", color: "#f4ead8" } },
          y: { ticks: { color: "#f4ead8" }, title: { display: true, text: "Saldo", color: "#f4ead8" } },
        },
      },
    });
  } catch (e) {
    alert(e.message);
  }
});

cargarEstado();
