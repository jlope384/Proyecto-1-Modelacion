"""Descarga los PDF mensuales del Nevada Gaming Control Board.

Uso (desde la raíz del repo):
    python src/datos/descargar_nevada.py datos/crudos/nevada 2023-01 2024-12 2021-09

Después de la carpeta van meses AAAA-MM leídos de dos en dos, cada par es un
rango "desde hasta": 2023-01 2024-12 baja los 24 meses, y un mes que queda solo
al final (2021-09) se baja solo. Los PDF se guardan
con el nombre original, por ejemplo 2021Sep-gri.pdf. Los que ya existen no se
vuelven a bajar. Solo usa la biblioteca estándar.
"""
import sys
import urllib.request
from pathlib import Path

URL = ("https://gaming.nv.gov/uploadedFiles/gamingnvgov/content/about/"
       "gaming-revenue/{nombre}")
MESES = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def meses_entre(desde, hasta):
    a, m = map(int, desde.split("-"))
    a2, m2 = map(int, hasta.split("-"))
    while (a, m) <= (a2, m2):
        yield a, m
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)


def nombre_pdf(anio, mes):
    return f"{anio}{MESES[mes - 1]}-gri.pdf"


def descargar(anio, mes, carpeta):
    nombre = nombre_pdf(anio, mes)
    destino = carpeta / nombre
    if destino.exists():
        return "ya estaba"
    req = urllib.request.Request(URL.format(nombre=nombre),
                                 headers={"User-Agent": "proyecto-uvg-cc3074"})
    with urllib.request.urlopen(req, timeout=60) as r:
        datos = r.read()
    if not datos.startswith(b"%PDF"):
        raise ValueError(f"{nombre}: la respuesta no es un PDF")
    destino.write_bytes(datos)
    return f"{len(datos) // 1024} KB"


def main(carpeta, *meses):
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    pedidos = []
    for i in range(0, len(meses), 2):
        par = meses[i:i + 2]
        pedidos.extend(meses_entre(par[0], par[-1]))
    for anio, mes in pedidos:
        try:
            print(f"{nombre_pdf(anio, mes)}: {descargar(anio, mes, carpeta)}")
        except Exception as e:  # sigue con los demás meses
            print(f"{nombre_pdf(anio, mes)}: ERROR {e}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], *sys.argv[2:])
