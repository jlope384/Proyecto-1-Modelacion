// Datos reales: tabla Real / Base / Mejorada (GET /api/datos/referencia, generado por la Fase 8).
import { Barras, COLOR, Grafica } from "../components/charts.jsx";
import { Card, ConDatos, Etiqueta, PROCEDENCIA, Stat } from "../components/ui.jsx";
import { DIA, JUEGO, num, signo } from "../formato.js";

const dec = (u) => (u === "veces" ? 2 : u === "%" ? 2 : u === "min" ? 2 : 0);

export default function DatosReales() {
  return <ConDatos ruta="/api/datos/referencia">{(d) => <Vista d={d} />}</ConDatos>;
}

function Vista({ d }) {
  const filas = d.filas;
  const wpu = filas.filter((f) => f.metrica.startsWith("Win por mesa"));
  const dias = d.llegadas_dia_semana;
  const mae = Object.entries(d.mae);
  const mez = d.mezcla_tragamonedas;
  return (
    <>
      <div className="stats">
        {mae.map(([k, v]) => (
          <Stat
            key={k}
            l={`MAE · ${k.toUpperCase()}`}
            v={num(v.mae_base, 2)}
            u={v.unidad}
            s={`Base, ${v.n} ${v.n === 1 ? "fila" : "filas"} · error relativo medio ${num(v.error_rel_medio_base_pct, 1)} %`}
          />
        ))}
      </div>

      <section className="card" aria-label="Referencia real contra simulación">
        <div className="ch">
          <span>REAL CONTRA SIMULACIÓN · VALIDACIÓN {d.periodo_validacion}</span>
          <Etiqueta tipo="sintetico">100 réplicas · semillas 7001–7100</Etiqueta>
        </div>
        <div className="legendrow">
          <span>Procedencia de cada dato:</span>
          {Object.keys(PROCEDENCIA).map((k) => (
            <Etiqueta key={k} tipo={k} />
          ))}
        </div>
        <div className="tw">
          <table>
            <thead>
              <tr>
                <th>Métrica</th>
                <th>Juego</th>
                <th>Unidad</th>
                <th className="n">Real</th>
                <th className="n">Base</th>
                <th className="n">Mejorada</th>
                <th className="n">Error abs.</th>
                <th className="n">Error rel.</th>
                <th className="n">Cambio</th>
                <th>Procedencia</th>
              </tr>
            </thead>
            <tbody>
              {filas.map((f, i) => (
                <tr key={i}>
                  <td>{f.metrica}</td>
                  <td className="m">{JUEGO[f.juego_o_dia] || f.juego_o_dia}</td>
                  <td className="m">{f.unidad}</td>
                  <td className="n">{f.real === null ? "—" : num(f.real, dec(f.unidad))}</td>
                  <td className="n">{num(f.base, dec(f.unidad))}</td>
                  <td className="n">{num(f.mejorada, dec(f.unidad))}</td>
                  <td className="n">{f.real === null ? "—" : signo(f.error_abs_base, dec(f.unidad))}</td>
                  <td className="n">{f.real === null ? "—" : `${signo(f.error_rel_base_pct, 1)} %`}</td>
                  <td className="n">{f.cambio_pct === null ? "—" : `${signo(f.cambio_pct, 1)} %`}</td>
                  <td>
                    <Etiqueta tipo={f.etiqueta} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="cf">
          Real: {d.fuentes.nevada}; {d.fuentes.gkl}. Error absoluto y relativo de la simulación base contra el dato real; cambio de la mejorada
          respecto de la base. {d.nota} La participación en el win es implícita: win por unidad simulado por las unidades estatales de Nevada,
          porque el piso simulado tiene más mesas por máquina que el estado.
        </div>
      </section>

      <div className="cols">
        <Card
          titulo="LLEGADAS POR DÍA"
          extra={<Etiqueta tipo="real" />}
          pie="Factor del día = llegadas del día ÷ promedio semanal. El modelo usa los factores de 2023; 2024 es la validación. El perfil por hora sigue siendo un supuesto: Grand Korea Leisure no trae horas."
        >
          <Grafica titulo="Llegadas por día de la semana" sub="Eje Y: factor del día (veces el promedio semanal) · Eje X: día">
            <Barras
              etiquetas={dias.map((x) => DIA[x.dia])}
              series={[
                { etiqueta: "Real 2023 (calibración)", datos: dias.map((x) => x.factor_real_2023), color: COLOR.real2 },
                { etiqueta: "Real 2024 (validación)", datos: dias.map((x) => x.factor_real_2024), color: COLOR.real },
                { etiqueta: "Simulado", datos: dias.map((x) => x.factor_simulado), color: COLOR.base },
              ]}
              xTitulo="Día de la semana"
              yTitulo="Factor (veces)"
              y={{ min: 0.6 }}
              formato={(v) => num(v, 3)}
            />
          </Grafica>
          <details className="tabla">
            <summary>Ver tabla</summary>
            <div className="tw">
              <table>
                <thead>
                  <tr>
                    <th>Día</th>
                    <th className="n">Real 2023</th>
                    <th className="n">Real 2024</th>
                    <th className="n">Simulado</th>
                    <th className="n">Sesiones sim.</th>
                  </tr>
                </thead>
                <tbody>
                  {dias.map((x) => (
                    <tr key={x.dia}>
                      <td>{DIA[x.dia]}</td>
                      <td className="n">{num(x.factor_real_2023, 3)}</td>
                      <td className="n">{num(x.factor_real_2024, 3)}</td>
                      <td className="n">{num(x.factor_simulado, 3)}</td>
                      <td className="n">{num(x.sesiones_sim_media)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </Card>

        <Card
          titulo="WIN POR UNIDAD"
          extra={<Etiqueta tipo="publico" />}
          pie="Win de una mesa dividido entre el win de una máquina. No depende del tamaño del piso ni de la moneda, por eso se compara con Nevada. El modelo sobreestima dados y ruleta y subestima blackjack: es la limitación principal de la calibración."
        >
          <Grafica titulo="Win por mesa relativo a una máquina" sub="Eje Y: veces el win de una máquina · Eje X: juego">
            <Barras
              etiquetas={wpu.map((f) => JUEGO[f.juego_o_dia])}
              series={[
                { etiqueta: `Real (Nevada ${d.periodo_validacion})`, datos: wpu.map((f) => f.real), color: COLOR.real },
                { etiqueta: "Base", datos: wpu.map((f) => f.base), color: COLOR.base },
                { etiqueta: "Mejorada", datos: wpu.map((f) => f.mejorada), color: COLOR.mejorada },
              ]}
              xTitulo="Juego"
              yTitulo="Veces"
              formato={(v) => num(v, 2)}
            />
          </Grafica>
        </Card>
      </div>

      <Card titulo="MEZCLA DE INGRESO" extra={<Etiqueta tipo="publico" />}>
        <div className="chart-t">Tragamonedas contra mesas</div>
        <div className="chart-s">Participación en el win de los cuatro juegos (implícita) · real (Nevada) contra simulación base y mejorada</div>
        {[
          ["Real (Nevada)", mez.real, "publico"],
          ["Simulación base", mez.base, "sintetico"],
          ["Simulación mejorada", mez.mejorada, "sintetico"],
        ].map(([t, a, tipo]) => (
          <div className="mx" key={t}>
            <div className="mxl">
              <span>{t}</span>
              <Etiqueta tipo={tipo} />
            </div>
            <div className="mxt">
              <div className="seg s1" style={{ width: `${a}%` }}>
                {num(a, 1)} % tragamonedas
              </div>
              <div className="seg s2" style={{ width: `${100 - a}%` }}>
                {num(100 - a, 1)} % mesas
              </div>
            </div>
          </div>
        ))}
      </Card>
    </>
  );
}
