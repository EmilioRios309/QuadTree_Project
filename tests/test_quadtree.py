"""Pruebas de correctitud del Quadtree.  Ejecutar:  python -m unittest discover -s tests -v"""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quadtree import (comprimir_y_evaluar, construir_quadtree, deserializar,  # noqa: E402
                      dividir_region, estadisticas_arbol, generar_imagen, mse,
                      recorrer_hojas, reconstruir, serializar)


def imagen_por_bloques(rng, alto, ancho, canales, niveles=3):
    """Imagen aleatoria con pocos valores distintos (genera regiones uniformes)."""
    base = rng.integers(0, niveles, size=(alto // 4 + 1, ancho // 4 + 1, canales)) * 80
    img = np.kron(base, np.ones((4, 4, 1), dtype=np.int64))[:alto, :ancho]
    ruido = (rng.random((alto, ancho, canales)) < 0.05) * rng.integers(0, 50, (alto, ancho, canales))
    return np.clip(img + ruido, 0, 255).astype(np.uint8)


class PruebasParticion(unittest.TestCase):
    def test_cobertura_exacta_sin_solapes(self):
        for ancho in range(1, 21):
            for alto in range(1, 21):
                if ancho * alto == 1:
                    continue
                marca = np.zeros((alto, ancho), dtype=int)
                subs = dividir_region(0, 0, ancho, alto)
                for (x, y, w, h) in subs:
                    self.assertGreater(w, 0)
                    self.assertGreater(h, 0)                    # nunca regiones vacías
                    self.assertLess(w * h, ancho * alto)        # el problema siempre decrece
                    marca[y:y + h, x:x + w] += 1
                self.assertTrue(np.all(marca == 1), f"{ancho}x{alto}")

    def test_cantidad_de_hijos(self):
        self.assertEqual(len(dividir_region(0, 0, 8, 8)), 4)
        self.assertEqual(len(dividir_region(0, 0, 1, 7)), 2)
        self.assertEqual(len(dividir_region(0, 0, 7, 1)), 2)
        self.assertEqual(len(dividir_region(0, 0, 2, 1)), 2)
        self.assertEqual(len(dividir_region(0, 0, 3, 3)), 4)

    def test_region_1x1_no_se_divide(self):
        with self.assertRaises(ValueError):
            dividir_region(3, 3, 1, 1)


class PruebasConstruccion(unittest.TestCase):
    def test_imagen_uniforme_es_una_hoja(self):
        img = generar_imagen("uniforme", 64)
        raiz = construir_quadtree(img, 0)
        self.assertTrue(raiz.es_hoja)
        self.assertEqual(estadisticas_arbol(raiz)["nodos"], 1)

    def test_sin_perdida_con_tolerancia_cero(self):
        rng = np.random.default_rng(1)
        for (h, w) in [(1, 1), (1, 9), (9, 1), (13, 7), (31, 33), (64, 64), (50, 75)]:
            for c in (1, 3):
                for img in (imagen_por_bloques(rng, h, w, c),
                            rng.integers(0, 256, (h, w, c), dtype=np.uint8)):
                    for metodo in ("directo", "integral"):
                        raiz = construir_quadtree(img, 0, metodo)
                        rec = reconstruir(raiz, h, w, c)
                        self.assertTrue(np.array_equal(img, rec), f"{h}x{w}x{c} {metodo}")

    def test_hojas_cubren_la_imagen_exactamente(self):
        rng = np.random.default_rng(2)
        img = imagen_por_bloques(rng, 37, 53, 3)
        for tol in (0, 30, 400):
            raiz = construir_quadtree(img, tol)
            marca = np.zeros((37, 53), dtype=int)
            for hoja in recorrer_hojas(raiz):
                marca[hoja.y:hoja.y + hoja.alto, hoja.x:hoja.x + hoja.ancho] += 1
            self.assertTrue(np.all(marca == 1))

    def test_cota_de_error(self):
        """MSE global <= tolerancia + 0.25 (error de la región + redondeo de la media)."""
        rng = np.random.default_rng(3)
        for img in (imagen_por_bloques(rng, 60, 45, 3), generar_imagen("detalle", 64)):
            for tol in (0, 1, 10, 100, 1000):
                raiz = construir_quadtree(img, tol)
                rec = reconstruir(raiz, *img.shape)
                self.assertLessEqual(mse(img, rec), tol + 0.25 + 1e-9)

    def test_metodos_producen_el_mismo_arbol(self):
        rng = np.random.default_rng(4)
        for (h, w, c) in [(33, 47, 3), (64, 64, 1), (20, 5, 3)]:
            img = imagen_por_bloques(rng, h, w, c)
            for tol in (0, 5, 200):
                a = serializar(construir_quadtree(img, tol, "directo"), h, w, c)
                b = serializar(construir_quadtree(img, tol, "integral"), h, w, c)
                self.assertEqual(a, b)

    def test_hojas_monotonas_en_la_tolerancia(self):
        """Al subir la tolerancia el árbol sólo se poda: nunca hay más hojas."""
        rng = np.random.default_rng(5)
        img = imagen_por_bloques(rng, 64, 64, 3)
        previo = None
        for tol in (0, 1, 5, 20, 100, 500, 5000):
            hojas = estadisticas_arbol(construir_quadtree(img, tol))["hojas"]
            if previo is not None:
                self.assertLessEqual(hojas, previo)
            previo = hojas

    def test_validaciones(self):
        img = generar_imagen("uniforme", 8)
        with self.assertRaises(ValueError):
            construir_quadtree(img, -1)
        with self.assertRaises(ValueError):
            construir_quadtree(img, 0, "otro")
        with self.assertRaises(ValueError):
            construir_quadtree(img.astype(np.float32), 0)
        with self.assertRaises(ValueError):
            construir_quadtree(img[:, :, :2], 0)


class PruebasAlmacenamiento(unittest.TestCase):
    def test_ida_y_vuelta(self):
        rng = np.random.default_rng(6)
        for (h, w, c) in [(1, 1, 3), (17, 9, 1), (64, 64, 3), (45, 100, 3)]:
            img = imagen_por_bloques(rng, h, w, c)
            for tol in (0, 50):
                raiz = construir_quadtree(img, tol)
                datos = serializar(raiz, h, w, c)
                raiz2, h2, w2, c2 = deserializar(datos)
                self.assertEqual((h, w, c), (h2, w2, c2))
                self.assertEqual(estadisticas_arbol(raiz), estadisticas_arbol(raiz2))
                self.assertTrue(np.array_equal(reconstruir(raiz, h, w, c),
                                               reconstruir(raiz2, h2, w2, c2)))

    def test_tamano_imagen_uniforme(self):
        img = generar_imagen("uniforme", 64)
        datos = serializar(construir_quadtree(img, 0), 64, 64, 3)
        # cabecera 5 bytes + 1 bandera + 24 bits de color = 5 bytes + 25 bits -> 5 + 4 = 9 bytes
        self.assertEqual(len(datos), 9)

    def test_el_metodo_puede_expandir(self):
        """En ruido sin tolerancia el Quadtree ocupa MÁS que la imagen original."""
        img = generar_imagen("ruido", 64)
        fila, *_ = comprimir_y_evaluar(img, 0)
        self.assertLess(fila["razon_compresion"], 1.0)
        self.assertFalse(fila["comprime"])
        self.assertEqual(fila["mse"], 0.0)

    def test_comprime_regiones_planas(self):
        img = generar_imagen("regiones", 128)
        fila, *_ = comprimir_y_evaluar(img, 0)
        self.assertGreater(fila["razon_compresion"], 3.0)
        self.assertEqual(fila["mse"], 0.0)


if __name__ == "__main__":
    unittest.main()
