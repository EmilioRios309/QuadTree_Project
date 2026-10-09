"""Formato binario de almacenamiento del Quadtree (.qt).

Estructura del archivo
----------------------
CABECERA (5 bytes = 40 bits)
    ancho   : 16 bits (big endian)
    alto    : 16 bits (big endian)
    canales :  8 bits (1 = grises, 3 = RGB)

CUERPO (flujo de bits, recorrido en PREORDEN, orden NO, NE, SO, SE)
    para cada nodo cuya región tiene más de 1 píxel:
        1 bit de bandera: 1 = nodo interno, 0 = hoja
    (una región de 1x1 es siempre hoja, por lo que NO lleva bandera)
    para cada hoja:
        8 bits por canal con el color representativo

RELLENO
    se completan con ceros los bits sobrantes del último byte.

No hace falta guardar posiciones ni tamaños de los nodos: se recalculan al
decodificar aplicando la misma función ``dividir_region`` sobre las
dimensiones de la cabecera. El tamaño real es la longitud en bytes de la
cadena producida por ``serializar``.
"""
from .constructor import dividir_region
from .nodo import NodoQuadtree

BITS_CABECERA = 40


class EscritorBits:
    def __init__(self):
        self._bytes = bytearray()
        self._acum = 0
        self._n = 0

    def escribir(self, valor, nbits):
        self._acum = (self._acum << nbits) | valor
        self._n += nbits
        while self._n >= 8:
            self._n -= 8
            self._bytes.append((self._acum >> self._n) & 0xFF)
        self._acum &= (1 << self._n) - 1

    def finalizar(self):
        if self._n:
            self._bytes.append((self._acum << (8 - self._n)) & 0xFF)
            self._acum = 0
            self._n = 0
        return bytes(self._bytes)


class LectorBits:
    def __init__(self, datos, posicion_byte=0):
        self._datos = datos
        self._pos = posicion_byte * 8

    def leer(self, nbits):
        valor = 0
        for _ in range(nbits):
            byte = self._datos[self._pos >> 3]
            valor = (valor << 1) | ((byte >> (7 - (self._pos & 7))) & 1)
            self._pos += 1
        return valor

    def leer_byte(self):
        """Lectura de 8 bits (camino rápido cuando está alineado)."""
        return self.leer(8)


def serializar(raiz, alto, ancho, canales):
    """Codifica el árbol en bytes siguiendo el formato descrito arriba."""
    esc = EscritorBits()
    esc.escribir(ancho, 16)
    esc.escribir(alto, 16)
    esc.escribir(canales, 8)

    pila = [raiz]
    while pila:
        nodo = pila.pop()
        if nodo.ancho * nodo.alto > 1:
            esc.escribir(0 if nodo.hijos is None else 1, 1)
        if nodo.hijos is None:
            for valor in nodo.color:
                esc.escribir(valor, 8)
        else:
            pila.extend(reversed(nodo.hijos))
    return esc.finalizar()


def deserializar(datos):
    """Reconstruye el árbol a partir de los bytes. Devuelve (raiz, alto, ancho, canales)."""
    lector = LectorBits(datos)
    ancho = lector.leer(16)
    alto = lector.leer(16)
    canales = lector.leer(8)

    def leer_nodo(x, y, w, h):
        if w * h > 1 and lector.leer(1) == 1:
            hijos = [leer_nodo(*sub) for sub in dividir_region(x, y, w, h)]
            return NodoQuadtree(x, y, w, h, hijos=hijos)
        color = tuple(lector.leer_byte() for _ in range(canales))
        return NodoQuadtree(x, y, w, h, color=color)

    raiz = leer_nodo(0, 0, ancho, alto)
    return raiz, alto, ancho, canales


def desglose_almacenamiento(raiz, canales):
    """Desglose teórico (en bits) del tamaño de la representación."""
    banderas = 0
    hojas = 0
    pila = [raiz]
    while pila:
        nodo = pila.pop()
        if nodo.ancho * nodo.alto > 1:
            banderas += 1
        if nodo.hijos is None:
            hojas += 1
        else:
            pila.extend(nodo.hijos)
    bits_colores = hojas * 8 * canales
    total = BITS_CABECERA + banderas + bits_colores
    relleno = (-total) % 8
    return {"bits_cabecera": BITS_CABECERA, "bits_banderas": banderas,
            "bits_colores": bits_colores, "bits_relleno": relleno,
            "bytes_totales": (total + relleno) // 8}
