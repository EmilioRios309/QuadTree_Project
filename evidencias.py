#!/usr/bin/env python3
"""Genera las evidencias de funcionamiento (Entregable 4) en ``evidencias/``.

Para cada ejemplo guarda: imagen original, imagen reconstruida, archivo .qt,
figura comparativa (original | reconstruida | divisiones), y metricas.json con
la configuración y las métricas obtenidas.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quadtree import comprimir_y_evaluar, generar_imagen, guardar_imagen  # noqa: E402
from quadtree.visualizacion import figura_comparativa  # noqa: E402

SEMILLA = 42

# (nombre, tipo, ancho, alto, tolerancia, comentario)
EJEMPLOS = [
    ("ej1_regiones_tol0", "regiones", 256, 256, 0,
     "Regiones planas, uniformidad exacta: sin pérdida y alta compresión."),
    ("ej2_detalle_tol100", "detalle", 256, 256, 100,
     "Imagen con variaciones: tolerancia moderada, pérdida visible leve."),
    ("ej3_detalle_tol300", "detalle", 256, 256, 300,
     "Misma imagen con tolerancia alta: mayor compresión, bloques evidentes."),
    ("ej4_ruido_tol0", "ruido", 256, 256, 0,
     "Peor caso: ruido sin redundancia. El Quadtree EXPANDE el tamaño."),
    ("ej5_regiones_203x151_tol25", "regiones", 203, 151, 25,
     "Dimensiones que no son potencias de dos."),
]


def main(carpeta="evidencias"):
    indice = ["# Evidencias de funcionamiento\n",
              "| Ejemplo | Imagen | Tol. | Hojas | Bytes (orig → comp.) | Razón | MSE | PSNR (dB) |",
              "|---|---|---|---|---|---|---|---|"]
    for nombre, tipo, ancho, alto, tol, comentario in EJEMPLOS:
        img = generar_imagen(tipo, ancho, alto, semilla=SEMILLA)
        fila, raiz, recon, datos = comprimir_y_evaluar(img, tol, "directo", repeticiones=3)
        destino = os.path.join(carpeta, nombre)
        os.makedirs(destino, exist_ok=True)
        guardar_imagen(img, os.path.join(destino, "original.png"))
        guardar_imagen(recon, os.path.join(destino, "reconstruida.png"))
        with open(os.path.join(destino, "arbol.qt"), "wb") as f:
            f.write(datos)
        psnr = "inf" if fila["psnr_db"] == float("inf") else f"{fila['psnr_db']:.2f}"
        resumen = (f"{ancho}x{alto}x3 | tol={tol} | método=directo | semilla={SEMILLA}\n"
                   f"nodos={fila['nodos']}  hojas={fila['hojas']}  profundidad={fila['profundidad_max']}  "
                   f"bytes={fila['bytes_comprimidos']} (orig {fila['bytes_originales']})  "
                   f"razón={fila['razon_compresion']:.2f}\n"
                   f"MSE={fila['mse']:.3f}  PSNR={psnr} dB  t_construcción={fila['t_construccion_s']*1000:.1f} ms")
        figura_comparativa(img, recon, raiz, f"{nombre}: {comentario}", resumen,
                           os.path.join(destino, "comparacion.png"))
        metricas = {k: ("inf" if v == float("inf") else v) for k, v in fila.items()}
        with open(os.path.join(destino, "metricas.json"), "w", encoding="utf-8") as f:
            json.dump({"configuracion": {"tipo": tipo, "ancho": ancho, "alto": alto, "tolerancia": tol,
                                         "metodo": "directo", "semilla": SEMILLA},
                       "comentario": comentario, "metricas": metricas}, f, indent=2, ensure_ascii=False)
        indice.append(f"| [{nombre}]({nombre}/comparacion.png) | {ancho}x{alto} {tipo} | {tol} | {fila['hojas']} | "
                      f"{fila['bytes_originales']} → {fila['bytes_comprimidos']} | {fila['razon_compresion']:.2f} | "
                      f"{fila['mse']:.3f} | {psnr} |")
        print(f"{nombre}: razón={fila['razon_compresion']:.2f} mse={fila['mse']:.3f}")
    with open(os.path.join(carpeta, "indice.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(indice) + "\n")
    print(f"Evidencias en {os.path.abspath(carpeta)}")


if __name__ == "__main__":
    main()
