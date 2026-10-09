"""Métricas de calidad, compresión y estadísticas estructurales del árbol."""
import math

import numpy as np


def mse(original, reconstruida):
    """Error cuadrático medio sobre todos los valores (píxeles x canales)."""
    d = original.astype(np.float64) - reconstruida.astype(np.float64)
    return float(np.mean(d * d))


def psnr(mse_valor, valor_maximo=255.0):
    """Relación señal-ruido pico en dB (infinito si la reconstrucción es exacta)."""
    if mse_valor == 0:
        return math.inf
    return 10.0 * math.log10(valor_maximo ** 2 / mse_valor)


def razon_compresion(bytes_originales, bytes_comprimidos):
    """bytes_originales / bytes_comprimidos. Un valor < 1 significa que el método EXPANDE."""
    return bytes_originales / bytes_comprimidos


def estadisticas_arbol(raiz):
    """Recorrido iterativo del árbol.

    nodos            : total de nodos
    hojas            : nodos sin hijos
    nodos_internos   : nodos con hijos
    profundidad_max  : profundidad de la hoja más profunda (raíz = 0)
    pixeles_evaluados: suma de las áreas de todos los nodos. Es el número de
                       lecturas de píxel que hace el método "directo" (cada
                       nodo se evalúa una sola vez), una medida del costo
                       independiente del hardware.
    """
    nodos = hojas = prof_max = pix_eval = 0
    pila = [(raiz, 0)]
    while pila:
        nodo, prof = pila.pop()
        nodos += 1
        pix_eval += nodo.ancho * nodo.alto
        if nodo.hijos is None:
            hojas += 1
            if prof > prof_max:
                prof_max = prof
        else:
            pila.extend((h, prof + 1) for h in nodo.hijos)
    return {"nodos": nodos, "hojas": hojas, "nodos_internos": nodos - hojas,
            "profundidad_max": prof_max, "pixeles_evaluados": pix_eval}
