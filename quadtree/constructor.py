"""Construcción del Quadtree con la estrategia Divide y Vencerás.

Definiciones (ver también el README):

* Región R = rectángulo de n = ancho*alto píxeles, con C canales.
* Para cada canal c: media  m_c = (1/n) * sum(p_c)
                     SSE_c = sum((p_c - m_c)^2) = sum(p_c^2) - (sum p_c)^2 / n
* Criterio de uniformidad (tolerancia ``tol`` >= 0):

        MSE_region = (SSE_1 + ... + SSE_C) / (n * C)  <=  tol

  Es decir, la región es uniforme si la varianza media de sus píxeles respecto
  a su color medio no supera ``tol``. Con tol = 0 se exige uniformidad EXACTA
  (todos los píxeles idénticos) y la compresión es sin pérdida.
  La comparación se hace con aritmética ENTERA (n*sum(p^2) - (sum p)^2), por
  lo que no hay errores de redondeo en el caso tol = 0.

* Color representativo de una hoja: media por canal redondeada (mitad hacia
  arriba) con aritmética entera.

Divide y Vencerás:
  DIVIDIR   : si la región no es uniforme y tiene más de 1 píxel, se parte en
              hasta 4 subregiones (``dividir_region``).
  RESOLVER  : se procesa cada subregión recursivamente. Caso base: región
              uniforme o de 1 píxel -> nodo hoja.
  COMBINAR  : los nodos resultantes se enlazan bajo un nodo padre.
"""
import numpy as np

from .nodo import NodoQuadtree

METODOS = ("directo", "integral")
MAX_DIMENSION = 65535  # el formato de almacenamiento usa 16 bits por dimensión


# --------------------------------------------------------------------------
# DIVIDIR: partición espacial
# --------------------------------------------------------------------------
def dividir_region(x, y, ancho, alto):
    """Divide una región en sus subregiones NO vacías.

    Estrategia para dimensiones arbitrarias (no potencias de 2):
        mitad izquierda/superior = ceil(dim / 2)
        mitad derecha/inferior   = dim - ceil(dim / 2)   (puede ser 0)

    * Las subregiones son disjuntas y su unión es exactamente la región
      (cubre todos los píxeles, sin omisiones ni superposiciones).
    * Si una dimensión vale 1 no se parte en esa dirección, por lo que nunca
      se generan regiones vacías (la región degenera en 2 hijos, o en 1 sólo
      si fuera de 1x1, caso que se rechaza).
    * Todo hijo tiene estrictamente menos píxeles que su padre, por lo que
      la recursión siempre avanza hacia el caso base.

    Devuelve una lista de tuplas (x, y, ancho, alto) en el orden
    NO (noroeste), NE, SO, SE.
    """
    if ancho <= 0 or alto <= 0:
        raise ValueError("región vacía")
    if ancho * alto == 1:
        raise ValueError("una región de 1x1 no se puede dividir")
    w1 = (ancho + 1) // 2
    h1 = (alto + 1) // 2
    columnas = [(x, w1)]
    if ancho - w1 > 0:
        columnas.append((x + w1, ancho - w1))
    filas = [(y, h1)]
    if alto - h1 > 0:
        filas.append((y + h1, alto - h1))
    return [(cx, fy, cw, fh) for (fy, fh) in filas for (cx, cw) in columnas]


# --------------------------------------------------------------------------
# Estadísticas de una región (suma y suma de cuadrados por canal)
# --------------------------------------------------------------------------
class EstadisticasDirectas:
    """Calcula las sumas recorriendo los píxeles de la región: Theta(n*C)."""

    def __init__(self, imagen):
        self.imagen = imagen

    def sumas(self, x, y, ancho, alto):
        r = self.imagen[y:y + alto, x:x + ancho].astype(np.int64)
        return r.sum(axis=(0, 1)).tolist(), (r * r).sum(axis=(0, 1)).tolist()


class EstadisticasIntegrales:
    """Imágenes integrales (tablas de áreas sumadas) de p y p^2.

    Preprocesamiento Theta(n*C); después cada consulta cuesta O(C).
    Memoria extra: 2 tablas int64 de (alto+1)*(ancho+1)*C elementos.
    """

    def __init__(self, imagen):
        a = imagen.astype(np.int64)
        alto, ancho, canales = a.shape
        self.s1 = np.zeros((alto + 1, ancho + 1, canales), dtype=np.int64)
        self.s2 = np.zeros((alto + 1, ancho + 1, canales), dtype=np.int64)
        self.s1[1:, 1:] = a.cumsum(axis=0).cumsum(axis=1)
        self.s2[1:, 1:] = (a * a).cumsum(axis=0).cumsum(axis=1)

    def sumas(self, x, y, ancho, alto):
        x2, y2 = x + ancho, y + alto
        s1, s2 = self.s1, self.s2
        r1 = s1[y2, x2] - s1[y, x2] - s1[y2, x] + s1[y, x]
        r2 = s2[y2, x2] - s2[y, x2] - s2[y2, x] + s2[y, x]
        return r1.tolist(), r2.tolist()


def es_uniforme(suma, suma_cuad, n, tolerancia):
    """Criterio de uniformidad: MSE de la región respecto a su media <= tol.

    sum_c [n*sum(p^2) - (sum p)^2]  <=  tol * n^2 * C        (todo entero salvo tol)
    """
    canales = len(suma)
    numerador = 0
    for c in range(canales):
        numerador += n * suma_cuad[c] - suma[c] * suma[c]
    return numerador <= tolerancia * n * n * canales


def color_representativo(suma, n):
    """Media por canal redondeada (mitad hacia arriba), en aritmética entera."""
    return tuple((2 * s + n) // (2 * n) for s in suma)


# --------------------------------------------------------------------------
# RESOLVER + COMBINAR: construcción recursiva
# --------------------------------------------------------------------------
def _construir(est, x, y, ancho, alto, tolerancia):
    n = ancho * alto
    suma, suma_cuad = est.sumas(x, y, ancho, alto)

    # Caso base: región de 1 píxel o región uniforme -> hoja
    if n == 1 or es_uniforme(suma, suma_cuad, n, tolerancia):
        return NodoQuadtree(x, y, ancho, alto, color=color_representativo(suma, n))

    # Dividir + resolver recursivamente cada subregión + combinar bajo un padre
    hijos = [_construir(est, sx, sy, sw, sh, tolerancia)
             for (sx, sy, sw, sh) in dividir_region(x, y, ancho, alto)]
    return NodoQuadtree(x, y, ancho, alto, hijos=hijos)


def validar_imagen(imagen):
    if not isinstance(imagen, np.ndarray) or imagen.ndim != 3:
        raise ValueError("la imagen debe ser un ndarray de forma (alto, ancho, canales)")
    if imagen.dtype != np.uint8:
        raise ValueError("la imagen debe ser de tipo uint8")
    alto, ancho, canales = imagen.shape
    if canales not in (1, 3):
        raise ValueError("solo se admiten 1 canal (grises) o 3 canales (RGB)")
    if not (1 <= alto <= MAX_DIMENSION and 1 <= ancho <= MAX_DIMENSION):
        raise ValueError(f"las dimensiones deben estar entre 1 y {MAX_DIMENSION}")


def construir_quadtree(imagen, tolerancia=0.0, metodo="directo"):
    """Construye el Quadtree de ``imagen`` y devuelve su nodo raíz.

    metodo: "directo"  -> cada región se evalúa recorriendo sus píxeles
            "integral" -> las regiones se evalúan en O(1) con imágenes integrales
    Ambos métodos producen exactamente el mismo árbol.
    """
    validar_imagen(imagen)
    if tolerancia < 0:
        raise ValueError("la tolerancia debe ser >= 0")
    if metodo not in METODOS:
        raise ValueError(f"metodo debe ser uno de {METODOS}")
    alto, ancho, _ = imagen.shape
    est = EstadisticasDirectas(imagen) if metodo == "directo" else EstadisticasIntegrales(imagen)
    return _construir(est, 0, 0, ancho, alto, tolerancia)
