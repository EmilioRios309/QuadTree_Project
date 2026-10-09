"""Compresión + reconstrucción + métricas en una sola llamada.

Separa los costos que pide el enunciado:
  t_construccion_s   : construir el árbol (Divide y Vencerás)
  t_serializacion_s  : recorrer el árbol y codificarlo en bytes
  t_reconstruccion_s : recorrer el árbol y regenerar la imagen
"""
import statistics
import time

import numpy as np

from .almacenamiento import deserializar, serializar
from .constructor import construir_quadtree
from .metricas import estadisticas_arbol, mse, psnr, razon_compresion
from .reconstruccion import reconstruir


def _medir(funcion, repeticiones):
    """Ejecuta ``funcion`` varias veces; devuelve (mediana de tiempos, último resultado)."""
    tiempos, resultado = [], None
    for _ in range(max(1, repeticiones)):
        t0 = time.perf_counter()
        resultado = funcion()
        tiempos.append(time.perf_counter() - t0)
    return statistics.median(tiempos), resultado


def comprimir_y_evaluar(imagen, tolerancia, metodo="directo", repeticiones=1, verificar=True):
    """Devuelve (fila_de_metricas, raiz, imagen_reconstruida, bytes_comprimidos).

    Si ``verificar`` es True se decodifican los bytes y se comprueba que la
    imagen reconstruida desde el archivo coincide exactamente con la
    reconstruida desde el árbol en memoria.
    """
    alto, ancho, canales = imagen.shape

    t_cons, raiz = _medir(lambda: construir_quadtree(imagen, tolerancia, metodo), repeticiones)
    t_ser, datos = _medir(lambda: serializar(raiz, alto, ancho, canales), repeticiones)
    t_rec, recon = _medir(lambda: reconstruir(raiz, alto, ancho, canales), repeticiones)

    if verificar:
        raiz2, a2, w2, c2 = deserializar(datos)
        recon2 = reconstruir(raiz2, a2, w2, c2)
        if (a2, w2, c2) != (alto, ancho, canales) or not np.array_equal(recon, recon2):
            raise AssertionError("la imagen decodificada no coincide con la reconstruida del árbol")

    est = estadisticas_arbol(raiz)
    bytes_orig = alto * ancho * canales
    bytes_comp = len(datos)
    error = mse(imagen, recon)

    fila = {
        "ancho": ancho, "alto": alto, "canales": canales, "pixeles": alto * ancho,
        "metodo": metodo, "tolerancia": tolerancia,
        "t_construccion_s": t_cons, "t_serializacion_s": t_ser, "t_reconstruccion_s": t_rec,
        **est,
        "bytes_originales": bytes_orig, "bytes_comprimidos": bytes_comp,
        "razon_compresion": razon_compresion(bytes_orig, bytes_comp),
        "ahorro_pct": (1.0 - bytes_comp / bytes_orig) * 100.0,
        "bits_por_pixel": bytes_comp * 8.0 / (alto * ancho),
        "mse": error, "psnr_db": psnr(error),
        "comprime": bytes_comp < bytes_orig,
    }
    return fila, raiz, recon, datos
