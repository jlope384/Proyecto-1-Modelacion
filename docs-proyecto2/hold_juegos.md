# Hold de los juegos del piso

Ventaja de la casa = ingreso de la casa / total apostado (por apuesta). El algoritmo genético necesita que todos los juegos del piso tengan ventaja positiva.

| Juego | Apuesta usada en el piso | Ventaja de la casa | Referencia Nevada (sept. 2021, win %) | Nota |
|---|---|---|---|---|
| Tragamonedas | 1 giro, 3 reels (`PAGOS_TRIO = [2,3,7,40,216]`) | 7.325 % (teórica, `tragamonedas.retorno_teorico()`) | 7.32 % | Comparable: win / dinero jugado. |
| Ruleta | `("color","rojo")`, europea de un cero | 2.70 % (teórica, `ruleta.retorno_teorico`) | 18.97 % | No comparable (ver nota). |
| Dados | `("field", None)` | 5.56 % (teórica, exactamente 1/18) | 16.39 % (craps) | No comparable (ver nota). |
| Blackjack | `estrategia="basica"`, `umbral=17` | 0.92 % (simulada, 200,000 manos), IC 95 % [0.48 %, 1.37 %] | 15.30 % | No comparable (ver nota). IC aproximado (trata la apuesta efectiva como casi constante). |

**Nota obligatoria:** en mesas el win percent de Nevada se calcula sobre el *drop* (fichas compradas), no sobre lo apostado. Por eso NO es comparable con la ventaja por apuesta del simulador; solo tragamonedas es comparable (ambos usan dinero jugado).

## Qué se cambió y por qué

- **Dados**: todas las apuestas existentes (`suma`, `par_impar`) son justas (EV = 0) y se dejaron intactas porque las usa la pestaña interactiva. Se añadió la apuesta de una tirada `"field"` (valor ignorado): gana con 2, 3, 4, 9, 10, 11, 12; paga 1:1, salvo 2 y 12 a 2:1; pierde con 5, 6, 7, 8. Retorno = (14·1 + 2·2 − 20)/36 = −1/18. El piso (`_APUESTA_DADOS`) pasó de `par_impar/par` a `field`.
- **Tragamonedas**: `PAGOS_TRIO` pasó de `[2,3,8,50,300]` (retorno −4.475 %) a `[2,3,7,40,216]`. Con PESOS [35,30,20,10,5], PAGO_PAR 0 y PAGO_NADA −1: Σp³·pago = 0.28975, P(nada) = 0.363, retorno = −0.07325.

## Blackjack: snippet reproducible (desde `backend/`)

```python
import math
from casino import blackjack, rng
gen = rng.Generador(semilla=2024)
zapato = blackjack.Zapato(gen)
N = 200_000
apostado = ingreso = 0.0
casa = []
for _ in range(N):
    d = blackjack.jugar_mano(10.0, zapato, estrategia="basica", umbral=17)
    apostado += d["apuesta"]          # doblar cuenta como apuesta mayor
    ingreso += -d["ganancia"]
    casa.append(-d["ganancia"])
hold = ingreso / apostado
m = ingreso / N
se = math.sqrt(sum((g - m) ** 2 for g in casa) / (N - 1) / N) / (apostado / N)
print(hold, hold - 1.96 * se, hold + 1.96 * se)   # 0.00922 [0.00477, 0.01367]
```

## Hold empírico del piso (10 días, `simular_dia(24, semilla=s)`, s = 1..10)

| Juego | Apostado | Ingreso | Ingreso/apostado | Teórico |
|---|---|---|---|---|
| Tragamonedas | 14,704,969 | 1,050,169 | 7.14 % | 7.325 % |
| Ruleta | 3,632,582 | 64,398 | 1.77 % | 2.70 % |
| Dados (field) | 1,325,208 | 80,457 | 6.07 % | 5.56 % |
| Blackjack | 4,331,916 | 17,087 | 0.39 % | sin forma cerrada (simulado 0.92 %) |

Las diferencias de ruleta y blackjack son ruido muestral y efecto de truncar sesiones (ruina/meta), con pocas rondas relativas a la varianza de esos juegos. Todos son positivos, aunque blackjack con estrategia básica deja un margen muy fino.
