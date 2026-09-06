# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A casino simulation used to study random-variable generation methods: five games (ruleta, dados,
tragamonedas, blackjack, carrera de caballos), an interactive mode to play them manually, and a Monte
Carlo simulation mode to analyze long-run behavior. Backend is Python/Flask (API only), frontend is
React/Vite. All prose, identifiers, and API fields are in Spanish — match that when adding code.

The core point of the project is methodological: **all randomness flows through a custom-built stack**,
never through `random`/`numpy`. See `backend/casino/rng.py`'s module docstring for the two-layer design
(a hand-rolled LCG as the uniform source, then inverse-transform and acceptance-rejection built on top of
it). `backend/casino/estadistica.py` reimplements the incomplete gamma function, normal CDF, and
Kolmogorov series by hand for this reason too — the project intentionally needs neither scipy nor numpy.
Don't casually introduce either as a dependency, or swap in `random`/`numpy.random` for convenience: that
would defeat the point of the whole codebase.

## Running it

Two terminals; backend and frontend are separate processes.

```bash
# Terminal 1 - backend
cd backend
python -m venv venv && source venv/bin/activate   # venv\Scripts\activate on Windows
pip install -r requirements.txt
python app.py                # http://127.0.0.1:5000
```

```bash
# Terminal 2 - frontend
cd frontend
npm install
npm run dev                  # http://localhost:5173, proxies /api/* to :5000 (see vite.config.js)
```

There is no test suite and no lint config in either half of the project — don't invent commands for
either.

### Docker

`docker-compose.yml` at the repo root builds `backend/Dockerfile` (gunicorn, `--workers 1` — required,
see below) and `frontend/Dockerfile` (Vite build served by nginx, proxying `/api/` to the backend
service). `docker compose up --build` serves the app on `http://localhost:8080`.

### Frontend commands

```bash
cd frontend
npm run build       # vite build
npm run preview     # preview a production build
```

## Architecture

### Backend: one global RNG, one process, in-memory state

`backend/app.py` is a single Flask app with no database. All game/player state lives in module-level
Python objects (`saldo_jugador`, `mesa_blackjack`, `hipodromo`), which only works because the process is
a single worker — **this is why the backend must always run with exactly one worker/process**
(`gunicorn --workers 1`, no `debug=True` with a reloader forking workers in prod, etc.). Adding real
concurrency would require moving this state out of module globals first.

`backend/casino/rng.py` holds one global `Generador` singleton (`GENERADOR`), switchable at runtime
between `"inversa"` and `"aceptacion_rechazo"` via `POST /api/generador`. Every game module function
takes an optional `generador=None` argument and resolves it to the global one via `rng.resolver(gen)` —
this is how changing the method from the frontend transparently changes how every game draws its random
numbers. When adding a new source of randomness, follow this same pattern (accept `generador=None`,
resolve against the global) rather than reaching for a local RNG.

Each `backend/casino/<juego>.py` module is self-contained: game rules/state transitions plus the
theoretical probability math needed to validate it (e.g. `ruleta.probabilidad_teorica`,
`tragamonedas.py`'s payout table derivation). `simulacion.py` is the Monte Carlo engine that runs games
many times headlessly for the simulation tab; `validacion.py` is what runs statistical tests
(chi-squared, KS, runs, autocorrelation) against generator output and compares the two generation
methods. When reworking a game's odds/payouts, keep the empirical (simulated) and theoretical numbers
in the module in sync — the README's "Resultados" section documents expected values and is the contract
those numbers are checked against.

Blackjack and carreras are stateful across multiple requests (a hand/race is several HTTP calls):
- Blackjack: `nueva` → (`pedir` | `doblar`)* → `plantarse`. While a hand is live, the dealer's hidden
  card is serialized as `"?"`.
- Carreras: `nueva` → (`soborno/dato` | `soborno/redbull`)* → `apostar` → `correr`. Horses' true speed/
  stamina are not revealed until the race runs; only the odds are visible before that.

See the README's "API" section for the full endpoint list and request bodies — it's kept up to date and
shouldn't be duplicated here.

### Frontend: tab-per-game, saldo lifted to the top

`App.jsx` owns `saldo` (fetched once from `/api/estado`) and the active tab; each game component
receives `onSaldoActualizado` and calls it with whatever saldo the play endpoint returns. `api.js` is a
thin fetch wrapper that throws on non-OK responses using the JSON body's `error` field — game components
catch that and render it as the result message.

The frontend currently only has tabs for ruleta, dados, tragamonedas, and simulación — blackjack and
carreras have full backend APIs but no React components yet (`Tabs.jsx` / `App.jsx` don't route to them).
When adding one, follow the existing pattern in e.g. `Ruleta.jsx` or `Dados.jsx`: local state for
bet inputs, a `jugar()` that POSTs and updates saldo + a `resultado` message, styled via the shared
classes in `App.css` (`.tab-panel`, `.form-fila`, `.resultado.gano`/`.perdio`) rather than new one-off
CSS.

`Ruleta.jsx`'s wheel is a pure-CSS `conic-gradient` disc (37 real wedges in true physical wheel order,
see `NUMEROS_DISCO`) with the ball animated via a separately-rotating track element and React state
(`anguloBola`), not DOM/keyframe injection — keep new animations in this codebase state-driven rather
than imperative DOM manipulation.
