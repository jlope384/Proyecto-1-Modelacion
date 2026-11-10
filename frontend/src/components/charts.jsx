// Gráficas con Chart.js, con los tokens del diseño (README del handoff).
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { Bar, Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Filler, Tooltip, Legend);

ChartJS.defaults.font.family = "'DM Sans', system-ui, sans-serif";
ChartJS.defaults.font.size = 12;
ChartJS.defaults.color = "#cdbdea";

export const COLOR = {
  real: "#f1ebfb",
  real2: "rgba(241,235,251,.45)",
  base: "#b48cff",
  mejorada: "#5fd0ff",
  estimado: "#ffffff",
  limite: "#f060c0",
};

const GRID = "rgba(255,255,255,.11)";

function ejes(xTitulo, yTitulo, extraY = {}) {
  return {
    x: { grid: { color: GRID }, ticks: { color: "#e1d6f3" }, title: { display: !!xTitulo, text: xTitulo, color: "#cdbdea" } },
    y: {
      grid: { color: GRID },
      ticks: { color: "#cdbdea" },
      title: { display: !!yTitulo, text: yTitulo, color: "#cdbdea" },
      ...extraY,
    },
  };
}

const LEYENDA = { labels: { color: "#e1d6f3", boxWidth: 14, boxHeight: 10 } };

export function Grafica({ titulo, sub, alto = 260, children }) {
  return (
    <div className="chart">
      {titulo && <div className="chart-t">{titulo}</div>}
      {sub && <div className="chart-s">{sub}</div>}
      <div style={{ position: "relative", height: alto }}>{children}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Barras con forma de prisma: cara frontal, cara lateral más oscura y tapa en
// rombo, sobre una columna "fantasma" de alto completo, como la referencia
// visual del equipo. Chart.js calcula la geometría y las interacciones
// (tooltip, leyenda); este plugin solo cambia cómo se pinta cada barra.
// ---------------------------------------------------------------------------

function aRgb(color) {
  if (color.startsWith("#")) {
    const h = color.length === 4 ? color.slice(1).replace(/./g, (c) => c + c) : color.slice(1);
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16), 1];
  }
  const m = color.match(/rgba?\(([^)]+)\)/);
  if (!m) return [180, 140, 255, 1];
  const p = m[1].split(",").map((x) => parseFloat(x));
  return [p[0], p[1], p[2], p[3] === undefined ? 1 : p[3]];
}

/** Mezcla el color con blanco (t > 0) o con negro (t < 0). */
function tono(color, t) {
  const [r, g, b, a] = aRgb(color);
  const f = (v) => Math.round(t >= 0 ? v + (255 - v) * t : v * (1 + t));
  return `rgba(${f(r)},${f(g)},${f(b)},${a})`;
}

function poligono(ctx, pts, relleno) {
  ctx.beginPath();
  ctx.moveTo(pts[0][0], pts[0][1]);
  pts.slice(1).forEach(([x, y]) => ctx.lineTo(x, y));
  ctx.closePath();
  ctx.fillStyle = relleno;
  ctx.fill();
}

/** Prisma vertical: rombo arriba en `tope`, base en `piso`, centrado en x. */
function prisma(ctx, x, ancho, tope, piso, color) {
  const x0 = x - ancho / 2;
  const x1 = x + ancho / 2;
  const d = Math.min(ancho * 0.28, Math.max(2, (piso - tope) / 2));
  const yLado = Math.min(tope + d, piso);
  const yCentro = Math.min(tope + 2 * d, piso);
  poligono(ctx, [[x0, yLado], [x, yCentro], [x, piso], [x0, piso]], color); // cara frontal
  poligono(ctx, [[x, yCentro], [x1, yLado], [x1, piso], [x, piso]], tono(color, -0.45)); // cara lateral
  poligono(ctx, [[x0, yLado], [x, tope], [x1, yLado], [x, yCentro]], tono(color, 0.22)); // tapa
}

const pluginPrisma = {
  id: "prisma",
  beforeDatasetsDraw(chart) {
    const { ctx, chartArea: area } = chart;
    ctx.save();
    ctx.beginPath();
    ctx.rect(area.left, area.top - 20, area.right - area.left, area.bottom - area.top + 20);
    ctx.clip();
    const barras = [];
    chart.data.datasets.forEach((ds, i) => {
      const meta = chart.getDatasetMeta(i);
      if (meta.hidden || meta.type !== "bar") return;
      meta.data.forEach((bar, j) => {
        const v = ds.data[j];
        if (v === null || v === undefined || Number.isNaN(v)) return;
        barras.push({ ...bar.getProps(["x", "y", "base", "width"], true), color: ds.backgroundColor });
      });
    });
    // primero las columnas fantasma de alto completo, luego las barras
    barras.forEach((b) => prisma(ctx, b.x, b.width, area.top, area.bottom, "rgba(120,60,200,0.16)"));
    barras.forEach((b) => {
      const tope = Math.min(b.y, b.base);
      const piso = Math.min(Math.max(b.y, b.base), area.bottom);
      prisma(ctx, b.x, b.width, tope, piso, b.color);
    });
    ctx.restore();
    return false; // no pintar las barras planas de Chart.js
  },
};

/** series: [{ etiqueta, datos, color }] */
export function Barras({ etiquetas, series, xTitulo, yTitulo, horizontal = false, apilado = false, y = {}, formato }) {
  const data = {
    labels: etiquetas,
    datasets: series.map((s) => ({
      label: s.etiqueta,
      data: s.datos,
      backgroundColor: s.color,
      borderColor: s.borde || s.color,
      borderWidth: s.borde ? 1 : 0,
      maxBarThickness: 64,
      categoryPercentage: 0.82,
      barPercentage: 0.88,
    })),
  };
  // El prisma solo aplica a barras verticales sin apilar.
  const plugins = !horizontal && !apilado ? [pluginPrisma] : [];
  const sc = ejes(horizontal ? yTitulo : xTitulo, horizontal ? xTitulo : yTitulo, y);
  if (apilado) {
    sc.x.stacked = true;
    sc.y.stacked = true;
  }
  return (
    <Bar
      data={data}
      plugins={plugins}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: horizontal ? "y" : "x",
        plugins: {
          legend: LEYENDA,
          tooltip: formato ? { callbacks: { label: (c) => `${c.dataset.label}: ${formato(c.raw)}` } } : {},
        },
        scales: sc,
      }}
    />
  );
}

/** series: [{ etiqueta, datos, color, banda: [[lo...],[hi...]] , punteada }] */
export function Lineas({ etiquetas, series, xTitulo, yTitulo, y = {}, formato }) {
  const datasets = [];
  series.forEach((s) => {
    if (s.banda) {
      datasets.push({ label: `${s.etiqueta} IC inf`, data: s.banda[0], borderWidth: 0, pointRadius: 0, fill: false, _banda: true });
      datasets.push({
        label: `${s.etiqueta} IC 95 %`,
        data: s.banda[1],
        borderWidth: 0,
        pointRadius: 0,
        backgroundColor: s.color + "33",
        fill: "-1",
        _banda: true,
      });
    }
    datasets.push({
      label: s.etiqueta,
      data: s.datos,
      borderColor: s.color,
      backgroundColor: s.color,
      borderWidth: 2.5,
      borderDash: s.punteada ? [6, 5] : [],
      pointRadius: s.puntos ? 3 : 0,
      tension: 0,
      fill: false,
    });
  });
  return (
    <Line
      data={{ labels: etiquetas, datasets }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { ...LEYENDA, labels: { ...LEYENDA.labels, filter: (it, d) => !d.datasets[it.datasetIndex]._banda } },
          tooltip: {
            filter: (it) => !it.dataset._banda,
            callbacks: formato ? { label: (c) => `${c.dataset.label}: ${formato(c.raw)}` } : {},
          },
        },
        scales: ejes(xTitulo, yTitulo, y),
      }}
    />
  );
}
