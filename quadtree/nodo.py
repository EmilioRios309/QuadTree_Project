"""Nodo del Quadtree.

Cada nodo representa una región rectangular de la imagen:

    columnas [x, x + ancho)   y   filas [y, y + alto)

* Un nodo HOJA guarda el color representativo (media redondeada por canal)
  de toda su región y no tiene hijos.
* Un nodo INTERNO guarda referencias a sus subregiones (entre 2 y 4 hijos,
  ver ``constructor.dividir_region``) y no guarda color.

Con la posición, el tamaño y los hijos es posible recuperar la distribución
espacial completa y reconstruir la imagen.
"""


class NodoQuadtree:
    __slots__ = ("x", "y", "ancho", "alto", "color", "hijos")

    def __init__(self, x, y, ancho, alto, color=None, hijos=None):
        self.x = x
        self.y = y
        self.ancho = ancho
        self.alto = alto
        self.color = color      # tupla de enteros (uno por canal) si es hoja
        self.hijos = hijos      # lista de NodoQuadtree si es interno, None si es hoja

    @property
    def es_hoja(self):
        return self.hijos is None

    @property
    def area(self):
        return self.ancho * self.alto

    def __repr__(self):
        tipo = "hoja" if self.es_hoja else f"interno({len(self.hijos)} hijos)"
        return (f"NodoQuadtree(x={self.x}, y={self.y}, ancho={self.ancho}, "
                f"alto={self.alto}, {tipo})")


def recorrer_hojas(raiz):
    """Genera todas las hojas del árbol (recorrido iterativo, orden NO, NE, SO, SE)."""
    pila = [raiz]
    while pila:
        nodo = pila.pop()
        if nodo.hijos is None:
            yield nodo
        else:
            # se invierte para visitar los hijos en su orden natural
            pila.extend(reversed(nodo.hijos))
