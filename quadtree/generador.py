"""Generación reproducible de imágenes sintéticas de prueba.

Tipos:
  uniforme : un solo color.
  regiones : fondo + rectángulos y círculo de colores planos definidos.
  detalle  : gradientes + textura sinusoidal + ruido gaussiano (muchas variaciones).
  ruido    : ruido uniforme independiente por píxel (peor caso: sin redundancia).

Todas devuelven arreglos uint8 (alto, ancho, 3). Con la misma semilla el
resultado es idéntico en cualquier ejecución.
"""
import numpy as np

TIPOS = ("uniforme", "regiones", "detalle", "ruido")


def _uniforme(alto, ancho, rng):
    return np.full((alto, ancho, 3), (70, 130, 180), dtype=np.uint8)


def _regiones(alto, ancho, rng):
    img = np.empty((alto, ancho, 3), dtype=np.uint8)
    img[:] = (245, 240, 225)                                   # fondo
    ys, xs = np.mgrid[0:alto, 0:ancho]
    fx, fy = xs / ancho, ys / alto

    img[(fx >= 0.10) & (fx < 0.45) & (fy >= 0.15) & (fy < 0.50)] = (200, 50, 50)    # rectángulo rojo
    img[(fx >= 0.55) & (fx < 0.90) & (fy >= 0.10) & (fy < 0.35)] = (40, 80, 200)    # rectángulo azul
    img[(fx >= 0.60) & (fx < 0.95) & (fy >= 0.60) & (fy < 0.90)] = (240, 200, 40)   # rectángulo amarillo
    radio = 0.20 * min(alto, ancho)
    cx, cy = 0.35 * ancho, 0.72 * alto
    img[(xs - cx) ** 2 + (ys - cy) ** 2 <= radio ** 2] = (50, 160, 90)              # círculo verde
    return img


def _detalle(alto, ancho, rng):
    ys, xs = np.mgrid[0:alto, 0:ancho].astype(np.float64)
    r = 255.0 * xs / max(ancho - 1, 1)
    g = 255.0 * ys / max(alto - 1, 1)
    b = 255.0 * (xs + ys) / max(ancho + alto - 2, 1)
    base = np.stack([r, g, b], axis=2)
    textura = 18.0 * np.sin(xs / 3.0)[:, :, None] * np.cos(ys / 5.0)[:, :, None]
    ruido = rng.normal(0.0, 8.0, size=(alto, ancho, 3))
    return np.clip(base + textura + ruido, 0, 255).astype(np.uint8)


def _ruido(alto, ancho, rng):
    return rng.integers(0, 256, size=(alto, ancho, 3), dtype=np.uint8)


_GENERADORES = {"uniforme": _uniforme, "regiones": _regiones,
                "detalle": _detalle, "ruido": _ruido}


def generar_imagen(tipo, ancho, alto=None, semilla=42):
    """Genera una imagen sintética RGB. Si no se da ``alto``, es cuadrada."""
    if tipo not in _GENERADORES:
        raise ValueError(f"tipo debe ser uno de {TIPOS}")
    alto = ancho if alto is None else alto
    rng = np.random.default_rng(semilla)
    return _GENERADORES[tipo](alto, ancho, rng)
