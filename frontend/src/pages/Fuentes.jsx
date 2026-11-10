// Fuentes: datasets, supuestos, uso de IA y reproducción. Contenido estático.
import { Card, Etiqueta } from "../components/ui.jsx";

const DATASETS = [
  {
    n: "NEVADA GAMING CONTROL BOARD",
    tipo: "publico",
    enlace: "https://gaming.nv.gov (Gaming Revenue Reports, archivos AAAAMmm-gri.pdf)",
    licencia: "Publicación oficial de acceso público; se cita la fuente",
    acceso: "2026-11-09",
    periodo: "Enero 2023 a diciembre 2024 (y septiembre 2021 para verificar el lector)",
    respalda: "Piso base (unidades por local), mezcla de ingreso, win por unidad y hold de tragamonedas. 2023 calibra, 2024 valida.",
  },
  {
    n: "GRAND KOREA LEISURE (SEVEN LUCK)",
    tipo: "real",
    enlace: "https://www.data.go.kr/data/15116743/fileData.do",
    licencia: "data.go.kr, uso sin restricciones (이용허락범위 제한 없음)",
    acceso: "2026-11-09 (versión 2026-06-18)",
    periodo: "Visitantes diarios 2015 a 2026; se usan 2023 (calibración) y 2024 (validación)",
    respalda: "Nivel de llegadas por día y factor por día de la semana. Se excluyen 2020 a 2022 por COVID.",
  },
];

const SUPUESTOS = [
  ["Perfil de llegadas por hora", "estimado", "Proyecto 1 (los datos solo traen días)"],
  ["Sesiones por visitante", "estimado", "3; con 1 el piso no tendría congestión"],
  ["Puestos por mesa", "estimado", "Blackjack 5, ruleta 7, dados 8 (Proyecto 1)"],
  ["Área por unidad", "estimado", "Máquina 1, blackjack 6, ruleta 8, dados 10; se prueba con mesas ±25 %"],
  ["Demanda por juego", "estimado", "Proporcional a los puestos del piso base"],
  ["Paciencia en cola", "estimado", "Exponencial con media 8 min; se prueba 4 y 12"],
  ["Escala de apuesta en mesas", "publico", "Calibrada contra la mezcla de Nevada 2023"],
  ["Resultados de cada día simulado", "sintetico", "Generados por el modelo con semillas registradas"],
];

export default function Fuentes() {
  return (
    <>
      <div className="ds">
        {DATASETS.map((d) => (
          <Card key={d.n} titulo={d.n} extra={<Etiqueta tipo={d.tipo} />}>
            <dl>
              <dt>Enlace</dt>
              <dd>{d.enlace}</dd>
              <dt>Licencia</dt>
              <dd>{d.licencia}</dd>
              <dt>Acceso</dt>
              <dd>{d.acceso}</dd>
              <dt>Periodo</dt>
              <dd>{d.periodo}</dd>
              <dt>Respalda</dt>
              <dd>{d.respalda}</dd>
            </dl>
          </Card>
        ))}
        <Card titulo="DATOS QUE NO SE USARON" extra={<Etiqueta tipo="sintetico">Descartados</Etiqueta>}>
          <dl>
            <dt>Kangwon Land</dt>
            <dd>Usuarios por tipo de juego (data.go.kr 15121887): la página devuelve 404. La mezcla de juegos sale de Nevada.</dd>
            <dt>Espera y abandono</dt>
            <dd>No hay datos públicos. Se reportan como salidas estimadas del modelo, no como validadas.</dd>
          </dl>
        </Card>
      </div>

      <Card titulo="SUPUESTOS DEL MODELO" cuerpo={false} pie="Cada supuesto se declara con su etiqueta de procedencia. La pestaña Escenarios prueba los de llegadas, paciencia, calibración de mesas y área por unidad.">
        <div className="tw">
          <table>
            <thead>
              <tr>
                <th>Elemento</th>
                <th>Valor u origen</th>
                <th>Procedencia</th>
              </tr>
            </thead>
            <tbody>
              {SUPUESTOS.map(([a, t, b]) => (
                <tr key={a}>
                  <td>{a}</td>
                  <td className="m">{b}</td>
                  <td>
                    <Etiqueta tipo={t} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="cols">
        <Card titulo="USO DE INTELIGENCIA ARTIFICIAL">
          <dl>
            <dt>Herramienta</dt>
            <dd>Claude (Anthropic)</dd>
            <dt>Uso</dt>
            <dd>Apoyo en el código de datos, calibración, algoritmo genético, experimentos, gráficas e interfaz, y en la documentación.</dd>
            <dt>Revisión</dt>
            <dd>Brandon Rivera</dd>
          </dl>
        </Card>
        <Card titulo="REPRODUCIR DESDE CERO">
          <pre>{`# dependencias (desde la raíz)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# datos (Nevada se descarga; GKL viene en el repo)
python src/datos/descargar_nevada.py datos/crudos/nevada 2023-01 2024-12 2021-09
python src/datos/nevada_a_csv.py datos/crudos/nevada datos/procesados/nevada_mensual.csv
python src/datos/nevada_referencia.py datos/procesados/nevada_mensual.csv datos/procesados/nevada_referencia.csv

# calibración, GA, experimentos y gráficas
python src/calibracion/calibrar.py
python src/optimizacion/genetico.py
python src/experimentos/correr.py
python src/optimizacion/genetico.py --area blackjack=5,ruleta=6,dados=8 --salida optimizacion_area_menos25
python src/optimizacion/genetico.py --area blackjack=8,ruleta=10,dados=13 --salida optimizacion_area_mas25
python src/experimentos/sensibilidad_area.py
python src/visualizacion/graficas.py

# panel: API (puerto 5000) y Vite
cd backend && python app.py
cd frontend && npm install && npm run dev`}</pre>
        </Card>
      </div>
    </>
  );
}
