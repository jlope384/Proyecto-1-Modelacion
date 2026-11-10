# Proyecto 2 — Fases 0–4 de `02_instrucciones_reutilizar_codigo.md`

## Contexto

El Proyecto 2 (CC3074) reutiliza el casino del Proyecto 1 para optimizar el reparto del piso con un GA. Antes de datos, calibración y GA hay que dejar el código limpio y parametrizable. Este plan cubre **solo las Fases 1–4** del documento 02 (más la Fase 0 de línea base, que las otras necesitan para verificarse). Fuera de alcance: datos (5/5A), calibración (6), GA (7), experimentos, gráficas y rediseño de UI.

Decisiones del usuario:
- Trabajar en una branch nueva (`proyecto-2`) dentro de este repo, no en un repo copiado.
- **Descartar** los cambios sin commitear de `README.md` y `frontend/src/components/Modelos.jsx` (`git restore`).
- Dados con ventaja de la casa **y** tragamonedas ajustadas a ~7.32% (Nevada).
- Frontend/`app.py`: recorte mínimo (quitar carreras y póker para que todo arranque).
- Programan subagentes **Sonnet** (`model: "sonnet"`); yo solo orquesto, verifico y commiteo.

Hallazgos de la exploración que corrigen el documento 02:
- `backend/casino/__init__.py` **no existe** (`.gitignore` lo ignora): no hay nada que editar ahí.
- **Todas** las apuestas de `dados.py` son justas (`PAGOS_SUMA` son cuotas exactas, EV = 0), no solo `par_impar`. Hace falta una apuesta nueva.
- No hay tests; el único chequeo es `_demo()` de `casino/piso.py` (`python -m casino.piso`).
- Entorno: `backend/.venv` (Python 3.14); ejecutar siempre desde `backend/`.

## Orquestación

Yo (orquestador): git, línea base, verificación de cada punto de control, commits locales (sin push), bitácora. Agentes Sonnet, en este orden:

| Paso | Quién | Archivos |
|---|---|---|
| 0. Branch + línea base + docs | Orquestador | `docs-proyecto2/` |
| 1. Borrar Docker | Orquestador | 6 archivos Docker, `README.md` |
| 2a. Quitar carreras/póker backend | Agente Sonnet A | `backend/casino/simulacion.py`, `validacion.py`, `backend/app.py`, borra `carreras.py`, `poker.py` |
| 2b. Quitar carreras/póker frontend | Agente Sonnet B (en paralelo con A, archivos disjuntos) | `frontend/src/App.jsx`, `Tabs.jsx`, `Simulacion.jsx`, `Modelos.jsx`, `App.css`, borra `Carreras.jsx`, `Poker.jsx` |
| 3. Parametrizar | Agente Sonnet C | `backend/casino/llegadas.py`, `piso.py`, `app.py` (ruta `/api/piso`) |
| 4. Hold de juegos | Agente Sonnet D | `backend/casino/dados.py`, `tragamonedas.py`, `piso.py`, `docs-proyecto2/hold_juegos.md` |

Un commit por fase, tras verificar.

## Fase 0 — Branch y línea base

1. `git restore README.md frontend/src/components/Modelos.jsx` (descarta +97 líneas, incluido el guion de presentación de `Modelos.jsx`; decidido por el usuario).
2. `git switch -c proyecto-2`.
3. Crear `docs-proyecto2/` y copiar desde `~/Downloads` `00_contexto_proyecto2.md`, `01_plan_proyecto2.md`, `02_instrucciones_reutilizar_codigo.md`; añadir `PLAN_IMPLEMENTACION.md` (este plan) y `BITACORA.md` (qué se hizo, se actualiza al cerrar cada fase).
4. Línea base: `cd backend && .venv/bin/python -m casino.piso` (debe imprimir `piso.py: autochequeo OK`) y guardar en `docs-proyecto2/linea_base_p1.json` el resultado de `simular_dia(horas=24, semilla=1)` sin las series largas (`esperas_min`, series por hora). Esperado ≈ 755 llegadas, 680 atendidos, 75 abandonos, ingreso ≈ 108,786.
5. Commit "línea base P1".

## Fase 1 — Borrar lo que no se usa

- Borrar `docker-compose.yml`, `backend/Dockerfile`, `backend/.dockerignore`, `frontend/Dockerfile`, `frontend/.dockerignore`, `frontend/nginx.conf`.
- Quitar `gunicorn` de `backend/requirements.txt` (solo lo usaba Docker); `Flask` se queda.
- Quitar la sección Docker del `README.md`.
- `__pycache__/` ya está en `.gitignore`; borrar las carpetas locales.
- Verificar: autochequeo de piso sigue OK.

## Fase 2 — Quitar carreras y póker

Backend (agente A), siguiendo 02 §Fase 2 con estas líneas localizadas:
- `simulacion.py`: imports L15, `JUEGOS` L18, constantes L20-32, parámetro `m_cuotas` L36, ramas L85-102, notas L153-175, `retorno_teorico` L193-194. **Conservar** `comparar_estrategias_blackjack` (la usa `/api/simulacion/blackjack/estrategias` y `Modelos.jsx`).
- `validacion.py`: imports L40/L44, ramas de póker L125-128, L146-147, `MODOS_POKER` L158, L179-189, L246, lista de `comparar_todos` L443, `carreras.comparar_metodos` en `reporte_completo` L495-498.
- `app.py`: imports L7/L11, `hipodromo`/`mesa_poker` L33-34, su recreación en `/api/reiniciar` y `/api/generador`, rutas L263-459, topes y `m_cuotas` en `/api/simulacion` L485-500.
- Borrar `carreras.py`, `poker.py`; limpiar docstring de `piso.py` L18-21 y comentario `estadistica.py` L232.

Frontend (agente B):
- `App.jsx` L9-10, L38-39; `Tabs.jsx` L7-8; borrar `Carreras.jsx`, `Poker.jsx` (**`Carta.jsx` se queda**, la usa Blackjack).
- `Simulacion.jsx`: entradas de carreras/póker en `COSTO_MS`, `JUEGOS`, `ESTRATEGIAS`, `RESULTADOS`, cuerpo de petición y formularios L306-347.
- `Modelos.jsx`: `"poker"` de `JUEGOS_DISCRETOS`, comparación especial de carreras L164-188, secciones 5 y 6 (lógica L260-331 y JSX L640-~815), `<option value="carreras">`.
- `App.css`: bloques `.cr-*` y `.pk-*` (L1032-fin).

Verificar: `python -m casino.piso` OK; `python -c "from casino import validacion, simulacion; import app"`; `grep -rniE "carreras|poker|hipodromo" backend/ frontend/src` sin resultados; `npm run build` en `frontend/` sin errores; arrancar `python app.py` + `npm run dev` y comprobar en el navegador que las 7 pestañas restantes cargan y `/api/piso` responde.

## Fase 3 — Parametrizar llegadas y paciencia

- `llegadas.py`: `generar`, `_llegadas_inversa`, `_llegadas_adelgazamiento` (y los helpers `tasa`, `lambda_acumulada`) reciben `tasa_por_hora=None` y `factor=1.0`; `None` → `TASA_POR_HORA`; `lambda_max = max(tasa) * factor` calculado dentro, ya no el global `LAMBDA_MAX` (L44).
- `piso.py`: `simular_dia(..., factor_llegadas=1.0, tasa_por_hora=None, paciencia_media_min=None)`; L201 los pasa a `llegadas.generar`; L301 usa el parámetro o `PACIENCIA_MEDIA_MIN`; el dict de salida reporta la tasa y paciencia efectivamente usadas.
- `app.py` `/api/piso`: aceptar `factor_llegadas` y `paciencia_media_min` opcionales.
- Se omite el punto opcional (bankroll/estadía como parámetros): sin uso en estas fases.
- **Punto de control:** `simular_dia(horas=24, semilla=1)` con defaults debe ser **idéntico** a `linea_base_p1.json` (mismos enteros y floats). Además `factor_llegadas=1.2` → ~20% más llegadas; `paciencia_media_min=4` → más abandono.

## Fase 4 — Hold de cada juego

- **Dados:** añadir a `dados.py` la apuesta de una tirada `"field"` (gana con 2,3,4,9,10,11,12; paga 1:1, y 2:1 en 2 y 12) en `jugar`, `probabilidad_teorica` y `retorno_teorico` → ventaja de la casa **5.56%** (EV = −1/18). `piso.py` L95: `_APUESTA_DADOS = ("field", None)`. Las apuestas existentes (justas) no se tocan: las usa la pestaña Dados.
- **Tragamonedas:** `PAGOS_TRIO` de `[2, 3, 8, 50, 300]` a `[2, 3, 7, 40, 216]` → `retorno_teorico()` = **−7.325%** (Nevada: 7.32%). Verificado a mano: Σp³·pago = 0.28975, P(nada) = 0.363. Actualizar docstring.
- **Ruleta:** sin cambios, 2.70% (europea de un cero). Anotar.
- **Blackjack:** medir hold por simulación (≥200,000 manos con `jugar_mano`, estrategia básica, semilla fija) y registrar valor e IC.
- `docs-proyecto2/hold_juegos.md`: tabla juego / apuesta en el piso / hold teórico o simulado / referencia Nevada / nota (en mesas el win % de Nevada es sobre drop, no comparable).
- Ampliar `_demo()` de `piso.py` con asserts: `dados.retorno_teorico("field", None)` ≈ −1/18, `tragamonedas.retorno_teorico()` ≈ −0.07325 y todos los `ingreso_teorico_por_juego` > 0.
- Guardar nueva referencia `docs-proyecto2/linea_base_p2.json` (los números cambian respecto a P1 por diseño).
- **Punto de control:** los cuatro juegos del piso tienen hold positivo documentado; autochequeo OK.

## Verificación final

1. `cd backend && .venv/bin/python -m casino.piso` → `autochequeo OK` (incluye asserts nuevos de hold).
2. Identidad con línea base P1 comprobada al cerrar Fase 3 (antes de Fase 4).
3. `grep` de carreras/póker vacío; `npm run build` limpio; app levantada y pestañas revisadas en el navegador.
4. `git log` en `proyecto-2`: un commit por fase; `main` intacta.
5. `docs-proyecto2/BITACORA.md` describe por fase: qué se cambió, decisiones, valores medidos y qué sigue (Fase 5: datos Nevada/GKL).
