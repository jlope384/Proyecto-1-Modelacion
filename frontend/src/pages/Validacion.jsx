// Validación: generador, distribución de cada juego, consistencia del sistema y hold (GET /api/validacion).
import { Card, ConDatos, Stat, Veredicto } from "../components/ui.jsx";
import { JUEGO, num } from "../formato.js";

export default function Validacion() {
  return <ConDatos ruta="/api/validacion">{(d) => <Vista d={d} />}</ConDatos>;
}

function Vista({ d }) {
  const cuenta = (xs) => `${xs.filter((x) => x.aprobado).length} / ${xs.length}`;
  return (
    <>
      <div className="stats">
        <Stat l="GENERADOR (LCG)" v={cuenta(d.pruebas)} s={`Pruebas aprobadas con ${num(d.n)} uniformes`} />
        <Stat l="DISTRIBUCIÓN POR JUEGO" v={cuenta(d.juegos)} s="Chi² repetida con 100 semillas" />
        <Stat l="SISTEMA" v={cuenta(d.sistema)} s="Ley de Little y conservación" />
        <Stat l="HOLD POR JUEGO" v={cuenta(d.hold)} s="Teórico compatible con el simulado" />
      </div>

      <Card
        titulo="GENERADOR DE NÚMEROS ALEATORIOS"
        cuerpo={false}
        pie={`LCG propio: a = ${d.generador.a}, c = ${d.generador.c}, m = ${d.generador.m}, semilla ${d.generador.semilla}. Nivel de significancia 5 %: se aprueba si no se rechaza H0. Con muchas pruebas, se espera que alguna falle por azar en 1 de cada 20.`}
      >
        <div className="tw">
          <table>
            <thead>
              <tr>
                <th>Prueba</th>
                <th>Hipótesis nula</th>
                <th className="n">Estadístico</th>
                <th className="n">p</th>
                <th>Veredicto</th>
              </tr>
            </thead>
            <tbody>
              {d.pruebas.map((t) => (
                <tr key={t.nombre}>
                  <td>{t.nombre}</td>
                  <td className="m">{t.hipotesis}</td>
                  <td className="n">{t.estadistico === null || t.estadistico === undefined ? "—" : num(t.estadistico, 3)}</td>
                  <td className="n">{t.p_valor === null || t.p_valor === undefined ? "—" : num(t.p_valor, 3)}</td>
                  <td>
                    <Veredicto ok={t.aprobado} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="cols">
        <Card
          titulo="DISTRIBUCIÓN DE CADA JUEGO"
          cuerpo={false}
          pie="Chi² entre lo generado y la distribución teórica (número de ruleta, suma de dados, símbolo, carta), repetida con 100 semillas. Una sola chi² rechaza por azar 1 de cada 20 veces; lo que valida es que la tasa de rechazo ronde el 5 % y que los p-valores sean uniformes (KS sobre los p-valores)."
        >
          <div className="tw">
            <table>
              <thead>
                <tr>
                  <th>Juego</th>
                  <th className="n">Rechazos</th>
                  <th className="n">p medio</th>
                  <th className="n">KS p</th>
                  <th>Veredicto</th>
                </tr>
              </thead>
              <tbody>
                {d.juegos.map((t) => (
                  <tr key={t.juego}>
                    <td>
                      {JUEGO[t.juego]}
                      <span className="sub">
                        {t.replicas} × {num(t.n)} valores
                      </span>
                    </td>
                    <td className="n">
                      {t.rechazos} / {t.replicas}
                      <span className="sub">esperado ≈ {num(100 * t.tasa_esperada, 0)} %</span>
                    </td>
                    <td className="n">{num(t.p_medio, 3)}</td>
                    <td className="n">{num(t.ks_p, 3)}</td>
                    <td>
                      <Veredicto ok={t.aprobado} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
        <Card titulo="CONSISTENCIA DEL SISTEMA" cuerpo={false} pie="Calculado sobre todas las réplicas de los experimentos (Fase 8).">
          <div className="tw">
            <table>
              <thead>
                <tr>
                  <th>Prueba</th>
                  <th>Resultado</th>
                  <th>Criterio</th>
                  <th>Veredicto</th>
                </tr>
              </thead>
              <tbody>
                {d.sistema.map((t) => (
                  <tr key={t.nombre}>
                    <td>
                      {t.nombre}
                      <span className="sub">{t.que}</span>
                    </td>
                    <td className="m">{t.resultado}</td>
                    <td className="m">{t.criterio}</td>
                    <td>
                      <Veredicto ok={t.aprobado} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <Card
        titulo="HOLD POR JUEGO: TEÓRICO CONTRA SIMULADO"
        cuerpo={false}
        pie={`Simulado = suma de ingreso ÷ suma de apostado en ${d.hold[0].replicas} días del piso base. Criterio de aprobación: ${d.criterio_hold}. La prueba usa ingreso − h₀ · apostado por día, cuya media es 0 si el hold es h₀.`}
      >
        <div className="tw">
          <table>
            <thead>
              <tr>
                <th>Juego</th>
                <th className="n">Teórico (%)</th>
                <th className="n">Simulado (%)</th>
                <th className="n">IC 95 % (%)</th>
                <th className="n">Diferencia (pp)</th>
                <th className="n">z</th>
                <th>Veredicto</th>
              </tr>
            </thead>
            <tbody>
              {d.hold.map((t) => (
                <tr key={t.juego}>
                  <td>
                    {JUEGO[t.juego]}
                    <span className="sub">{t.origen_teorico}</span>
                  </td>
                  <td className="n">{num(100 * t.teorico, 3)}</td>
                  <td className="n">{num(100 * t.simulado, 3)}</td>
                  <td className="n">
                    {num(100 * t.ic95[0], 2)} – {num(100 * t.ic95[1], 2)}
                  </td>
                  <td className="n">{num(100 * (t.simulado - t.teorico), 3)}</td>
                  <td className="n">{num(t.z, 2)}</td>
                  <td>
                    <Veredicto ok={t.aprobado} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  );
}
