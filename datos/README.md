# Datos

Todo se regenera desde la raíz del repo con Python 3 (solo biblioteca estándar) y `pdftotext` (poppler o xpdf; en Windows viene con Git for Windows):

```bash
python src/datos/descargar_nevada.py datos/crudos/nevada 2023-01 2024-12 2021-09
python src/datos/nevada_a_csv.py datos/crudos/nevada datos/procesados/nevada_mensual.csv
python src/datos/nevada_referencia.py datos/procesados/nevada_mensual.csv datos/procesados/nevada_referencia.csv
python src/datos/gkl_a_csv.py "datos/crudos/gkl/그랜드코리아레저(주)_일별 방문고객 정보_20260618.csv" datos/procesados
```

Los PDF de Nevada no se versionan (25 archivos, ~11 MB): se bajan con el primer comando. El CSV de Grand Korea Leisure sí se versiona, porque data.go.kr pide entrar al portal para descargarlo.

## Archivos y etiqueta

| Archivo | Etiqueta | Fuente y periodo |
|---|---|---|
| `crudos/nevada/*-gri.pdf` | Dato público de referencia | Nevada Gaming Control Board, Monthly Revenue Report. 2023-01 a 2024-12 y 2021-09. Descargados el 2026-11-09 de `gaming.nv.gov/uploadedFiles/gamingnvgov/content/about/gaming-revenue/AAAAMmm-gri.pdf`. |
| `crudos/gkl/그랜드코리아레저(주)_일별 방문고객 정보_20260618.csv` | Dato real observado | Grand Korea Leisure, visitantes diarios, data.go.kr dataset 15116743, versión 2026-06-18. 2015-01-01 a 2026-06-23, 119,670 filas, codificación CP949. |
| `procesados/nevada_mensual.csv` | Dato público de referencia (transformado) | Tabla "Statewide - All Nonrestricted Locations" de cada PDF, una fila por mes, juego y periodo (mes, 3 y 12 meses). |
| `procesados/nevada_referencia.csv` | Dato público de referencia (derivado) | Métricas de calibración (2023) y validación (2024) para los cuatro juegos del modelo. |
| `procesados/gkl_diario.csv` | Dato real observado (agregado) | Visitantes por día y sucursal. Marca `excluido=1` en 2020-2022. |
| `procesados/gkl_resumen_anual.csv` | Dato real observado (agregado) | Promedio diario por año y sucursal. |
| `procesados/gkl_dia_semana.csv` | Dato real observado (agregado) | Promedio y factor por día de la semana, 2023 (calibración) y 2024 (validación). |

Kangwon Land (usuarios por tipo de juego, data.go.kr 15121887): la página devuelve 404 (2026-11-09). Se omite; la mezcla de juegos sale de Nevada.

## Notas de cada fuente

**Nevada**

- Columnas de `nevada_mensual.csv`: `mes` (AAAA-MM del informe), `seccion` (mesas o tragamonedas), `juego`, `periodo` (mes, 3_meses, 12_meses), `locales`, `unidades`, `win_miles` (miles de USD acumulados en el periodo), `cambio_pct`, `win_pct`, `win_por_unidad_mes_miles` (win / unidades promedio / meses del periodo).
- Verificado con septiembre 2021 (periodo `mes`): Twenty One 1,933 unidades, 92,180, 15.30%, 47.69; Roulette 508, 42,574, 18.97%, 83.81; Craps 328, 37,684, 16.39%, 114.89; tragamonedas 122,446, 780,520, 7.32%, 6.37; tragamonedas / (mesas + tragamonedas) = 67.4%. Coincide con la tabla de `docs-proyecto2/02_instrucciones_reutilizar_codigo.md`.
- Chequeo cruzado: el agregado de 2023 de `nevada_referencia.csv` coincide con la fila "12 meses" del informe de diciembre 2023 (blackjack 55.32 contra 55.32 miles/unidad/mes; tragamonedas 6.868 contra 6.868; ruleta y dados difieren menos de 0.3%, porque Nevada redondea las unidades promedio).
- Se ignoran las filas que no traen los 15 números (`Card Games`, `Other`, y `Pai Gow` en 2023-04, sin "% cambio"). Ninguna es un juego del modelo.
- En mesas el win percent de Nevada es sobre el drop, no sobre lo apostado: no se compara con el hold del simulador. Solo el de tragamonedas es comparable.
- Mapeo al modelo: Twenty One → blackjack, Roulette → ruleta, Craps → dados, fila `Total` de Slot Machines → tragamonedas.

**Grand Korea Leisure**

- Columnas: fecha, código y nombre de sucursal (CX Coex, HT Dragon City, LT Lotte Busan), sexo (M, F, X), país del pasaporte y cinco columnas de edad (60+, 50s, 40s, 30s, 20s). Las columnas de edad son conteos enteros: visitantes del día = suma de las cinco columnas sobre todas las filas.
- Solo trae días, no horas: el perfil horario de llegadas del modelo sigue siendo un supuesto.
- Se excluyen 2020-2022: cierres por COVID en 2020-2021 y en 2022 el promedio diario fue 1,502, un 35% del de 2019 (4,333). 2023 (2,331) y 2024 (2,702) ya son estables.
- Es un casino solo para extranjeros: se usan patrones (factores por día de semana) y proporciones, no montos absolutos.
- Los días sin fila para una sucursal se tratan como cerrados y no entran en promedios.
