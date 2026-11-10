# Proyecto 2: instrucciones para reutilizar el código del Proyecto 1

Cada fase es corta y deja el proyecto funcionando antes de pasar a la siguiente. Rutas relativas a la raíz de Proyecto-1-Modelacion.

## Resumen

| Acción | Qué |
|---|---|
| Se queda | `rng.py`, `estadistica.py`, `llegadas.py`, `piso.py`, `ruleta.py`, `dados.py`, `tragamonedas.py`, `blackjack.py`, `simulacion.py` y `validacion.py` recortados |
| Se borra | Docker, `carreras.py`, `poker.py`, `__pycache__/`, y los componentes y rutas de juegos interactivos del frontend y de `app.py` |
| Se conserva y se recorta | `frontend/` y `backend/app.py`, siguiendo `03_instrucciones_ui.md` |
| Se modifica | `llegadas.py`, `piso.py`, `dados.py` (o la apuesta de dados en el piso), `simulacion.py`, `validacion.py`, `__init__.py`, `requirements.txt` |
| Se agrega | Lectores de datos, calibración, algoritmo genético, experimentos, gráficas, README |

## Fase 0: copia y línea base

1. Copiar la carpeta completa a un repositorio nuevo para Proyecto 2. No trabajar sobre el repositorio de P1.
2. Crear un entorno virtual e instalar `requirements.txt`.
3. Desde `backend/`, correr `python -m casino.piso`. Debe imprimir `piso.py: autochequeo OK`.
4. Guardar la salida de `simular_dia(horas=24, semilla=1)` como referencia (unos 755 llegadas, 680 atendidos, 75 abandonos, ingreso cercano a 108,786, cerca de 0.6 s). Sirve para comprobar que las fases siguientes no rompen nada.
5. Hacer commit con el mensaje "línea base P1".

## Fase 1: borrar lo que no se usa

1. Borrar `docker-compose.yml`, `backend/Dockerfile`, `backend/.dockerignore`, `frontend/Dockerfile`, `frontend/.dockerignore` y `frontend/nginx.conf`, salvo que el equipo quiera desplegar con Docker.
2. **No borrar** `frontend/` ni `backend/app.py`: se conservan para la demostración y se recortan siguiendo `03_instrucciones_ui.md`. `Flask` se queda en `requirements.txt`.
3. Borrar todas las carpetas `__pycache__/` y confirmar que `.gitignore` las excluye.
4. Hacer commit y volver a correr `python -m casino.piso`. Todavía debe pasar, porque `piso.py` no depende de nada de esto.

## Fase 2: quitar carreras y póker

`carreras.py` y `poker.py` no se usan en el piso, pero otros módulos los importan. Hay que editarlos antes de borrarlos o el código deja de importar.

1. `casino/__init__.py`: quitar `carreras` de la lista de imports.
2. `casino/simulacion.py`:
   - Quitar `carreras` y `poker` del `from . import`.
   - Dejar `JUEGOS = ("ruleta", "dados", "tragamonedas", "blackjack")`.
   - Quitar las ramas de `carreras` y `poker` dentro de `simular` y de `retorno_teorico`.
   - Quitar `comparar_estrategias_blackjack` si no la van a usar.
3. `casino/validacion.py`:
   - Quitar `carreras` y `poker` de los imports.
   - Quitar las ramas de `poker` en `distribucion_teorica`, `distribucion_base` y `_muestrear`.
   - Quitar `"poker"` de la lista de `comparar_todos` y la línea de `carreras.comparar_metodos` en `reporte_completo`.
4. `backend/app.py` también importa `carreras` y `poker` y crea `Hipodromo` y `MesaPoker`. Mientras no se haga la Fase U3 de `03_instrucciones_ui.md`, el servidor no arranca. Si quieren probar el piso antes, hagan primero esa fase.
5. Borrar `carreras.py` y `poker.py`.
6. Correr `python -m casino.piso` y `python -c "from casino import validacion"`. Ambos deben funcionar. Si falla un import, hay una referencia que quedó pendiente.
7. Opcional: en `blackjack.py` la clase `Mesa` (modo interactivo) y `jugar` ya no se usan. El piso solo usa `Zapato` y `jugar_mano`. Se pueden borrar al final si quieren reducir el código.

## Fase 3: hacer parametrizable lo que hoy es fijo

Hoy `simular_dia` ya recibe `recursos` y `pesos_juego`. Falta lo siguiente, que el proyecto necesita para calibrar y para la sensibilidad.

1. `llegadas.py`: `TASA_POR_HORA` es una constante global. Agregar un parámetro `tasa_por_hora=None` a `generar`, `_llegadas_inversa` y `_llegadas_adelgazamiento`, y calcular `lambda_max` dentro. También sirve un parámetro `factor` que multiplique la tasa.
2. `piso.py`: agregar a `simular_dia` los parámetros `tasa_por_hora=None` (o `factor_llegadas=1.0`) y `paciencia_media_min=None`. Hoy `PACIENCIA_MEDIA_MIN` se lee como constante en el motor, línea 301. Hacer que use el parámetro si viene dado.
3. Opcional: pasar también `BANKROLL_TRIANGULAR` y `ESTADIA_MAX_MIN_TRIANGULAR` como parámetros, ya que son supuestos del modelo.
4. Comprobar que con los valores por defecto el resultado es idéntico a la línea base de la Fase 0 (misma semilla, mismos números).

## Fase 4: revisar el hold de cada juego

Esto afecta directamente a la optimización y conviene resolverlo antes de calibrar.

1. **Dados:** en el piso se usa la apuesta `par_impar` que paga 1:1 con probabilidad 0.5. Su retorno teórico es exactamente 0, así que la casa no gana nada de dados y el GA nunca tendría motivo para asignarles mesas. Cambiar la apuesta del piso a una con ventaja de la casa, por ejemplo `suma` en un valor con pago ajustado, o introducir un pago de 1:1 menos comisión. Documentar el cambio.
2. **Tragamonedas:** la ventaja de la casa es 4.475% (`tragamonedas.retorno_teorico()` devuelve -0.04475). Nevada reporta 7.32% de win percent. Decidir si se ajusta la tabla de pagos para acercarse o si se deja y se declara la diferencia como error de calibración.
3. **Ruleta:** -2.70% (`ruleta.retorno_teorico("color", "rojo")`). Es el valor de ruleta europea de un solo cero. Anotarlo.
4. **Blackjack:** usa estrategia básica. Medir el hold simulado con muchas manos y registrar el valor.
5. Crear una tabla con el hold teórico de cada juego y usarla en el informe.

## Fase 5: lectores de datos

Crear una carpeta `datos/` con subcarpetas `crudos/` y `procesados/`, y una carpeta `src/datos/` o similar con los scripts.

1. **Nevada:** descargar los PDF mensuales del Nevada Gaming Control Board y convertirlos a CSV siguiendo la Fase 5A.
2. **Grand Korea Leisure:** descargar el CSV desde data.go.kr. Antes de usarlo, abrirlo y confirmar columnas, rango de fechas y si las columnas de edad son conteos. Sumar por día para obtener visitantes diarios. Excluir 2020 a 2021.
3. **Kangwon Land:** intentar descargar el CSV. Si no sirve, omitirlo; Nevada cubre la mezcla de juegos.
4. Etiquetar cada archivo como dato real observado, dato público de referencia, estimación o dato sintético.

## Fase 5A: pasar los PDF de Nevada a un CSV usable

Cada informe mensual es un PDF de más de 40 páginas, pero solo se necesita la primera tabla: "Statewide, All Nonrestricted Locations". Ahí hay una fila por juego con tres periodos seguidos (mes actual, últimos 3 meses y últimos 12 meses), y cada periodo trae cinco números: locales, unidades, win en miles de dólares, cambio porcentual y win percent. Una fila de mesas tiene 15 números después del nombre. El objetivo es obtener un CSV largo con una fila por mes, juego y periodo.

1. **Descargar los PDF.** Guardarlos en `datos/crudos/nevada/` conservando el nombre original, por ejemplo `2021Sep-gri.pdf`. La dirección del que ya se revisó es `https://gaming.nv.gov/uploadedFiles/gamingnvgov/content/about/gaming-revenue/2021Sep-gri.pdf`; los otros meses siguen el mismo patrón de nombre con año y mes de tres letras en inglés, pero la carpeta del sitio puede variar entre años. Si un enlace no abre, buscar el mes en la página de Gaming Revenue Reports de gaming.nv.gov. Conviene bajar entre 12 y 36 meses consecutivos para tener periodo de calibración y de validación.
2. **Instalar la herramienta de extracción.** El script usa `pdftotext` (viene en el paquete poppler: `brew install poppler` en macOS, `apt install poppler-utils` en Linux). Se descartó una biblioteca de Python para no agregar dependencias al modelo.
3. **Guardar el script** como `src/datos/nevada_a_csv.py`:

```python
"""Convierte los PDF mensuales del Nevada Gaming Control Board en un CSV largo.

Uso:  python nevada_a_csv.py datos/crudos/nevada datos/procesados/nevada_mensual.csv
Los PDF deben llamarse como el original, por ejemplo 2021Sep-gri.pdf.
"""
import csv, re, subprocess, sys
from pathlib import Path

NUM = r"\(?-?[\d,]+(?:\.\d+)?\)?"
PERIODOS = ("mes", "3_meses", "12_meses")
CAMPOS = ("locales", "unidades", "win_miles", "cambio_pct", "win_pct")
MESES = {m: i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), start=1)}
MESES_PERIODO = {"mes": 1, "3_meses": 3, "12_meses": 12}


def a_numero(tok):
    neg = tok.startswith("(") and tok.endswith(")")
    v = float(tok.strip("()").replace(",", ""))
    return -v if neg else v


def pdf_a_texto(ruta):
    # Solo hacen falta las primeras páginas: el bloque estatal está en la 1.
    salida = subprocess.run(
        ["pdftotext", "-layout", "-f", "1", "-l", "2", str(ruta), "-"],
        capture_output=True, text=True, check=True)
    return salida.stdout


def parsear(texto, mes):
    filas, seccion, en_bloque = [], None, False
    for linea in texto.splitlines():
        s = linea.strip()
        if s.startswith("Statewide - All Nonrestricted Locations"):
            en_bloque = True
            continue
        if not en_bloque:
            continue
        if s.startswith("Statewide - $") or s.startswith("Total Gaming"):
            break
        if s.startswith("Table, Counter and Card Games"):
            seccion = "mesas"; continue
        if s.startswith("Slot Machines"):
            seccion = "tragamonedas"; continue
        tokens = s.split()
        if seccion is None or len(tokens) < 16:
            continue
        if not all(re.fullmatch(NUM, t) for t in tokens[-15:]):
            continue  # filas incompletas (Other, Card Games) o texto
        juego = re.sub(r"\s*\(\d\)$", "", " ".join(tokens[:-15])).strip()
        nums = tokens[-15:]
        for i, per in enumerate(PERIODOS):
            vals = [a_numero(t) for t in nums[i * 5:(i + 1) * 5]]
            fila = {"mes": mes, "seccion": seccion, "juego": juego, "periodo": per}
            fila.update(zip(CAMPOS, vals))
            # win acumulado del periodo entre unidades promedio y meses
            fila["win_por_unidad_mes_miles"] = (
                fila["win_miles"] / fila["unidades"] / MESES_PERIODO[per]
                if fila["unidades"] else None)
            filas.append(fila)
    return filas


def main(carpeta, salida):
    todas = []
    for pdf in sorted(Path(carpeta).glob("*-gri.pdf")):
        m = re.match(r"(\d{4})([A-Za-z]{3})", pdf.name)
        mes = f"{m[1]}-{MESES[m[2].title()]:02d}"
        filas = parsear(pdf_a_texto(pdf), mes)
        if not filas:
            print(f"AVISO: {pdf.name} no produjo filas, revisar formato")
        todas.extend(filas)
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(todas[0].keys()))
        w.writeheader(); w.writerows(todas)
    print(f"{len(todas)} filas en {salida}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
```

4. **Correrlo:** `python src/datos/nevada_a_csv.py datos/crudos/nevada datos/procesados/nevada_mensual.csv`.
5. **Columnas del CSV:** `mes` (formato 2021-09), `seccion` (mesas o tragamonedas), `juego`, `periodo` (mes, 3_meses o 12_meses), `locales`, `unidades`, `win_miles` (miles de dólares, acumulado del periodo), `cambio_pct`, `win_pct` y `win_por_unidad_mes_miles`. Esta última divide el win entre las unidades promedio y entre los meses del periodo, por eso en los periodos de 3 y 12 meses no es el win dividido solo entre unidades.
6. **Verificar con septiembre 2021** antes de bajar más meses. Con `periodo` igual a `mes` deben salir estos valores:

| Juego | Unidades | Win en miles | Win percent | Win por unidad al mes en miles |
|---|---|---|---|---|
| Twenty One | 1,933 | 92,180 | 15.30 | 47.69 |
| Roulette | 508 | 42,574 | 18.97 | 83.81 |
| Craps | 328 | 37,684 | 16.39 | 114.89 |
| Total tragamonedas | 122,446 | 780,520 | 7.32 | 6.37 |

   Además, win de tragamonedas entre la suma de win de mesas y tragamonedas debe dar 67.4%, usando las filas `Total` de cada sección (780,520 contra 377,649).
7. **Revisar los casos especiales**, ya contemplados en el script:
   - Los números negativos vienen entre paréntesis, como `(26.53)`, y se convierten a negativo.
   - Los nombres con nota al pie, como `Race Book (1)`, se limpian a `Race Book`.
   - Las denominaciones de tragamonedas empiezan con un número (`1 Cent`, `25 Cent`, `100 Dollars`); el script toma siempre los últimos 15 valores como números y el resto como nombre, por eso funciona.
   - Las filas que no tienen los 15 números (`Other`, `Card Games`) se ignoran. Si algún mes se necesita el total de mesas, usar la fila `Total` de la sección.
   - La fila `Total` aparece en las dos secciones; se distingue con la columna `seccion`.
8. **Probar el script con otros meses.** El script se verificó con el texto de septiembre 2021, tal como lo entregó la herramienta de lectura de PDF, no con `pdftotext` sobre el archivo local, así que puede necesitar un ajuste menor. Si un mes imprime `AVISO`, abrir el texto con `pdftotext -layout -f 1 -l 2 archivo.pdf -` y comparar el formato de las líneas con el de septiembre 2021. Los nombres de juegos y el orden de las filas pueden cambiar entre años, por ejemplo se agregan juegos nuevos de mesa, así que al comparar entre meses conviene filtrar por `juego` y no por posición.
9. **Derivar la tabla de calibración** en `datos/procesados/nevada_referencia.csv` con, para el periodo elegido de calibración y el de validación:
   - Mezcla de ingreso: win de tragamonedas entre el total, y por juego de mesa.
   - Win por unidad al mes por juego.
   - Unidades por local, que es `unidades` entre `locales`.
   - Win percent de tragamonedas.
10. Etiquetar el CSV en el README como dato público de referencia, con fuente, fecha de descarga y periodo cubierto.

## Fase 6: calibración del modelo

1. Elegir un periodo de calibración y otro de validación (hold-out) en los datos.
2. Escalar el modelo: usar un piso proporcional al promedio de Nevada, por ejemplo una décima parte, y comparar por unidad.
3. Ajustar la tasa de llegadas del modelo al promedio diario de Grand Korea Leisure, y el perfil por día de semana con sus factores. El perfil por hora queda como supuesto.
4. Ajustar `PESOS_JUEGO` y el número de unidades base con los datos de Nevada (unidades por local y mezcla de ingreso).
5. Criterio de calibración: elegir un solo parámetro a ajustar (por ejemplo la escala de llegadas) con un indicador, y validar con los demás. Así la comparación no es circular.
6. Calcular MAE y error porcentual entre simulado y real, y guardar la tabla.

## Fase 7: algoritmo genético

Crear `src/optimizacion/genetico.py`, escrito a mano.

1. Cromosoma: vector de enteros con mesas o máquinas por juego.
2. Restricción: área total constante. Definir el área equivalente de cada recurso (por ejemplo una máquina = 1 unidad, una mesa = k unidades) y justificar k como estimación.
3. Operador de reparación que corrige individuos que exceden el área.
4. Selección por torneo, cruce de un punto, mutación de sumar o restar uno.
5. Fitness: ingreso diario promedio en k réplicas, menos penalización por abandono sobre 10%. Usar las mismas semillas para todos los individuos (números aleatorios comunes).
6. Terminar por generaciones máximas o estancamiento. Guardar historial para la gráfica de convergencia.
7. Probar con una población pequeña antes de la corrida larga.
8. Comprobar por código que la solución final respeta la restricción.

## Fase 8: experimentos

Crear `src/experimentos/correr.py`.

1. Tres condiciones: base, mejorada (GA) y sensibilidad (llegadas +20%). Agregar variantes de paciencia (50% a 150%) y pesos de juego.
2. 30 o más réplicas por condición con semillas registradas en un CSV.
3. Reportar promedio, desviación e intervalo de confianza de 95% para ingreso, espera, abandono y utilización.
4. Pruebas internas: ley de Little, atendidos más abandonos igual a llegadas, y las pruebas del generador de `validacion.py`.
5. Para la tabla de comparación con la realidad, incluir solo las métricas con referencia real; espera y abandono se reportan aparte como estimados.
6. Guardar todo en `resultados/` como CSV y JSON.

## Fase 9: gráficas

Usar matplotlib en un script separado de los experimentos, que solo lea `resultados/`.

1. Llegadas simuladas contra reales por día de semana.
2. Base contra mejorada, con barras de error.
3. Sensibilidad.
4. Convergencia del GA.
5. Utilización por recurso.

Cada una con título, ejes, unidades y leyenda.

## Fase 10: repositorio y entrega

1. Organizar: `src/` (modelo, simulación, optimización, visualización), `datos/`, `resultados/`, `tests/`, `docs/`.
2. Escribir `README.md` con pasos desde un entorno limpio: crear el entorno, instalar, obtener los datos, correr los experimentos y generar las gráficas.
3. `requirements.txt` con versiones fijas (numpy, pandas y matplotlib para el análisis; el modelo sigue sin depender de ellos).
4. Verificar la reproducción desde cero en una carpeta nueva.
5. Redactar el informe PDF siguiendo la estructura del documento y registrar contribuciones por integrante.
6. Preparar la presentación de 15 minutos con la demostración.
7. Citar los datasets, las herramientas y el uso de inteligencia artificial.

## Orden sugerido y puntos de control

| Punto de control | Se verifica |
|---|---|
| Después de Fase 2 | El autochequeo de `piso.py` pasa sin carreras ni póker |
| Después de Fase 3 | Los valores por defecto reproducen exactamente la línea base |
| Después de Fase 4 | Todos los juegos del piso tienen hold positivo documentado |
| Después de Fase 5A | El CSV de septiembre 2021 reproduce los valores de la tabla de verificación |
| Después de Fase 6 | Existe una tabla de MAE contra datos reales con hold-out |
| Después de Fase 7 | La solución del GA respeta el área, probado por código |
| Después de Fase 8 | Cada condición tiene 30 réplicas con semillas guardadas |
