// Formato de números. Separador de miles con coma y decimales con punto, como en el diseño.
const nf = (d) => new Intl.NumberFormat("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

export const num = (x, d = 0) => (x === null || x === undefined || Number.isNaN(x) ? "—" : nf(d).format(x));
export const pct = (x, d = 1) => (x === null || x === undefined ? "—" : `${nf(d).format(100 * x)} %`);
export const signo = (x, d = 0) => (x === null || x === undefined ? "—" : `${x > 0 ? "+" : x < 0 ? "−" : ""}${nf(d).format(Math.abs(x))}`);
export const ic = (par, d = 0, f = 1) => `IC 95 %: ${nf(d).format(par[0] * f)} – ${nf(d).format(par[1] * f)}`;

export const JUEGO = {
  tragamonedas: "Tragamonedas",
  blackjack: "Blackjack",
  ruleta: "Ruleta",
  dados: "Dados",
};
export const UNIDAD = { tragamonedas: "máquinas", blackjack: "mesas", ruleta: "mesas", dados: "mesas" };
export const DIA = { lunes: "Lun", martes: "Mar", miercoles: "Mié", jueves: "Jue", viernes: "Vie", sabado: "Sáb", domingo: "Dom" };
