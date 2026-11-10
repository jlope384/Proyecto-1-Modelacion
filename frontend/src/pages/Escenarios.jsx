// Escenarios: base, mejorada y sensibilidad (GET /api/escenarios, generado por src/experimentos/correr.py).
import { useState } from "react";
import { Barras, COLOR, Grafica, Lineas } from "../components/charts.jsx";
import { Card, ConDatos, Etiqueta, Stat, Veredicto } from "../components/ui.jsx";
import { ic, num, signo } from "../formato.js";

const JUEGOS = ["tragamonedas", "blackjack", "ruleta", "dados"];
const PUESTOS = { tragamonedas: 1, blackjack: 5, ruleta: 7, dados: 8 };

export default function Escenarios({ config }) {
  return <ConDatos ruta="/api/escenarios">{(d) => <Vista d={d} puestos={config.datos ? config.datos.puestos_por_unidad : PUESTOS} />}</ConDatos>;
}

function utilGlobal(c, puestos) {
  const cap = JUEGOS.reduce((a, j) => a + c.conteos[j] * puestos[j], 0);
  return JUEGOS.reduce((a, j) => a + c.metricas[`utilizacion_${j}`].media * c.conteos[j] * puestos[j], 0) / cap;
}

function Celda({ m, f = 1, d = 0 }) {
  return (
    <td className="n">
      {num(m.media * f, d)} ± {num(m.desv * f, d)}
      <span className="sub">{ic(m.ic95, d, f)}</span>
    </td>
  );
}

function Vista({ d, puestos }) {
  const [sens, setSens] = useState("llegadas");
  const conds = d.condiciones;
  const pares = d.pares;
  const meta = d.meta;
  const principal = pares.find((p) => p.condicion === "principal");
  const S = d.sensibilidad[sens];
  const etiquetasCond = pares.map((p) => p.etiqueta);
  const de = (cid, conf) => conds.find((c) => c.condicion === cid && c.configuracion === conf);
  const reparto = (c) => JUEGOS.map((j) => c[j]).join("/");

  return (
    <>
      <div className="stats">
        <Stat
          l="MEJORA DE INGRESO"
          v={signo(principal.ingreso.pct, 1)}
          u="%"
          s={`IC 95 %: ${signo(principal.ingreso.pct_ic95[0], 1)} a ${signo(principal.ingreso.pct_ic95[1], 1)} % · ${principal.replicas} réplicas pareadas`}
        />
        <Stat
          l="ABANDONO BASE → MEJORADA"
          v={`${num(100 * principal.abandono_base, 1)} → ${num(100 * principal.abandono_mejorada, 1)}`}
          u="%"
          s={`Límite ${num(100 * meta.limite_abandono, 0)} %`}
          chip={<Etiqueta tipo="estimado" />}
        />
        <Stat
          l="CONDICIONES CON MEJORA"
          v={`${pares.filter((p) => p.mejora_significativa).length} / ${pares.length}`}
          s="IC 95 % de la diferencia por encima de 0"
        />
        <Stat
          l="CONSISTENCIA"
          v={`${d.consistencia.replicas_totales}`}
          u="réplicas"
          s={`Little ≤ ${num(100 * d.consistencia.little_error_rel_max, 1)} % · conservación ${d.consistencia.conservacion_clientes ? "OK" : "falla"}`}
        />
      </div>

      <section className="card" aria-label="Escenarios con intervalos de confianza">
        <div className="ch">
          <span>BASE, MEJORADA Y SENSIBILIDAD</span>
          <Etiqueta tipo="sintetico">Semillas desde {meta.semilla_inicial}</Etiqueta>
        </div>
        <div className="tw">
          <table>
            <thead>
              <tr>
                <th>Condición</th>
                <th>Piso</th>
                <th className="n">Ingreso (u.m./día)</th>
                <th className="n">Espera (min)</th>
                <th className="n">Abandono (%)</th>
                <th className="n">Utilización (%)</th>
              </tr>
            </thead>
            <tbody>
              {conds.map((c) => (
                <tr key={c.id}>
                  <td>
                    <b>{c.etiqueta}</b>
                    <span className="sub">
                      {c.replicas} réplicas · semillas {c.semillas[0]}–{c.semillas[1]}
                    </span>
                  </td>
                  <td>
                    {c.configuracion === "base" ? "Base" : "Mejorada"}
                    <span className="sub">{reparto(c.conteos)}</span>
                  </td>
                  <Celda m={c.metricas.ingreso_total} />
                  <Celda m={c.metricas.espera_promedio_min} d={2} />
                  <Celda m={c.metricas.prob_abandono} f={100} d={2} />
                  <td className="n">{num(100 * utilGlobal(c, puestos), 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="cf">
          Cada celda: media ± desviación entre réplicas, y debajo el intervalo de confianza de 95 % de la media. Piso = máquinas/blackjack/ruleta/dados.
          Utilización ponderada por puestos. Espera y abandono son estimados: no tienen referencia real.
        </div>
      </section>

      <>
        <Card
          titulo="CAMBIO RESPECTO DE LA BASE"
          extra={<Etiqueta tipo="estimado">Mejora simulada, no observada</Etiqueta>}
          cuerpo={false}
          pie="Diferencias pareadas: base y mejorada corren con las mismas semillas y los mismos clientes (números aleatorios comunes), así que el intervalo mide la mejora y no el ruido entre días."
        >
          <div className="tw">
            <table>
              <thead>
                <tr>
                  <th>Condición</th>
                  <th className="n">Δ ingreso</th>
                  <th className="n">%</th>
                  <th className="n">Δ abandono</th>
                  <th>Mejorada ≤ 10 %</th>
                </tr>
              </thead>
              <tbody>
                {pares.map((p) => (
                  <tr key={p.condicion}>
                    <td>
                      {p.etiqueta}
                      <span className="sub">{p.replicas} réplicas</span>
                    </td>
                    <td className="n">
                      {signo(p.ingreso.media)}
                      <span className="sub">{ic(p.ingreso.ic95)}</span>
                    </td>
                    <td className="n">
                      {signo(p.ingreso.pct, 1)} %
                      <span className="sub">
                        {p.mejora_significativa ? "significativa" : "no significativa"}
                      </span>
                    </td>
                    <td className="n">{signo(p.abandono_pp.media, 2)} pp</td>
                    <td>
                      <Veredicto ok={p.mejorada_dentro_del_limite} textoOk="CUMPLE" textoNo="EXCEDE" />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card titulo="INGRESO POR CONDICIÓN">
          <Grafica titulo="Ingreso medio por condición" sub="Eje Y: millones de u.m. por día (media de las réplicas) · Eje X: condición" alto={320}>
            <Barras
              etiquetas={etiquetasCond}
              series={[
                { etiqueta: "Base", datos: pares.map((p) => de(p.condicion, "base").metricas.ingreso_total.media / 1e6), color: COLOR.base },
                { etiqueta: "Mejorada", datos: pares.map((p) => de(p.condicion, "mejorada").metricas.ingreso_total.media / 1e6), color: COLOR.mejorada },
              ]}
              xTitulo="Condición"
              yTitulo="Millones de u.m. por día"
              y={{ min: 0.6 }}
              formato={(v) => num(v, 3)}
            />
          </Grafica>
        </Card>
      </>

      <section className="card">
        <div className="ch">
          <span>SENSIBILIDAD</span>
          <div className="opts">
            {Object.keys(d.sensibilidad).map((k) => (
              <button key={k} className={sens === k ? "ob on" : "ob"} aria-pressed={sens === k} onClick={() => setSens(k)}>
                {k === "llegadas" ? "LLEGADAS" : "PACIENCIA"}
              </button>
            ))}
          </div>
        </div>
        <div className="cb">
          <div className="cols">
            <Grafica titulo={`Ingreso según ${S.variable}`} sub={`Eje Y: millones de u.m. por día · Eje X: ${S.variable} (${S.unidad}). Banda: IC 95 %`}>
              <Lineas
                etiquetas={S.serie.map((p) => p.valor)}
                series={["base", "mejorada"].map((k) => ({
                  etiqueta: k === "base" ? "Base" : "Mejorada",
                  color: COLOR[k],
                  puntos: true,
                  datos: S.serie.map((p) => p[k].ingreso_total.media / 1e6),
                  banda: [S.serie.map((p) => p[k].ingreso_total.ic95[0] / 1e6), S.serie.map((p) => p[k].ingreso_total.ic95[1] / 1e6)],
                }))}
                xTitulo={`${S.variable} (${S.unidad})`}
                yTitulo="Millones de u.m. por día"
                formato={(v) => num(v, 3)}
              />
            </Grafica>
            <Grafica titulo={`Abandono según ${S.variable}`} sub={`Eje Y: % de sesiones · Eje X: ${S.variable}. Línea punteada: límite de ${num(100 * meta.limite_abandono, 0)} %`}>
              <Lineas
                etiquetas={S.serie.map((p) => p.valor)}
                series={[
                  ...["base", "mejorada"].map((k) => ({
                    etiqueta: k === "base" ? "Base" : "Mejorada",
                    color: COLOR[k],
                    puntos: true,
                    datos: S.serie.map((p) => 100 * p[k].prob_abandono.media),
                    banda: [S.serie.map((p) => 100 * p[k].prob_abandono.ic95[0]), S.serie.map((p) => 100 * p[k].prob_abandono.ic95[1])],
                  })),
                  { etiqueta: "Límite", color: COLOR.limite, punteada: true, datos: S.serie.map(() => 100 * meta.limite_abandono) },
                ]}
                xTitulo={`${S.variable} (${S.unidad})`}
                yTitulo="Abandono (%)"
                formato={(v) => num(v, 2)}
              />
            </Grafica>
          </div>
          <div className="tw" style={{ marginTop: 20 }}>
            <table>
              <thead>
                <tr>
                  <th>{S.variable}</th>
                  <th className="n">Ingreso base</th>
                  <th className="n">Ingreso mejorada</th>
                  <th className="n">Abandono base</th>
                  <th className="n">Abandono mejorada</th>
                  <th className="n">Réplicas</th>
                </tr>
              </thead>
              <tbody>
                {S.serie.map((p) => (
                  <tr key={p.valor}>
                    <td>
                      {p.valor} {S.unidad === "min" ? "min" : "x"}
                      {p.condicion === "principal" && <span className="sub">valor calibrado</span>}
                    </td>
                    <td className="n">{num(p.base.ingreso_total.media)}</td>
                    <td className="n">{num(p.mejorada.ingreso_total.media)}</td>
                    <td className="n">{num(100 * p.base.prob_abandono.media, 2)} %</td>
                    <td className="n">{num(100 * p.mejorada.prob_abandono.media, 2)} %</td>
                    <td className="n">{p.base.ingreso_total.n}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="why" style={{ marginTop: 12 }}>
            Con más llegadas los dos pisos pasan el límite de abandono: la mejora de ingreso se mantiene, pero ninguno de los dos repartos sería
            aceptable sin más área. La recomendación vale para la demanda calibrada con 2023 y con menos llegadas.
          </p>
        </div>
      </section>

      {d.sensibilidad_area && <SensibilidadArea a={d.sensibilidad_area} />}
    </>
  );
}

// Sensibilidad al área por unidad: el GA se corre de nuevo con mesas más chicas y más grandes.
function SensibilidadArea({ a }) {
  const es = a.escenarios;
  const rep = (c) => JUEGOS.map((j) => c[j]).join("/");
  return (
    <section className="card" aria-label="Sensibilidad al área por unidad">
      <div className="ch">
        <span>SENSIBILIDAD AL ÁREA POR UNIDAD</span>
        <Etiqueta tipo="estimado">Supuesto sin fuente</Etiqueta>
      </div>
      <div className="cb">
        <p className="why" style={{ marginBottom: 16 }}>
          El área que ocupa cada mesa (en máquinas) es una estimación del equipo y define el trade-off que optimiza el GA. Se volvió a correr el
          GA con mesas 25 % más chicas y 25 % más grandes, y cada reparto elegido se comparó con la base con {a.replicas} réplicas pareadas
          (semillas {a.semillas[0]}–{a.semillas[1]}).
        </p>
        <div className="cols">
          <Grafica titulo="Mejora de ingreso por escenario de área" sub="Eje Y: % del ingreso base (mejorada − base) · Eje X: área por unidad de las mesas">
            <Barras
              etiquetas={es.map((e) => `${e.etiqueta} (${e.area_por_unidad.blackjack}/${e.area_por_unidad.ruleta}/${e.area_por_unidad.dados})`)}
              series={[{ etiqueta: "Mejora de ingreso (%)", datos: es.map((e) => e.diferencia.ingreso.pct), color: COLOR.mejorada }]}
              xTitulo="Escenario (área blackjack/ruleta/dados)"
              yTitulo="% del ingreso base"
              y={{ min: 0 }}
              formato={(v) => `${num(v, 1)} %`}
            />
          </Grafica>
          <Grafica titulo="Abandono del reparto elegido" sub="Eje Y: % de sesiones · Eje X: escenario. Línea: límite de 10 %">
            <Barras
              etiquetas={es.map((e) => e.etiqueta)}
              series={[
                { etiqueta: "Base", datos: es.map((e) => 100 * e.base.prob_abandono.media), color: COLOR.base },
                { etiqueta: "Reparto del GA", datos: es.map((e) => 100 * e.mejorada.prob_abandono.media), color: COLOR.mejorada },
              ]}
              xTitulo="Escenario"
              yTitulo="Abandono (%)"
              y={{ min: 7, max: 11 }}
              formato={(v) => `${num(v, 2)} %`}
            />
          </Grafica>
        </div>
        <div className="tw" style={{ marginTop: 20 }}>
          <table>
            <thead>
              <tr>
                <th>Escenario</th>
                <th className="n">Área BJ/ruleta/dados</th>
                <th className="n">Área total</th>
                <th>Reparto del GA</th>
                <th className="n">Δ ingreso</th>
                <th className="n">Abandono</th>
                <th>Límite</th>
                <th>¿Cabe 84/5/1/2?</th>
              </tr>
            </thead>
            <tbody>
              {es.map((e) => (
                <tr key={e.id}>
                  <td>{e.etiqueta}</td>
                  <td className="n">
                    {e.area_por_unidad.blackjack}/{e.area_por_unidad.ruleta}/{e.area_por_unidad.dados}
                  </td>
                  <td className="n">{e.area_total}</td>
                  <td>
                    {rep(e.piso_elegido)}
                    <span className="sub">{e.mismo_reparto_que_el_ga_principal ? "igual al principal" : "cambia"}</span>
                  </td>
                  <td className="n">
                    {signo(e.diferencia.ingreso.pct, 1)} %
                    <span className="sub">
                      IC 95 %: {signo(e.diferencia.ingreso.pct_ic95[0], 1)} a {signo(e.diferencia.ingreso.pct_ic95[1], 1)} %
                    </span>
                  </td>
                  <td className="n">{num(100 * e.mejorada.prob_abandono.media, 2)} %</td>
                  <td>
                    <Veredicto ok={e.mejorada_dentro_del_limite} textoOk="CUMPLE" textoNo="EXCEDE" />
                  </td>
                  <td>
                    <Veredicto ok={e.reparto_principal_cabe} textoOk="SÍ CABE" textoNo="NO CABE" />
                    <span className="sub">usa {e.area_reparto_principal} de {e.area_total}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="why" style={{ marginTop: 12 }}>
          En los tres escenarios el GA agrega una segunda mesa de dados y la mejora de ingreso es significativa. Lo que cambia es cuánto
          blackjack y ruleta conviene: con mesas más chicas sube a 6 blackjack y 2 ruletas; con mesas más grandes baja a 3 blackjack, y con 100
          réplicas el abandono queda apenas sobre el límite (en la re-evaluación de 30 réplicas del GA estaba por debajo). Si las mesas fueran
          25 % más grandes, el reparto 84/5/1/2 no cabría en el piso. La recomendación robusta es la segunda mesa de dados; el número exacto de
          mesas de blackjack depende de cuánto ocupen.
        </p>
      </div>
    </section>
  );
}
