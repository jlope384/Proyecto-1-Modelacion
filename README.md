# Casino - Modelación y Simulación

Proyecto que simula 3 juegos de casino (ruleta, dados y tragamonedas), con un modo
interactivo para jugar manualmente y un modo de simulación Monte Carlo que corre
muchas rondas automáticas para analizar el comportamiento del casino a largo plazo.

Backend en Python (Flask, solo API) + frontend en React (Vite).

## Estructura

```
backend/
  app.py              # servidor Flask con la API (/api/...)
  casino/
    ruleta.py         # lógica de la ruleta europea (0-36)
    dados.py          # lógica de dados (2 dados, suma o par/impar)
    tragamonedas.py   # lógica de tragamonedas (3 reels)
    simulacion.py     # motor de simulación Monte Carlo
  requirements.txt
frontend/
  src/
    App.jsx           # tabs + estado global del saldo
    api.js            # helper de fetch a la API
    components/
      Header.jsx
      Tabs.jsx
      Ruleta.jsx
      Dados.jsx
      Tragamonedas.jsx
      Simulacion.jsx  # gráfica con Chart.js (react-chartjs-2)
  vite.config.js      # proxy de /api hacia el backend (localhost:5000)
  package.json
```

## Cómo correrlo

Se necesitan **dos terminales** (backend y frontend corren por separado).

**Terminal 1 - backend:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate        # en Windows
pip install -r requirements.txt
python app.py
```
Levanta la API en `http://127.0.0.1:5000`.

**Terminal 2 - frontend:**
```bash
cd frontend
npm install
npm run dev
```
Levanta React en `http://localhost:5173`. El proxy configurado en `vite.config.js`
reenvía cualquier request a `/api/...` hacia el backend Flask, así que no hace
falta configurar CORS.

Abre `http://localhost:5173` en el navegador.

## Cómo funciona

- **Ruleta**: apuesta a color (rojo/negro), par/impar, o un número exacto (0-36).
- **Dados**: tira 2 dados, apuesta a la suma exacta (2-12) o a par/impar de la suma.
- **Tragamonedas**: 3 reels con 5 símbolos, paga si hay 2 o 3 iguales.
- **Simulación**: corre N rondas automáticas con una apuesta fija y muestra
  probabilidad de ganar, ganancia neta, retorno sobre lo apostado, y una gráfica
  de la evolución del saldo simulado (útil para ver la ventaja de la casa a largo plazo).

El saldo del jugador (modo interactivo) se guarda en memoria del backend y se
reinicia a 1000 con el botón "Reiniciar saldo" o al reiniciar el servidor Flask.
