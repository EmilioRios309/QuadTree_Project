"""Lectura y escritura de imágenes como matrices de píxeles.

Representación interna: ``numpy.ndarray`` de forma (alto, ancho, canales) y
tipo ``uint8``. Se usan 3 canales (RGB) o 1 canal (escala de grises). Las
imágenes en escala de grises también se guardan con eje de canales (C = 1)
para que todo el algoritmo trate ambos casos de la misma forma.

Pillow se usa únicamente para leer/escribir archivos; no interviene en la
construcción ni en la compresión.
"""
import numpy as np
from PIL import Image


def cargar_imagen(ruta, modo="rgb"):
    """Carga una imagen desde disco.

    modo: "rgb"   -> matriz (alto, ancho, 3)
          "gris"  -> matriz (alto, ancho, 1)
    Si el archivo tiene canal alfa, se descarta (se convierte a RGB).
    """
    modo = modo.lower()
    if modo not in ("rgb", "gris"):
        raise ValueError("modo debe ser 'rgb' o 'gris'")
    with Image.open(ruta) as im:
        im = im.convert("RGB" if modo == "rgb" else "L")
        matriz = np.asarray(im, dtype=np.uint8)
    if matriz.ndim == 2:
        matriz = matriz[:, :, None]
    return matriz.copy()


def guardar_imagen(matriz, ruta):
    """Guarda una matriz (alto, ancho, 1|3) uint8 como archivo de imagen."""
    if matriz.ndim == 3 and matriz.shape[2] == 1:
        matriz = matriz[:, :, 0]
    Image.fromarray(matriz).save(ruta)


def describir_imagen(matriz):
    """Dimensiones y cantidad total de píxeles."""
    alto, ancho, canales = matriz.shape
    return {"alto": alto, "ancho": ancho, "canales": canales,
            "pixeles": alto * ancho, "valores": alto * ancho * canales}
