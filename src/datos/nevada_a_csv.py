"""Convierte los PDF mensuales del Nevada Gaming Control Board en un CSV largo.

Uso (desde la raíz del repo):
    python src/datos/nevada_a_csv.py datos/crudos/nevada datos/procesados/nevada_mensual.csv

Los PDF deben llamarse como el original, por ejemplo 2021Sep-gri.pdf. Requiere
`pdftotext` (poppler o xpdf; en Windows viene con Git for Windows).

Diferencias con el script de 02_instrucciones_reutilizar_codigo.md (Fase 5A):
- Se usa `pdftotext -raw`, no `-layout`. Con `-layout` las columnas de la tabla
  salen desordenadas (los números de una fila quedan en otras líneas); con
  `-raw` cada juego queda en una sola línea con sus 15 números.
- El bloque estatal no está en la página 1 sino en la 4 (antes van portada,
  introducción e índice), así que se leen las páginas 1 a 6.
"""
import csv
import re
import subprocess
import sys
from pathlib import Path

NUM = r"\(?-?[\d,]+(?:\.\d+)?\)?"
PERIODOS = ("mes", "3_meses", "12_meses")
CAMPOS = ("locales", "unidades", "win_miles", "cambio_pct", "win_pct")
MESES = {m: i for i, m in enumerate(
    "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), start=1)}
MESES_PERIODO = {"mes": 1, "3_meses": 3, "12_meses": 12}
ULTIMA_PAGINA = 6


def a_numero(tok):
    neg = tok.startswith("(") and tok.endswith(")")
    v = float(tok.strip("()").replace(",", ""))
    return -v if neg else v


def pdf_a_texto(ruta):
    salida = subprocess.run(
        ["pdftotext", "-raw", "-f", "1", "-l", str(ULTIMA_PAGINA), str(ruta), "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=True)
    return salida.stdout


def parsear(texto, mes):
    filas, seccion, en_bloque = [], None, False
    for linea in texto.splitlines():
        s = linea.strip()
        if s.startswith("Statewide - All Nonrestricted Locations"):
            en_bloque = True
            continue
        if not en_bloque:
            continue
        if s.startswith("Statewide - $") or s.startswith("Total Gaming"):
            break
        if s.startswith("Table, Counter and Card Games"):
            seccion = "mesas"
            continue
        if s.startswith("Slot Machines"):
            seccion = "tragamonedas"
            continue
        tokens = s.split()
        if seccion is None or len(tokens) < 16:
            continue
        if not all(re.fullmatch(NUM, t) for t in tokens[-15:]):
            continue  # filas incompletas (Other, Card Games) o texto
        juego = re.sub(r"\s*\(\d\)$", "", " ".join(tokens[:-15])).strip()
        nums = tokens[-15:]
        for i, per in enumerate(PERIODOS):
            vals = [a_numero(t) for t in nums[i * 5:(i + 1) * 5]]
            fila = {"mes": mes, "seccion": seccion, "juego": juego, "periodo": per}
            fila.update(zip(CAMPOS, vals))
            # win acumulado del periodo entre unidades promedio y meses
            fila["win_por_unidad_mes_miles"] = (
                round(fila["win_miles"] / fila["unidades"] / MESES_PERIODO[per], 4)
                if fila["unidades"] else None)
            filas.append(fila)
    return filas


def main(carpeta, salida):
    todas = []
    for pdf in sorted(Path(carpeta).glob("*-gri.pdf")):
        m = re.match(r"(\d{4})([A-Za-z]{3})", pdf.name)
        mes = f"{m[1]}-{MESES[m[2].title()]:02d}"
        filas = parsear(pdf_a_texto(pdf), mes)
        if not filas:
            print(f"AVISO: {pdf.name} no produjo filas, revisar formato")
        todas.extend(filas)
    todas.sort(key=lambda f: (f["mes"], f["seccion"]))  # orden estable por mes
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    with open(salida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(todas[0].keys()))
        w.writeheader()
        w.writerows(todas)
    print(f"{len(todas)} filas en {salida}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
