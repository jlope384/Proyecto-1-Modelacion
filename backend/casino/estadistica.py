"""
Pruebas estadísticas para validar los generadores.

Todo está implementado a mano (gamma incompleta, erf, serie de Kolmogorov)
para no agregar dependencias: el proyecto sigue corriendo solo con Flask, y
además queda explícito de dónde sale cada p-valor.

Criterio de lectura en todas las pruebas: H0 es "el generador se comporta
como debería". Un p-valor alto NO prueba que el generador sea bueno, solo
dice que la prueba no encontró evidencia en contra. Un p-valor < 0.05 sí es
señal de problema.
"""

import math

NIVEL_SIGNIFICANCIA = 0.05


# ---------------------------------------------------------------------------
# Funciones especiales (para los p-valores)
# ---------------------------------------------------------------------------


def _log_gamma(x):
    """log Γ(x) por la aproximación de Lanczos."""
    coeficientes = [
        76.18009172947146, -86.50532032941677, 24.01409824083091,
        -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5,
    ]
    y = x
    tmp = x + 5.5
    tmp -= (x + 0.5) * math.log(tmp)
    serie = 1.000000000190015
    for c in coeficientes:
        y += 1
        serie += c / y
    return -tmp + math.log(2.5066282746310005 * serie / x)


def _gamma_inc_p_serie(a, x):
    """P(a, x) por desarrollo en serie (converge rápido si x < a+1)."""
    if x <= 0:
        return 0.0
    ap = a
    suma = 1.0 / a
    termino = suma
    for _ in range(1000):
        ap += 1
        termino *= x / ap
        suma += termino
        if abs(termino) < abs(suma) * 1e-15:
            break
    return suma * math.exp(-x + a * math.log(x) - _log_gamma(a))


def _gamma_inc_q_fraccion(a, x):
    """Q(a, x) = 1 - P(a, x) por fracción continua (mejor si x >= a+1)."""
    diminuto = 1e-300
    b = x + 1.0 - a
    c = 1.0 / diminuto
    d = 1.0 / b
    h = d
    for i in range(1, 1000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < diminuto:
            d = diminuto
        c = b + an / c
        if abs(c) < diminuto:
            c = diminuto
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - _log_gamma(a)) * h


def _gamma_inc_q(a, x):
    """Gamma incompleta superior regularizada Q(a, x)."""
    if x < 0 or a <= 0:
        raise ValueError("Argumentos inválidos en la gamma incompleta.")
    if x == 0:
        return 1.0
    if x < a + 1.0:
        return 1.0 - _gamma_inc_p_serie(a, x)
    return _gamma_inc_q_fraccion(a, x)


def p_valor_chi2(estadistico, grados_libertad):
    """P(X > estadistico) para X ~ chi-cuadrado con esos grados de libertad."""
    if grados_libertad <= 0:
        return float("nan")
    return _gamma_inc_q(grados_libertad / 2.0, estadistico / 2.0)


def phi(z):
    """Función de distribución acumulada de la normal estándar."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def p_valor_z_bilateral(z):
    return 2.0 * (1.0 - phi(abs(z)))


def _p_valor_kolmogorov(lam):
    """Serie asintótica Q_KS(λ) = 2 Σ (-1)^{j-1} e^{-2 j² λ²}."""
    if lam <= 0:
        return 1.0
    suma = 0.0
    signo = 1.0
    for j in range(1, 101):
        termino = signo * math.exp(-2.0 * j * j * lam * lam)
        suma += termino
        if abs(termino) < 1e-12:
            break
        signo = -signo
    return max(0.0, min(1.0, 2.0 * suma))


# ---------------------------------------------------------------------------
# Pruebas
# ---------------------------------------------------------------------------


def prueba_chi2(observados, esperados, parametros_estimados=0, etiquetas=None):
    """
    Bondad de ajuste chi-cuadrado.

        X² = Σ (O_i - E_i)² / E_i,  con k - 1 - p grados de libertad

    Se agrupan (por índice) las categorías con esperado < 5, porque con
    esperados muy chicos la aproximación chi-cuadrado deja de valer.
    """
    obs = list(observados)
    esp = list(esperados)
    if len(obs) != len(esp):
        raise ValueError("Observados y esperados deben tener el mismo tamaño.")

    categorias = []
    obs_acum = 0.0
    esp_acum = 0.0
    nombres_acum = []
    for i, (o, e) in enumerate(zip(obs, esp)):
        nombre = etiquetas[i] if etiquetas else str(i)
        obs_acum += o
        esp_acum += e
        nombres_acum.append(nombre)
        if esp_acum >= 5.0:
            categorias.append((("+".join(nombres_acum)), obs_acum, esp_acum))
            obs_acum = 0.0
            esp_acum = 0.0
            nombres_acum = []
    if nombres_acum:  # sobrante: se pega a la última categoría
        if categorias:
            nombre, o, e = categorias[-1]
            categorias[-1] = (nombre + "+" + "+".join(nombres_acum), o + obs_acum, e + esp_acum)
        else:
            categorias.append(("+".join(nombres_acum), obs_acum, esp_acum))

    estadistico = sum((o - e) ** 2 / e for _, o, e in categorias if e > 0)
    gl = max(1, len(categorias) - 1 - parametros_estimados)
    p = p_valor_chi2(estadistico, gl)

    return {
        "prueba": "Chi-cuadrado de bondad de ajuste",
        "hipotesis_nula": "Los valores generados siguen la distribución teórica",
        "estadistico": estadistico,
        "grados_libertad": gl,
        "p_valor": p,
        "categorias_usadas": len(categorias),
        "agrupo_categorias": len(categorias) != len(obs),
        "rechaza_h0": p < NIVEL_SIGNIFICANCIA,
        "conclusion": _conclusion(p, "el ajuste a la distribución teórica"),
        "detalle": [
            {"categoria": n, "observado": o, "esperado": e} for n, o, e in categorias
        ],
    }


def prueba_uniformidad_chi2(muestra, n_intervalos=20):
    """Chi-cuadrado sobre U(0,1): se parte [0,1) en intervalos iguales."""
    n = len(muestra)
    conteos = [0] * n_intervalos
    for u in muestra:
        idx = int(u * n_intervalos)
        if idx >= n_intervalos:
            idx = n_intervalos - 1
        conteos[idx] += 1
    esperados = [n / n_intervalos] * n_intervalos
    resultado = prueba_chi2(conteos, esperados)
    resultado["prueba"] = f"Chi-cuadrado de uniformidad ({n_intervalos} intervalos)"
    resultado["hipotesis_nula"] = "Los uniformes se distribuyen U(0,1)"
    resultado["conclusion"] = _conclusion(resultado["p_valor"], "la uniformidad")
    resultado["histograma"] = conteos
    return resultado


def prueba_ks_uniforme(muestra):
    """
    Kolmogorov-Smirnov contra U(0,1): mide la distancia máxima entre la
    acumulada empírica y F(x) = x. Complementa al chi-cuadrado porque no
    depende de cómo se elijan los intervalos.
    """
    n = len(muestra)
    if n == 0:
        raise ValueError("Muestra vacía.")
    ordenada = sorted(muestra)
    d_mas = max((i + 1) / n - u for i, u in enumerate(ordenada))
    d_menos = max(u - i / n for i, u in enumerate(ordenada))
    d = max(d_mas, d_menos)
    lam = (math.sqrt(n) + 0.12 + 0.11 / math.sqrt(n)) * d
    p = _p_valor_kolmogorov(lam)
    return {
        "prueba": "Kolmogorov-Smirnov contra U(0,1)",
        "hipotesis_nula": "Los uniformes se distribuyen U(0,1)",
        "estadistico": d,
        "n": n,
        "p_valor": p,
        "rechaza_h0": p < NIVEL_SIGNIFICANCIA,
        "conclusion": _conclusion(p, "la uniformidad"),
    }


def prueba_rachas(muestra):
    """
    Prueba de rachas arriba-abajo: cuenta cuántas veces la secuencia cambia
    de dirección. Detecta dependencia serial, que el chi-cuadrado y el KS no
    ven (una secuencia perfectamente ordenada 0, 0.001, 0.002, ... pasa la
    prueba de uniformidad y falla ésta).

        E[R] = (2n - 1)/3,  Var[R] = (16n - 29)/90,  Z = (R - E[R])/sd
    """
    n = len(muestra)
    if n < 20:
        raise ValueError("La prueba de rachas necesita al menos 20 valores.")
    rachas = 1
    subiendo = muestra[1] > muestra[0]
    for i in range(1, n - 1):
        nuevo_subiendo = muestra[i + 1] > muestra[i]
        if nuevo_subiendo != subiendo:
            rachas += 1
            subiendo = nuevo_subiendo
    esperado = (2 * n - 1) / 3.0
    varianza = (16 * n - 29) / 90.0
    z = (rachas - esperado) / math.sqrt(varianza)
    p = p_valor_z_bilateral(z)
    return {
        "prueba": "Rachas arriba-abajo (independencia)",
        "hipotesis_nula": "Los valores son independientes entre sí",
        "rachas_observadas": rachas,
        "rachas_esperadas": esperado,
        "estadistico": z,
        "p_valor": p,
        "rechaza_h0": p < NIVEL_SIGNIFICANCIA,
        "conclusion": _conclusion(p, "la independencia"),
    }


def prueba_autocorrelacion(muestra, retardo=1):
    """
    Autocorrelación al retardo k. Bajo independencia el coeficiente se
    distribuye aproximadamente N(0, 1/m), con m el número de pares usados.
    """
    n = len(muestra)
    if n <= retardo + 2:
        raise ValueError("Muestra demasiado corta para ese retardo.")
    media = sum(muestra) / n
    num = sum((muestra[i] - media) * (muestra[i + retardo] - media) for i in range(n - retardo))
    den = sum((u - media) ** 2 for u in muestra)
    rho = num / den if den else 0.0
    m = n - retardo
    z = rho * math.sqrt(m)
    p = p_valor_z_bilateral(z)
    return {
        "prueba": f"Autocorrelación (retardo {retardo})",
        "hipotesis_nula": f"No hay correlación entre u_i y u_(i+{retardo})",
        "retardo": retardo,
        "coeficiente": rho,
        "estadistico": z,
        "p_valor": p,
        "rechaza_h0": p < NIVEL_SIGNIFICANCIA,
        "conclusion": _conclusion(p, "la ausencia de correlación serial"),
    }


def prueba_medias(muestra):
    """
    La media de U(0,1) debe ser 0.5 y la varianza 1/12. Es la prueba más
    barata y la primera que se revienta si el generador está mal escalado.
    """
    n = len(muestra)
    media = sum(muestra) / n
    varianza = sum((u - media) ** 2 for u in muestra) / (n - 1)
    z = (media - 0.5) / math.sqrt((1.0 / 12.0) / n)
    p = p_valor_z_bilateral(z)
    return {
        "prueba": "Media y varianza teóricas de U(0,1)",
        "hipotesis_nula": "La media poblacional es 0.5",
        "media_observada": media,
        "media_teorica": 0.5,
        "varianza_observada": varianza,
        "varianza_teorica": 1.0 / 12.0,
        "estadistico": z,
        "p_valor": p,
        "rechaza_h0": p < NIVEL_SIGNIFICANCIA,
        "conclusion": _conclusion(p, "la media teórica"),
    }


def _conclusion(p, que):
    if p < NIVEL_SIGNIFICANCIA:
        return (
            f"p = {p:.4f} < 0.05: se rechaza H0, hay evidencia en contra de {que}."
        )
    return (
        f"p = {p:.4f} >= 0.05: no se rechaza H0, los datos son compatibles con {que}."
    )
