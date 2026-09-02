# Casino - Modelación y Simulación

Proyecto que simula 3 juegos de casino (ruleta, dados y tragamonedas), con un modo
interactivo para jugar manualmente y un modo de simulación Monte Carlo que corre
muchas rondas automáticas para analizar el comportamiento del casino a largo plazo.

## Estructura

```
backend/
  app.py              # servidor Flask (API + sirve el frontend)
  casino/
    ruleta.py         # lógica de la ruleta europea (0-36)
    dados.py          # lógica de dados (2 dados, suma o par/impar)
    tragamonedas.py   # lógica de tragamonedas (3 reels)
    simulacion.py     # motor de simulación Monte Carlo
  requirements.txt
frontend/
  index.html
  style.css
  app.js
```

## Cómo correrlo

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # en Windows
pip install -r requirements.txt
python app.py
```

Luego abre `http://127.0.0.1:5000` en el navegador. El mismo servidor Flask sirve
el frontend, así que no hace falta configurar otro servidor ni CORS.

## Cómo funciona

- **Ruleta**: apuesta a color (rojo/negro), par/impar, o un número exacto (0-36).
- **Dados**: tira 2 dados, apuesta a la suma exacta (2-12) o a par/impar de la suma.
- **Tragamonedas**: 3 reels con 5 símbolos, paga si hay 2 o 3 iguales.
- **Simulación**: corre N rondas automáticas con una apuesta fija y muestra
  probabilidad de ganar, ganancia neta, retorno sobre lo apostado, y una gráfica
  de la evolución del saldo simulado (útil para ver la ventaja de la casa a largo plazo).

El saldo del jugador (modo interactivo) se guarda en memoria del servidor y se
reinicia a 1000 con el botón "Reiniciar saldo" o al reiniciar el servidor.
