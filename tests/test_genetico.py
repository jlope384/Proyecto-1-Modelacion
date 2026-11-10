"""Pruebas del GA sin simulación. Correr desde la raíz: python -m unittest discover tests"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from optimizacion import genetico as ga  # noqa: E402
from modelo import escenario as esc  # noqa: E402

BASE = ga.a_tupla(esc.piso_base())
AREA = ga.area(BASE)


class TestRestricciones(unittest.TestCase):
    def test_base_factible(self):
        self.assertTrue(ga.factible(BASE, AREA))

    def test_reparar_siempre_factible(self):
        al = random.Random(1)
        for _ in range(2000):
            mesas = {j: al.randint(-5, 40) for j in ga.MESAS}
            c = ga.reparar(mesas, AREA, al)
            self.assertTrue(ga.factible(c, AREA), (mesas, c))

    def test_operadores_producen_factibles(self):
        al = random.Random(2)
        pob = ga.poblacion_inicial(BASE, 30, AREA, al)
        self.assertTrue(all(ga.factible(c, AREA) for c in pob))
        for _ in range(500):
            a, b = al.sample(pob, 2)
            for h in ga.cruce_un_punto(a, b, al):
                self.assertTrue(ga.factible(ga.hijo(ga.mutar(h, 0.5, al), AREA, al), AREA))


class TestBusqueda(unittest.TestCase):
    def test_encuentra_optimo_conocido(self):
        objetivo = ga.reparar({"blackjack": 6, "ruleta": 3, "dados": 2}, AREA, random.Random(0))

        def evaluar(pob):
            return [-sum((x - y) ** 2 for x, y in zip(c, objetivo)) for c in pob]

        mejor, f, hist = ga.optimizar(evaluar, BASE, AREA, generaciones=60, estancamiento=60)
        self.assertEqual(mejor, objetivo)
        # el mejor global nunca empeora (elitismo)
        serie = [h["mejor_fitness_global"] for h in hist]
        self.assertEqual(serie, sorted(serie))


if __name__ == "__main__":
    unittest.main()
