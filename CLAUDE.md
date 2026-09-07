# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A casino simulation used to study random-variable generation methods. The centerpiece is **the
floor** (`backend/casino/piso.py`): a discrete-event system where players arrive via a
non-homogeneous Poisson process, queue for a finite-capacity resource (slots/roulette/blackjack/
dice), get served by playing real rounds of that game, and depart by busting, hitting a cashout
goal, running out of patience in the queue, or running out of time. That's what turns "a bunch of
casino games" into the arrivals-and-departures system the course project asks for — see the
README's "El sistema simulado" section. Six games exist in total (ruleta, dados, tragamonedas,
blackjack, carrera de caballos, Texas Hold'em); only the first four are part of the floor (see
`piso.py`'s docstring for why carreras/poker are excluded). All six can also be played
interactively or run standalone through the Monte Carlo simulation mode (`simulacion.py`), which
estimates house-edge/odds per game and does **not** model queueing — that's the floor's job.
Backend is Python/Flask (API only), frontend is React/Vite. All prose, identifiers, and API fields
are in Spanish — match that when adding code.

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

`piso.py` is the system layer: an event calendar built on stdlib `heapq` (arrival / end-of-service /
queue-abandonment events), sitting on top of the existing game modules rather than reimplementing
them — a floor customer's session is resolved by calling the real `ruleta.jugar` / `dados.jugar` /
`tragamonedas.jugar` / `blackjack.jugar_mano`. It reuses `llegadas.py` for arrivals and only adds
new *parameters* (bankroll, bet fraction, session duration, queue patience — all `Generador.triangular`
/ `.exponencial` draws), no new RNG methods. Keep it that way: if a floor tweak needs a new kind of
random draw, it almost certainly belongs in `rng.py` as a third case of an existing method, not as
a one-off `random.random()` call in `piso.py`.

### Frontend: tab-per-game, saldo lifted to the top

`App.jsx` owns `saldo` (fetched once from `/api/estado`) and the active tab; each game component
receives `onSaldoActualizado` and calls it with whatever saldo the play endpoint returns. `api.js` is a
thin fetch wrapper that throws on non-OK responses using the JSON body's `error` field — game components
catch that and render it as the result message.

The frontend has a tab per game (`Ruleta.jsx`, `Dados.jsx`, `Tragamonedas.jsx`, `Blackjack.jsx`,
`Carreras.jsx`, `Poker.jsx`) plus `Simulacion.jsx` (Monte Carlo), `Modelos.jsx` (RNG validation —
"La casa por dentro") and `Piso.jsx` (the system: KPIs, queues, method comparison — "El piso",
the default/first tab). When adding a game tab, follow the pattern in e.g. `Ruleta.jsx` or
`Dados.jsx`: local state for bet inputs, a `jugar()` that POSTs and updates saldo + a `resultado`
message. When adding a data/analysis tab, follow `Modelos.jsx` or `Piso.jsx` instead: no saldo,
just controls + `stats-grid` + charts. Either way, style via the shared classes in `App.css`
(`.tab-panel`, `.form-fila`, `.resultado.gano`/`.perdio`, `.stats-grid`, `.grafica-caja`/`.grafica-par`)
rather than new one-off CSS.

`Ruleta.jsx`'s wheel is a pure-CSS `conic-gradient` disc (37 real wedges in true physical wheel order,
see `NUMEROS_DISCO`) with the ball animated via a separately-rotating track element and React state
(`anguloBola`), not DOM/keyframe injection — keep new animations in this codebase state-driven rather
than imperative DOM manipulation.
