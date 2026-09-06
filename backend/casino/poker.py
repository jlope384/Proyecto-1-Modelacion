"""
Texas Hold'em como juego del casino: una mesa de hasta 4 asientos (el
jugador humano y 3 bots), con ciegas, las cuatro calles de apuesta
(preflop/flop/turn/river), fold/check/call/raise/all-in y botes laterales
(side pots) cuando alguien queda all-in.

Modelo de aleatoriedad
----------------------
La única fuente de azar es la carta que sale del mazo. Igual que el zapato de
blackjack, se modela como una extracción SIN reemplazo: `Mazo.sacar()` arma el
vector de probabilidades uniformes sobre las cartas que quedan y se lo pasa a
`rng.Generador.discreta`, así que el reparto también sirve para comparar
transformada inversa contra aceptación-rechazo (ver `validacion.py`).

Los bots no usan una tabla de estrategia fija como el blackjack: deciden
estimando su **equity por Monte Carlo** (qué fracción de las manos ganarían si
se completaran al azar las cartas que faltan) con el mismo generador de la
mesa. Es exactamente la misma idea que ya usa `carreras.py` para ponerle
precio a una carrera simulándola de antemano, aplicada aquí a una decisión de
apuesta en vez de a una cuota.

Simplificaciones deliberadas (como el blackjack, que no parte pares): el
tamaño mínimo de un raise es un incremento fijo respecto a la última subida en
vez de la regla completa de "reabrir la acción", y no hay antes ni straddle.
"""

import itertools
import math

from . import rng

# ---------------------------------------------------------------------------
# Cartas y mazo
# ---------------------------------------------------------------------------

RANGOS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
VALOR_DE_RANGO = {r: i + 2 for i, r in enumerate(RANGOS)}
RANGO_DE_VALOR = {v: r for r, v in VALOR_DE_RANGO.items()}
PALOS = ["picas", "corazones", "diamantes", "treboles"]

NOMBRES_CATEGORIA = {
    8: "escalera_color", 7: "poker", 6: "full", 5: "color", 4: "escalera",
    3: "trio", 2: "doble_par", 1: "par", 0: "carta_alta",
}


def carta_publica(carta):
    valor, palo = carta
    return {"rango": RANGO_DE_VALOR[valor], "palo": PALOS[palo]}


class Mazo:
    """
    Mazo de 52 cartas con muestreo sin reemplazo, mismo patrón que
    `blackjack.Zapato`: en cada extracción se arma el vector de
    probabilidades uniformes sobre las cartas restantes y se lo entrega al
    generador, en vez de barajar de antemano. Un mazo dura una mano.
    """

    def __init__(self, generador=None):
        self.gen = rng.resolver(generador)
        self.reiniciar()

    def reiniciar(self):
        self.cartas = [(v, p) for p in range(4) for v in range(2, 15)]
        self.repartidas = 0

    def sacar(self):
        n = len(self.cartas)
        if n == 0:
            raise ValueError("El mazo está vacío.")
        indice = self.gen.discreta([1.0 / n] * n)
        self.repartidas += 1
        return self.cartas.pop(indice)

    def sacar_n(self, n):
        return [self.sacar() for _ in range(n)]


# ---------------------------------------------------------------------------
# Evaluación de manos (sin librerías externas)
# ---------------------------------------------------------------------------


def evaluar_5(cartas):
    """
    Fuerza de 5 cartas como tupla comparable: (categoria, desempates...).
    Categoría más alta = mejor mano; a igual categoría, Python ya compara las
    tuplas de desempate en orden.
    """
    valores = sorted((c[0] for c in cartas), reverse=True)
    palos = [c[1] for c in cartas]
    es_color = len(set(palos)) == 1

    distintos = sorted(set(valores), reverse=True)
    escalera_alta = None
    if len(distintos) == 5:
        if distintos[0] - distintos[4] == 4:
            escalera_alta = distintos[0]
        elif distintos == [14, 5, 4, 3, 2]:  # escalera "rueda": A-2-3-4-5
            escalera_alta = 5

    conteos = {}
    for v in valores:
        conteos[v] = conteos.get(v, 0) + 1
    grupos = sorted(conteos.items(), key=lambda kv: (-kv[1], -kv[0]))
    formas = [n for _, n in grupos]
    ordenados = [v for v, _ in grupos]

    if escalera_alta is not None and es_color:
        return (8, escalera_alta)
    if formas[0] == 4:
        return (7, ordenados[0], ordenados[1])
    if formas[0] == 3 and len(formas) > 1 and formas[1] == 2:
        return (6, ordenados[0], ordenados[1])
    if es_color:
        return (5, *valores)
    if escalera_alta is not None:
        return (4, escalera_alta)
    if formas[0] == 3:
        return (3, *ordenados)
    if formas[0] == 2 and len(formas) > 1 and formas[1] == 2:
        return (2, *ordenados)
    if formas[0] == 2:
        return (1, *ordenados)
    return (0, *valores)


def evaluar_mejor(cartas):
    """La mejor mano de 5 entre las (2 a 7) cartas recibidas."""
    if len(cartas) <= 5:
        return evaluar_5(cartas)
    return max(evaluar_5(combo) for combo in itertools.combinations(cartas, 5))


def describir_mano(valor_evaluado):
    return NOMBRES_CATEGORIA[valor_evaluado[0]]


# ---------------------------------------------------------------------------
# Equity por Monte Carlo (lo que usan los bots para decidir)
# ---------------------------------------------------------------------------

M_EQUITY_BOT = 150


def estimar_equity(cartas_propias, board, n_oponentes, generador, m=M_EQUITY_BOT):
    """
    Fracción de bote que en promedio gana `cartas_propias` contra
    `n_oponentes` manos aleatorias, completando el board que falte.

    Se simulan `m` finales posibles repartiendo al azar (con el mismo
    generador de la mesa, así que también consume del método configurado)
    las cartas que faltan del board y las manos rivales, sin reemplazo entre
    sí. Un empate reparte medio punto, como el bote real.
    """
    gen = rng.resolver(generador)
    if n_oponentes <= 0:
        return 1.0
    conocidas = set(cartas_propias) | set(board)
    resto_base = [(v, p) for p in range(4) for v in range(2, 15) if (v, p) not in conocidas]
    faltan_board = 5 - len(board)
    necesarias = faltan_board + 2 * n_oponentes
    if necesarias > len(resto_base):
        return 0.5  # blindaje: no debería pasar con las mesas de este juego

    puntos = 0.0
    for _ in range(m):
        resto = list(resto_base)
        extra = []
        for _ in range(necesarias):
            n = len(resto)
            indice = gen.discreta([1.0 / n] * n)
            extra.append(resto.pop(indice))

        board_completo = board + extra[:faltan_board]
        mi_valor = evaluar_mejor(list(cartas_propias) + board_completo)

        mejor_rival = None
        for i in range(n_oponentes):
            mano_rival = extra[faltan_board + 2 * i: faltan_board + 2 * i + 2]
            valor_rival = evaluar_mejor(mano_rival + board_completo)
            if mejor_rival is None or valor_rival > mejor_rival:
                mejor_rival = valor_rival

        if mi_valor > mejor_rival:
            puntos += 1.0
        elif mi_valor == mejor_rival:
            puntos += 0.5
    return puntos / m


# ---------------------------------------------------------------------------
# Botes y side pots
# ---------------------------------------------------------------------------


def construir_botes(aportado_mano, en_mano):
    """
    Descompone lo aportado por cada asiento en la mano en botes por nivel,
    algoritmo estándar de side pots.

    `aportado_mano`: lista con lo que puso cada asiento en TODA la mano
    (todas las calles sumadas), incluidos los que se retiraron.
    `en_mano`: lista de bool, True si el asiento no se retiró (compite por
    los botes; los retirados igual pusieron fichas, así que su dinero entra
    en el bote pero ellos no son elegibles para ganarlo).

    Devuelve una lista de {"monto": ..., "elegibles": [asientos]} de menor a
    mayor nivel de aporte.
    """
    niveles = sorted({a for a in aportado_mano if a > 0})
    botes = []
    anterior = 0
    for nivel in niveles:
        contribuyentes = [s for s, a in enumerate(aportado_mano) if a >= nivel]
        monto = (nivel - anterior) * len(contribuyentes)
        if monto > 0:
            elegibles = [s for s in contribuyentes if en_mano[s]]
            botes.append({"monto": monto, "elegibles": elegibles})
        anterior = nivel
    return botes


def repartir_bote(monto, elegibles, valores):
    """
    Reparte `monto` entre los `elegibles` con mejor `valores[asiento]`.
    Empate parte el bote en partes iguales (las fichas son floats en este
    proyecto, como la apuesta de cualquier otro juego, así que no hace falta
    resolver restos de división entera).
    Devuelve {asiento: ganancia}.
    """
    mejor = max(valores[s] for s in elegibles)
    ganadores = [s for s in elegibles if valores[s] == mejor]
    base = monto / len(ganadores)
    return {s: base for s in ganadores}


# ---------------------------------------------------------------------------
# Una mano completa
# ---------------------------------------------------------------------------

CIEGA_PEQUENA = 5.0
CIEGA_GRANDE = 10.0


class ManoPoker:
    """
    Estado y motor de UNA mano de Texas Hold'em entre los asientos con stack
    positivo. `decisores[s]` es, para cada asiento, o bien `None` (el
    asiento decide desde afuera, vía `aplicar_accion`, y la mano se pausa ahí
    para esperarlo) o bien una función `(mano) -> (accion, monto)` que decide
    sola (los bots).

    Las acciones son:
        "fold"                     se retira
        "check"                    solo si no hay nada que igualar
        "call"                     iguala la apuesta actual (o va all-in si
                                    no le alcanza)
        ("raise", monto_total)     sube: `monto_total` es lo que el asiento
                                    quiere tener aportado en la calle (no el
                                    incremento), y puede ser un all-in
    """

    def __init__(self, n_asientos, stacks, boton, generador, decisores,
                 ciega_pequena=CIEGA_PEQUENA, ciega_grande=CIEGA_GRANDE,
                 m_equity=M_EQUITY_BOT):
        self.n = n_asientos
        self.stack = list(stacks)
        self.boton = boton
        self.gen = rng.resolver(generador)
        self.decisores = decisores
        self.cp = ciega_pequena
        self.cg = ciega_grande
        self.m_equity = m_equity

        self.activo = [s > 0 for s in stacks]  # participa en ESTA mano
        self.en_mano = list(self.activo)       # sigue sin retirarse
        self.all_in = [False] * self.n
        self.aportado_mano = [0.0] * self.n
        self.aportado_calle = [0.0] * self.n
        self.actuo_calle = [False] * self.n
        self.acciones = []  # historial [(asiento, calle, accion, monto)]

        self.mazo = Mazo(self.gen)
        self.cartas = [self.mazo.sacar_n(2) if self.activo[s] else [] for s in range(self.n)]
        self.board = []
        self.calle = "preflop"
        self.terminada = False
        self.ganadores = None   # {asiento: ganancia_neta} al terminar
        self.motivo_fin = None  # "fold" o "showdown"
        self.esperando = None   # asiento humano esperando decisión, o None

        self._postear_ciegas()
        self.incremento_minimo = self.cg
        self.turno = self._siguiente_activo(self._asiento_bb())
        self._avanzar()

    # -- utilidades de asientos ----------------------------------------------

    def _asiento_sb(self):
        return self._siguiente_activo(self.boton)

    def _asiento_bb(self):
        return self._siguiente_activo(self._asiento_sb())

    def _siguiente_activo(self, desde):
        for i in range(1, self.n + 1):
            s = (desde + i) % self.n
            if self.activo[s]:
                return s
        return None

    def _pendientes_por_actuar(self):
        return [s for s in range(self.n) if self.en_mano[s] and not self.all_in[s]]

    def _bote_total(self):
        return sum(self.aportado_mano)

    def _cobrar(self, asiento, monto):
        monto = min(monto, self.stack[asiento])
        self.stack[asiento] -= monto
        self.aportado_calle[asiento] += monto
        self.aportado_mano[asiento] += monto
        if self.stack[asiento] <= 1e-9:
            self.all_in[asiento] = True
        return monto

    def _postear_ciegas(self):
        sb, bb = self._asiento_sb(), self._asiento_bb()
        self._cobrar(sb, self.cp)
        self._cobrar(bb, self.cg)
        self.apuesta_actual = self.aportado_calle[bb]
        self.actuo_calle = [False] * self.n
        self.acciones.append((sb, "preflop", "ciega_pequena", self.cp))
        self.acciones.append((bb, "preflop", "ciega_grande", self.cg))

    # -- motor de turnos ------------------------------------------------------

    def _ronda_completa(self):
        pendientes = self._pendientes_por_actuar()
        if not pendientes:
            return True
        return all(
            abs(self.aportado_calle[s] - self.apuesta_actual) < 1e-9 and self.actuo_calle[s]
            for s in pendientes
        )

    def _solo_queda_uno(self):
        return sum(1 for s in range(self.n) if self.en_mano[s]) <= 1

    def _siguiente_calle(self):
        if self.calle == "preflop":
            self.board += self.mazo.sacar_n(3)
            self.calle = "flop"
        elif self.calle == "flop":
            self.board += self.mazo.sacar_n(1)
            self.calle = "turn"
        elif self.calle == "turn":
            self.board += self.mazo.sacar_n(1)
            self.calle = "river"
        else:
            return False
        self.apuesta_actual = 0.0
        self.incremento_minimo = self.cg
        self.aportado_calle = [0.0] * self.n
        self.actuo_calle = [False] * self.n
        self.turno = self._siguiente_activo(self.boton)
        return True

    def _avanzar(self):
        """Resuelve bots hasta que le toque a un humano o la mano termine."""
        while not self.terminada:
            if self._solo_queda_uno():
                self._terminar_por_retiro()
                return
            if self._ronda_completa():
                if not self._siguiente_calle():
                    self._showdown()
                    return
                continue
            s = self.turno
            if s is None or not self.en_mano[s] or self.all_in[s]:
                self.turno = self._siguiente_activo(s if s is not None else self.boton)
                continue
            decisor = self.decisores[s]
            if decisor is None:
                self.esperando = s
                return
            accion, monto = decisor(self)
            self._aplicar_accion(s, accion, monto)

    def aplicar_accion_externa(self, asiento, accion, monto=0.0):
        """La API llama aquí con la decisión del asiento humano en pausa."""
        if self.terminada:
            raise ValueError("La mano ya terminó.")
        if self.esperando != asiento:
            raise ValueError("No es el turno de ese asiento.")
        self.esperando = None
        self._aplicar_accion(asiento, accion, monto)
        self._avanzar()

    def _aplicar_accion(self, s, accion, monto):
        monto = float(monto or 0.0)
        a_pagar = self.apuesta_actual - self.aportado_calle[s]

        if accion == "fold":
            self.en_mano[s] = False
            self.actuo_calle[s] = True
        elif accion == "check":
            if a_pagar > 1e-9:
                raise ValueError("No se puede pasar: hay una apuesta que igualar.")
            self.actuo_calle[s] = True
        elif accion == "call":
            self._cobrar(s, max(0.0, a_pagar))
            self.actuo_calle[s] = True
        elif accion == "raise":
            tope = self.stack[s] + self.aportado_calle[s]
            monto_total = min(monto, tope)
            minimo = self.apuesta_actual + self.incremento_minimo
            es_all_in = abs(monto_total - tope) < 1e-9
            if monto_total <= self.apuesta_actual + 1e-9:
                raise ValueError("El raise debe superar la apuesta actual.")
            if monto_total < minimo - 1e-9 and not es_all_in:
                raise ValueError(f"El raise mínimo es {minimo}.")
            incremento = monto_total - self.apuesta_actual
            self._cobrar(s, monto_total - self.aportado_calle[s])
            if incremento >= self.incremento_minimo - 1e-9:
                self.incremento_minimo = incremento
            self.apuesta_actual = max(self.apuesta_actual, self.aportado_calle[s])
            for otro in range(self.n):
                if otro != s:
                    self.actuo_calle[otro] = False
            self.actuo_calle[s] = True
        else:
            raise ValueError(f"Acción inválida: {accion!r}")

        self.acciones.append((s, self.calle, accion, monto if accion == "raise" else a_pagar))
        self.turno = self._siguiente_activo(s)

    # -- resolución -----------------------------------------------------------

    def _terminar_por_retiro(self):
        ganador = next(s for s in range(self.n) if self.en_mano[s])
        self.stack[ganador] += self._bote_total()
        self.ganadores = {ganador: self._bote_total() - self.aportado_mano[ganador]}
        self.terminada = True
        self.motivo_fin = "fold"

    def _showdown(self):
        while len(self.board) < 5:
            self.board += self.mazo.sacar_n(1)
        valores = {
            s: evaluar_mejor(self.cartas[s] + self.board)
            for s in range(self.n) if self.en_mano[s]
        }
        botes = construir_botes(self.aportado_mano, self.en_mano)
        ganancia_neta = {s: -self.aportado_mano[s] for s in range(self.n) if self.activo[s]}
        for bote in botes:
            elegibles = [s for s in bote["elegibles"] if s in valores]
            if not elegibles:
                continue
            reparto = repartir_bote(bote["monto"], elegibles, valores)
            for s, monto in reparto.items():
                self.stack[s] += monto
                ganancia_neta[s] += monto
        self.ganadores = ganancia_neta
        self.terminada = True
        self.motivo_fin = "showdown"
        self.valores_mostrados = valores


# ---------------------------------------------------------------------------
# Bots: deciden con equity por Monte Carlo
# ---------------------------------------------------------------------------

ESTRATEGIAS = ("equity", "agresiva", "pasiva", "azar")


def _decisor(estrategia="equity", m_equity=M_EQUITY_BOT):
    """Fábrica de funciones decisoras compatibles con `ManoPoker.decisores`."""

    def decidir(mano):
        s = mano.turno
        gen = mano.gen
        a_pagar = mano.apuesta_actual - mano.aportado_calle[s]
        stack_disponible = mano.stack[s]

        if estrategia == "azar":
            # sin equity: sirve de control estadístico, como "azar" en carreras
            u = gen.uniforme_continua(0.0, 1.0)
            if a_pagar > 1e-9 and u < 0.2:
                return "fold", 0.0
            if u > 0.85 and stack_disponible > a_pagar:
                monto = mano.aportado_calle[s] + a_pagar + mano.cg
                return "raise", monto
            return ("call" if a_pagar > 1e-9 else "check"), 0.0

        n_oponentes = sum(
            1 for o in range(mano.n) if o != s and mano.en_mano[o]
        )
        equity = estimar_equity(mano.cartas[s], mano.board, n_oponentes, gen, m_equity)

        bote = mano._bote_total()
        pot_odds = a_pagar / (bote + a_pagar) if (bote + a_pagar) > 0 else 0.0
        ruido = gen.uniforme_continua(-0.07, 0.07)

        sesgo = {"agresiva": 0.12, "pasiva": -0.12}.get(estrategia, 0.0)
        margen_valor = 0.20 - sesgo   # cuánta equity de sobra pide para subir

        if a_pagar <= 1e-9:
            if equity > 0.55 + ruido - sesgo and stack_disponible > 0:
                monto = mano.aportado_calle[s] + max(mano.cg, bote * (0.5 + sesgo))
                return "raise", monto
            return "check", 0.0

        if equity + ruido < pot_odds:
            return "fold", 0.0
        if equity > pot_odds + margen_valor and stack_disponible > a_pagar:
            monto = mano.apuesta_actual + max(mano.cg, bote * (0.5 + sesgo))
            return "raise", monto
        return "call", 0.0

    return decidir


DECISORES_BOT = {e: _decisor(e) for e in ESTRATEGIAS}


# ---------------------------------------------------------------------------
# Interfaz compatible con la simulación del resto del casino
# ---------------------------------------------------------------------------

N_ASIENTOS = 4


def jugar_mano_automatica(apuesta, generador=None, estrategia="equity",
                          n_asientos=N_ASIENTOS, m_equity=M_EQUITY_BOT):
    """
    Juega una mano COMPLETA con los `n_asientos` decidiendo solos (el
    asiento 0 con `estrategia`, el resto con "equity"), misma forma que
    `ruleta.jugar` / `blackjack.jugar` para que `simulacion.py` trate al
    póker igual que a los demás juegos.

    `apuesta` es el stack con el que arranca CADA asiento en la mano (no hay
    stacks persistentes entre manos en este modo, para que cada ronda de la
    simulación sea independiente y reproducible).
    """
    gen = rng.resolver(generador)
    decisor_0 = DECISORES_BOT.get(estrategia, DECISORES_BOT["equity"])
    decisores = [decisor_0] + [DECISORES_BOT["equity"]] * (n_asientos - 1)
    stacks = [float(apuesta)] * n_asientos
    boton = gen.entero(0, n_asientos - 1)

    mano = ManoPoker(n_asientos, stacks, boton, gen, decisores, m_equity=m_equity)
    ganancia = mano.ganadores.get(0, 0.0)
    gano = ganancia > 0

    detalle = {
        "estrategia": estrategia,
        "calle_final": mano.calle,
        "motivo_fin": mano.motivo_fin,
        "bote": mano._bote_total(),
        "cartas_asiento_0": [carta_publica(c) for c in mano.cartas[0]],
        "board": [carta_publica(c) for c in mano.board],
        "gano": gano,
        "ganancia": ganancia,
        "apuesta": apuesta,
    }
    if mano.motivo_fin == "showdown" and 0 in mano.valores_mostrados:
        detalle["categoria_mano"] = describir_mano(mano.valores_mostrados[0])
    return detalle, gano, ganancia


# ---------------------------------------------------------------------------
# Mesa interactiva (el usuario juega desde el frontend)
# ---------------------------------------------------------------------------

STACK_INICIAL_BOT = 500.0
STACK_MINIMO_BOT = 100.0
HUMANO = 0


class MesaPoker:
    """
    Estado de una sesión de póker: el humano (asiento 0) compra fichas con
    saldo del casino y juega mano tras mano contra 3 bots, cuyo stack
    persiste entre manos (y se recarga solo si queda muy corto: son la banca
    de la casa, no dinero real del usuario).
    """

    def __init__(self, generador=None, n_asientos=N_ASIENTOS,
                ciega_pequena=CIEGA_PEQUENA, ciega_grande=CIEGA_GRANDE):
        self.gen = rng.resolver(generador)
        self.n = n_asientos
        self.cp = ciega_pequena
        self.cg = ciega_grande
        self.stack = [0.0] * self.n
        self.boton = -1  # se incrementa a 0 en la primera mano
        self.sentado = False
        self.mano = None
        self.mensaje = "Compra fichas para sentarte a la mesa."

    # -- mesa -----------------------------------------------------------------

    def comprar_fichas(self, monto):
        monto = float(monto)
        if monto <= 0:
            raise ValueError("El monto debe ser positivo.")
        if self.mano is not None and not self.mano.terminada:
            raise ValueError("No puedes comprar fichas con una mano en curso.")
        if not self.sentado:
            for s in range(1, self.n):
                self.stack[s] = STACK_INICIAL_BOT
            self.sentado = True
        self.stack[HUMANO] += monto
        self.mensaje = f"Compraste {monto:.2f} en fichas."
        return self.estado()

    def retirarse_mesa(self):
        """Cash out: devuelve el stack del humano (fuera del método, quien
        llama es responsable de acreditarlo al saldo del casino)."""
        if self.mano is not None and not self.mano.terminada:
            raise ValueError("No puedes retirarte con una mano en curso.")
        stack_final = self.stack[HUMANO]
        self.sentado = False
        self.stack = [0.0] * self.n
        self.boton = -1
        self.mano = None
        self.mensaje = "Te levantaste de la mesa."
        return stack_final

    # -- manos ------------------------------------------------------------

    def nueva_mano(self):
        if not self.sentado:
            raise ValueError("Compra fichas antes de jugar.")
        if self.mano is not None and not self.mano.terminada:
            raise ValueError("Ya hay una mano en curso.")
        if self.stack[HUMANO] <= 0:
            raise ValueError("No te quedan fichas: compra más para seguir jugando.")

        for s in range(1, self.n):
            if 0 < self.stack[s] < STACK_MINIMO_BOT:
                self.stack[s] = STACK_INICIAL_BOT

        self.boton = (self.boton + 1) % self.n
        decisores = [None] + [DECISORES_BOT["equity"]] * (self.n - 1)
        self.mano = ManoPoker(self.n, self.stack, self.boton, self.gen, decisores,
                              ciega_pequena=self.cp, ciega_grande=self.cg)
        self.stack = self.mano.stack  # la mano cobra las ciegas sobre esta misma lista
        self.mensaje = self._mensaje_de_turno()
        return self.estado()

    def actuar(self, accion, monto=0.0):
        if self.mano is None or self.mano.terminada:
            raise ValueError("No hay una mano en curso.")
        if self.mano.esperando != HUMANO:
            raise ValueError("No es tu turno.")
        self.mano.aplicar_accion_externa(HUMANO, accion, monto)
        self.mensaje = self._mensaje_de_turno()
        return self.estado()

    def _mensaje_de_turno(self):
        m = self.mano
        if m.terminada:
            if m.motivo_fin == "fold":
                return "Todos se retiraron menos un jugador: bote adjudicado sin showdown."
            return "Showdown: se revelan las manos y se reparte el bote."
        if m.esperando == HUMANO:
            a_pagar = m.apuesta_actual - m.aportado_calle[HUMANO]
            if a_pagar > 1e-9:
                return f"Tu turno: hay {a_pagar:.2f} para igualar."
            return "Tu turno: puedes pasar o apostar."
        return "Resolviendo turnos..."

    # -- estado ---------------------------------------------------------------

    def estado(self):
        if not self.sentado:
            return {"sentado": False, "mensaje": self.mensaje}

        m = self.mano
        asientos = []
        for s in range(self.n):
            fila = {
                "asiento": s,
                "es_humano": s == HUMANO,
                "stack": self.stack[s],
                "boton": m is not None and s == m.boton,
            }
            if m is not None:
                fila["en_mano"] = m.en_mano[s]
                fila["all_in"] = m.all_in[s]
                fila["aportado_mano"] = m.aportado_mano[s]
                fila["aportado_calle"] = m.aportado_calle[s]
                revelar = s == HUMANO or m.terminada
                fila["cartas"] = (
                    [carta_publica(c) for c in m.cartas[s]] if revelar and m.cartas[s]
                    else (["?", "?"] if m.cartas[s] else [])
                )
                if m.terminada and m.motivo_fin == "showdown" and s in getattr(m, "valores_mostrados", {}):
                    fila["categoria_mano"] = describir_mano(m.valores_mostrados[s])
            asientos.append(fila)

        estado = {
            "sentado": True,
            "asientos": asientos,
            "mensaje": self.mensaje,
        }
        if m is not None:
            estado.update({
                "mano_en_curso": not m.terminada,
                "calle": m.calle,
                "board": [carta_publica(c) for c in m.board],
                "bote": m._bote_total(),
                "apuesta_actual": m.apuesta_actual,
                "turno": m.esperando,
                "ciega_pequena": self.cp,
                "ciega_grande": self.cg,
            })
            if m.terminada:
                estado["ganancias"] = m.ganadores
                estado["motivo_fin"] = m.motivo_fin
        return estado
