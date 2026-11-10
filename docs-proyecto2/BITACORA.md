# Bitácora del Proyecto 2

Registro de lo hecho sobre el código del Proyecto 1, para retomar sin releer el chat. Branch: `proyecto-2` (sale de `main` en `bcc1540`; `main` no se tocó). Plan seguido: `PLAN_IMPLEMENTACION.md`. Instrucciones de origen: `02_instrucciones_reutilizar_codigo.md`.

**Estado: Fases 0–4 del documento 02 terminadas. Sigue la Fase 5 (lectores de datos Nevada / Grand Korea Leisure).**

Cómo ejecutar: desde `backend/`, `.venv/bin/python -m casino.piso` (autochequeo) y `.venv/bin/python app.py` (API en :5000); `cd frontend && npm run dev` (:5173). Scripts sueltos necesitan `PYTHONPATH=.` desde `backend/`.

## Fase 0 — Línea base (commit `línea base P1`)

- Se descartaron los cambios sin commitear de `main` (`README.md` y el guion de presentación de `Modelos.jsx`), por decisión del usuario.
- Se trabaja en una branch del mismo repo, no en un repo copiado.
- `linea_base_p1.json`: `simular_dia(horas=24, semilla=1)` con el código de P1 → 755 llegadas, 680 atendidos, 75 abandonos, ingreso 108,786.44. Sin las series largas (`esperas_min` y series por hora).

## Fase 1 — Borrar lo que no se usa

- Borrados `docker-compose.yml`, los dos `Dockerfile`, los dos `.dockerignore` y `frontend/nginx.conf`.
- `gunicorn` fuera de `backend/requirements.txt` (solo lo usaba Docker). Queda `Flask==3.0.3`.

## Fase 2 — Quitar carreras y póker

- Backend: borrados `carreras.py` y `poker.py`; limpiados `simulacion.py` (`JUEGOS` queda con 4 juegos, sin `m_cuotas`), `validacion.py` y `app.py` (sin rutas `/api/carreras/*` ni `/api/poker/*`). Se conservó `comparar_estrategias_blackjack`.
- Frontend: borrados `Carreras.jsx` y `Poker.jsx`; limpiados `App.jsx`, `Tabs.jsx`, `Simulacion.jsx`, `Modelos.jsx` (secciones 5 y 6) y `App.css` (bloques `.cr-*` y `.pk-*`). `Carta.jsx` se queda (Blackjack). En `Simulacion.jsx` también se quitó el aviso de "corrida lenta", que solo podían disparar esos dos juegos.
- `backend/casino/__init__.py` no existe (lo ignora `.gitignore`; `casino` es namespace package), así que el paso del documento 02 sobre ese archivo no aplica.
- Verificado: autochequeo OK, imports OK, `npm run build` limpio, rutas restantes responden 200 y las borradas 404.
- **Pendiente:** `README.md` todavía describe P1 (carreras, póker). Tiene una nota arriba; se reescribe en la Fase 10. No se hizo el rediseño de UI (`03_instrucciones_ui.md`), ni se cambió el prefijo "Q" de `Piso.jsx`.

## Fase 3 — Parámetros nuevos

- `llegadas.generar(..., tasa_por_hora=None, factor=1.0)`: la tasa efectiva es `tasa_por_hora[h] * factor`; `lambda_max` se calcula dentro.
- `piso.simular_dia(..., factor_llegadas=1.0, tasa_por_hora=None, paciencia_media_min=None)`; `ValueError` si factor o paciencia ≤ 0. La salida añade `factor_llegadas` y `paciencia_media_min`, y `tasa_por_hora` es la efectiva.
- `/api/piso` acepta `factor_llegadas` y `paciencia_media_min` (400 si son inválidos).
- No se parametrizaron bankroll ni estadía (punto opcional, sin uso todavía).
- **Punto de control cumplido:** con los valores por defecto el resultado es idéntico a `linea_base_p1.json` (0 claves distintas), con ambos métodos del generador.
- Sensibilidad, promedio de 8 semillas (1–8), 24 h:

| Cambio | Llegadas | P(abandono) |
|---|---|---|
| Base | 795 | 10.4% |
| `factor_llegadas=1.2` | 959 | 15.3% |
| `paciencia_media_min=4` | 795 | 10.8% |
| `paciencia_media_min=16` | 795 | 9.6% |

- **Hallazgos para el GA:** (1) el abandono casi no responde a la paciencia, lo domina la capacidad; (2) la configuración base ya está en ~10.4%, sobre el límite de 10% de la restricción; (3) una sola semilla no sirve para ver efectos (con semilla 1, paciencia 4 dio *menos* abandono): siempre promediar réplicas.

## Fase 4 — Hold de cada juego

Detalle y snippets en `hold_juegos.md`.

- **Dados:** todas las apuestas de P1 eran justas (EV 0), no solo `par_impar`. Se añadió la apuesta `"field"` (gana 2,3,4,9,10,11,12; 1:1, y 2:1 en 2 y 12) y el piso la usa: `_APUESTA_DADOS = ("field", None)`. Ventaja 1/18 = 5.56%. Las apuestas viejas siguen en la pestaña Dados.
- **Tragamonedas:** `PAGOS_TRIO` `[2, 3, 8, 50, 300]` → `[2, 3, 7, 40, 216]`. Ventaja 4.475% → 7.325% (Nevada sept. 2021: 7.32%). Afecta también a la pestaña interactiva.
- **Ruleta:** sin cambios, 2.70% (europea).
- **Blackjack:** medido, 200,000 manos, semilla 2024: hold 0.92%, IC 95% [0.48%, 1.37%].
- `_demo()` de `piso.py` ahora verifica los retornos teóricos de dados y tragamonedas y que `ingreso_teorico_por_juego` sea > 0 (esa clave no incluye blackjack).
- `linea_base_p2.json`: nueva referencia (semilla 1 → 755 llegadas, 695 atendidos, 60 abandonos, ingreso 88,102). Sustituye a la de P1 a partir de aquí.
- Hold empírico del piso (10 días): tragamonedas 7.14%, ruleta 1.77%, dados 6.07%, blackjack 0.39%.
- **Hallazgos para el GA:** (1) blackjack y ruleta dejan muy poco por apuesta frente a tragamonedas y dados; el GA tenderá a quitarles mesas, y en Nevada son los juegos con más win por unidad, así que la calibración (Fase 6) tendrá que revisar apuestas, ritmo de juego o reglas; (2) el ingreso diario es muy ruidoso (con semilla 1 la ruleta perdió 1,221 ese día; el ingreso total va de ~88,000 a ~160,000 según la semilla), lo que confirma la necesidad de réplicas y números aleatorios comunes en el fitness; (3) el win % de mesas de Nevada es sobre el drop y no se compara con la ventaja por apuesta: solo tragamonedas es comparable.

## Cómo se trabajó

Orquestación con Claude Code: un agente orquestador (plan, git, verificación, esta bitácora) y agentes Claude Sonnet para el código de las Fases 2, 3 y 4. Declarar este uso de IA en el informe.

## Siguiente

1. Fase 5/5A: `datos/crudos/`, script `nevada_a_csv.py` (requiere `pdftotext`), lector del CSV de Grand Korea Leisure (el archivo no es UTF-8, probablemente CP949; columnas de edad parecen conteos). Los archivos están en `~/Downloads` (`2021Sep-gri.pdf` y el CSV), aún no copiados al repo.
2. Fase 6: calibración. Fase 7: GA. Luego experimentos, gráficas, UI e informe.
