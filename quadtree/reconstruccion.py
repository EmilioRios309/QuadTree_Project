"""Reconstrucción de la imagen a partir del Quadtree."""
import numpy as np


def reconstruir(raiz, alto, ancho, canales):
    """Recorre el árbol y pinta cada hoja con su color representativo.

    Costo: Theta(nodos) para el recorrido + Theta(alto*ancho*canales) para
    escribir los píxeles (cada píxel pertenece a exactamente una hoja).
    El recorrido es iterativo (pila explícita).
    """
    imagen = np.zeros((alto, ancho, canales), dtype=np.uint8)
    pila = [raiz]
    while pila:
        nodo = pila.pop()
        if nodo.hijos is None:
            imagen[nodo.y:nodo.y + nodo.alto, nodo.x:nodo.x + nodo.ancho] = \
                np.array(nodo.color, dtype=np.uint8)
        else:
            pila.extend(nodo.hijos)
    return imagen


def dibujar_divisiones(imagen, raiz, color_linea=(230, 30, 30)):
    """Devuelve una copia RGB de ``imagen`` con los bordes de las hojas dibujados.

    Para cada hoja se marcan su fila superior y su columna izquierda, lo que
    cubre todas las fronteras internas entre regiones.
    """
    if imagen.shape[2] == 1:
        salida = np.repeat(imagen, 3, axis=2).copy()
    else:
        salida = imagen.copy()
    linea = np.array(color_linea, dtype=np.uint8)
    pila = [raiz]
    while pila:
        nodo = pila.pop()
        if nodo.hijos is None:
            salida[nodo.y, nodo.x:nodo.x + nodo.ancho] = linea
            salida[nodo.y:nodo.y + nodo.alto, nodo.x] = linea
        else:
            pila.extend(nodo.hijos)
    return salida
