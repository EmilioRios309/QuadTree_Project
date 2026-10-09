#!/usr/bin/env python3
"""Interfaz de consola para comprimir y descomprimir imágenes con el Quadtree.

    python comprimir.py comprimir imagenes_prueba/regiones_256.png --tolerancia 0
    python comprimir.py comprimir foto.jpg --tolerancia 100 --modo gris --salida salida/
    python comprimir.py descomprimir salida/foto.qt reconstruida.png

``comprimir`` escribe en la carpeta de salida:
    <nombre>.qt            representación comprimida (formato descrito en almacenamiento.py)
    <nombre>_reconstruida.png
    <nombre>_comparacion.png   original | reconstruida | divisiones del árbol
y imprime las métricas.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quadtree import (cargar_imagen, comprimir_y_evaluar, deserializar,  # noqa: E402
                      guardar_imagen, reconstruir)
from quadtree.visualizacion import figura_comparativa  # noqa: E402


def resumen_texto(fila):
    psnr = "inf" if fila["psnr_db"] == float("inf") else f"{fila['psnr_db']:.2f} dB"
    return (f"{fila['ancho']}x{fila['alto']}x{fila['canales']} | tol={fila['tolerancia']:g} | método={fila['metodo']}\n"
            f"nodos={fila['nodos']}  hojas={fila['hojas']}  profundidad={fila['profundidad_max']}  "
            f"bytes={fila['bytes_comprimidos']} (orig {fila['bytes_originales']})  "
            f"razón={fila['razon_compresion']:.2f}\n"
            f"MSE={fila['mse']:.3f}  PSNR={psnr}  t_construcción={fila['t_construccion_s']*1000:.1f} ms")


def comprimir(args):
    imagen = cargar_imagen(args.imagen, args.modo)
    fila, raiz, recon, datos = comprimir_y_evaluar(imagen, args.tolerancia, args.metodo, args.repeticiones)
    os.makedirs(args.salida, exist_ok=True)
    base = os.path.join(args.salida, os.path.splitext(os.path.basename(args.imagen))[0])
    with open(base + ".qt", "wb") as f:
        f.write(datos)
    guardar_imagen(recon, base + "_reconstruida.png")
    texto = resumen_texto(fila)
    figura_comparativa(imagen, recon, raiz, os.path.basename(args.imagen), texto, base + "_comparacion.png")
    print(texto)
    if not fila["comprime"]:
        print("AVISO: con esta imagen y tolerancia el Quadtree ocupa MÁS que la imagen original.")
    print(f"\nArchivos escritos con prefijo: {base}")


def descomprimir(args):
    with open(args.archivo, "rb") as f:
        raiz, alto, ancho, canales = deserializar(f.read())
    guardar_imagen(reconstruir(raiz, alto, ancho, canales), args.destino)
    print(f"Imagen {ancho}x{alto} ({canales} canal(es)) escrita en {args.destino}")


def main():
    ap = argparse.ArgumentParser(description="Compresor de imágenes basado en Quadtree")
    sub = ap.add_subparsers(dest="orden", required=True)

    c = sub.add_parser("comprimir", help="comprime una imagen y evalúa el resultado")
    c.add_argument("imagen")
    c.add_argument("--tolerancia", type=float, default=0.0, help="MSE máximo por región (0 = sin pérdida)")
    c.add_argument("--modo", choices=("rgb", "gris"), default="rgb")
    c.add_argument("--metodo", choices=("directo", "integral"), default="directo")
    c.add_argument("--repeticiones", type=int, default=1)
    c.add_argument("--salida", default="salida")
    c.set_defaults(funcion=comprimir)

    d = sub.add_parser("descomprimir", help="reconstruye una imagen desde un archivo .qt")
    d.add_argument("archivo")
    d.add_argument("destino")
    d.set_defaults(funcion=descomprimir)

    args = ap.parse_args()
    args.funcion(args)


if __name__ == "__main__":
    main()
