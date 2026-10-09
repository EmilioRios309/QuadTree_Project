#!/usr/bin/env python3
"""Genera el conjunto de imágenes de prueba en ``imagenes_prueba/``.

4 tipos (uniforme, regiones, detalle, ruido) x 3 tamaños (64, 128, 256), más
dos imágenes con dimensiones que NO son potencias de dos (203x151 y 100x75).
Son las mismas imágenes (misma semilla) que usa ``experimentos.py``.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quadtree import TIPOS, generar_imagen, guardar_imagen  # noqa: E402

SEMILLA = 42


def main(carpeta="imagenes_prueba"):
    os.makedirs(carpeta, exist_ok=True)
    for tipo in TIPOS:
        for n in (64, 128, 256):
            guardar_imagen(generar_imagen(tipo, n, semilla=SEMILLA), os.path.join(carpeta, f"{tipo}_{n}.png"))
    guardar_imagen(generar_imagen("regiones", 203, 151, semilla=SEMILLA), os.path.join(carpeta, "regiones_203x151.png"))
    guardar_imagen(generar_imagen("detalle", 100, 75, semilla=SEMILLA), os.path.join(carpeta, "detalle_100x75.png"))
    print(f"{len(os.listdir(carpeta))} imágenes generadas en {os.path.abspath(carpeta)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "imagenes_prueba")
