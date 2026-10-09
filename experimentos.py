#!/usr/bin/env python3
"""Experimentos reproducibles del proyecto.

Genera (en la carpeta de salida, por defecto ``resultados/``):

  resultados.csv          matriz principal: 4 tipos x 3 tamaños x 3 tolerancias x 2 métodos
  barrido_tolerancia.csv  imágenes de 256x256 con 11 tolerancias (compresión vs calidad)
  escalado.csv            tamaños 32..512 con tolerancia 0 (crecimiento del costo)
  tablas.md               tablas listas para copiar al reporte
  graficas/*.png          gráficas del análisis

Uso:
    python experimentos.py                  # experimento completo (varios minutos)
    python experimentos.py --rapido         # 1 repetición y sin tamaño 512
    python experimentos.py --solo-graficas  # regenera tablas y gráficas desde los CSV

Las imágenes se generan con semilla fija (quadtree/generador.py), por lo que
los resultados estructurales (nodos, bytes, MSE...) son idénticos en cada
ejecución; sólo los tiempos varían con la máquina.
"""
import argparse
import csv
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from quadtree import TIPOS, comprimir_y_evaluar, generar_imagen  # noqa: E402

TAMANOS = (64, 128, 256)
TOLERANCIAS = (0, 50, 500)           # 0 = uniformidad exacta (sin pérdida)
METODOS = ("directo", "integral")
BARRIDO = (0, 1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500)
ESCALADO = (32, 64, 128, 256, 512)
SEMILLA = 42

# --- estilo de las gráficas (paleta categórica validada, superficie clara) ---
SUPERFICIE, TINTA, TINTA_2, REJILLA, EJE = "#fcfcfb", "#0b0b0b", "#52514e", "#e1e0d9", "#c3c2b7"
COLOR_TIPO = {"uniforme": "#2a78d6", "regiones": "#eb6834", "detalle": "#1baf7a", "ruido": "#eda100"}
MARCA_TIPO = {"uniforme": "o", "regiones": "s", "detalle": "^", "ruido": "D"}
COLOR_METODO = {"directo": "#2a78d6", "integral": "#eb6834"}


def _fila(imagen, tipo, fila):
    return {"imagen": imagen, "tipo": tipo, **fila}


def _guardar_csv(ruta, filas):
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)


def _leer_csv(ruta):
    def conv(v):
        if v in ("True", "False"):
            return v == "True"
        try:
            return int(v)
        except ValueError:
            pass
        try:
            return float(v)
        except ValueError:
            return v
    with open(ruta, newline="", encoding="utf-8") as f:
        return [{k: conv(v) for k, v in r.items()} for r in csv.DictReader(f)]


# --------------------------------------------------------------------------
# Experimentos
# --------------------------------------------------------------------------
def experimento_principal(repeticiones):
    filas = []
    total = len(TIPOS) * len(TAMANOS) * len(TOLERANCIAS) * len(METODOS)
    k = 0
    for tipo in TIPOS:
        for n in TAMANOS:
            img = generar_imagen(tipo, n, semilla=SEMILLA)
            for tol in TOLERANCIAS:
                for metodo in METODOS:
                    k += 1
                    fila, *_ = comprimir_y_evaluar(img, tol, metodo, repeticiones)
                    filas.append(_fila(f"{tipo}_{n}x{n}", tipo, fila))
                    print(f"[principal {k:3d}/{total}] {tipo:9s} {n:3d} tol={tol:<5} {metodo:8s} "
                          f"nodos={fila['nodos']:6d} razon={fila['razon_compresion']:7.2f} "
                          f"mse={fila['mse']:9.3f} t={fila['t_construccion_s']*1000:8.1f} ms", flush=True)
    return filas


def experimento_barrido(repeticiones):
    filas = []
    for tipo in TIPOS:
        img = generar_imagen(tipo, 256, semilla=SEMILLA)
        for tol in BARRIDO:
            fila, *_ = comprimir_y_evaluar(img, tol, "directo", repeticiones)
            filas.append(_fila(f"{tipo}_256x256", tipo, fila))
            print(f"[barrido] {tipo:9s} tol={tol:<5} nodos={fila['nodos']:6d} "
                  f"razon={fila['razon_compresion']:7.2f} mse={fila['mse']:9.3f}", flush=True)
    return filas


def experimento_escalado(repeticiones, tamanos):
    filas = []
    for tipo in TIPOS:
        for n in tamanos:
            img = generar_imagen(tipo, n, semilla=SEMILLA)
            reps = 1 if n >= 512 else repeticiones
            for metodo in METODOS:
                fila, *_ = comprimir_y_evaluar(img, 0, metodo, reps, verificar=(n <= 256))
                filas.append(_fila(f"{tipo}_{n}x{n}", tipo, fila))
                print(f"[escalado] {tipo:9s} {n:3d} {metodo:8s} nodos={fila['nodos']:7d} "
                      f"t={fila['t_construccion_s']*1000:9.1f} ms", flush=True)
    return filas


# --------------------------------------------------------------------------
# Tablas
# --------------------------------------------------------------------------
def escribir_tablas(ruta, principal, barrido):
    def fmt_psnr(v):
        return "inf" if v == math.inf else f"{v:.2f}"

    lineas = ["# Tablas de resultados\n",
              "## Matriz principal (método directo)\n",
              "| Tipo | Tamaño | Tol. | Nodos | Hojas | Prof. | Bytes comp. | Razón | MSE | PSNR (dB) | t constr. (ms) |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in principal:
        if r["metodo"] != "directo":
            continue
        lineas.append(f"| {r['tipo']} | {r['ancho']}x{r['alto']} | {r['tolerancia']:g} | {r['nodos']} | "
                      f"{r['hojas']} | {r['profundidad_max']} | {r['bytes_comprimidos']} | "
                      f"{r['razon_compresion']:.2f} | {r['mse']:.3f} | {fmt_psnr(r['psnr_db'])} | "
                      f"{r['t_construccion_s']*1000:.1f} |")

    lineas += ["", "## Casos en que el Quadtree NO reduce el almacenamiento (razón < 1)\n",
               "| Tipo | Tamaño | Tol. | Bytes originales | Bytes comp. | Razón |", "|---|---|---|---|---|---|"]
    for r in principal + barrido:
        if r["metodo"] == "directo" and not r["comprime"]:
            lineas.append(f"| {r['tipo']} | {r['ancho']}x{r['alto']} | {r['tolerancia']:g} | "
                          f"{r['bytes_originales']} | {r['bytes_comprimidos']} | {r['razon_compresion']:.2f} |")

    lineas += ["", "## Barrido de tolerancia (256x256, método directo)\n",
               "| Tipo | Tol. | Hojas | Bytes comp. | Razón | MSE | PSNR (dB) |", "|---|---|---|---|---|---|---|"]
    for r in barrido:
        lineas.append(f"| {r['tipo']} | {r['tolerancia']:g} | {r['hojas']} | {r['bytes_comprimidos']} | "
                      f"{r['razon_compresion']:.2f} | {r['mse']:.3f} | {fmt_psnr(r['psnr_db'])} |")

    lineas += ["", "## Directo vs integral (tolerancia 0, tiempo de construcción en ms)\n",
               "| Tipo | Tamaño | Directo | Integral | Aceleración |", "|---|---|---|---|---|"]
    por_clave = {}
    for r in principal:
        if r["tolerancia"] == 0:
            por_clave.setdefault((r["tipo"], r["ancho"]), {})[r["metodo"]] = r["t_construccion_s"] * 1000
    for (tipo, n), d in por_clave.items():
        lineas.append(f"| {tipo} | {n}x{n} | {d['directo']:.1f} | {d['integral']:.1f} | "
                      f"{d['directo'] / d['integral']:.2f}x |")

    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


# --------------------------------------------------------------------------
# Gráficas
# --------------------------------------------------------------------------
def _estilo(ax, titulo, xlabel, ylabel):
    ax.set_facecolor(SUPERFICIE)
    ax.set_title(titulo, fontsize=11, color=TINTA, loc="left", fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=9.5, color=TINTA_2)
    ax.set_ylabel(ylabel, fontsize=9.5, color=TINTA_2)
    ax.grid(True, color=REJILLA, linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(EJE)
    ax.tick_params(colors=TINTA_2, labelsize=9)


def _serie(ax, x, y, tipo, etiqueta=None):
    ax.plot(x, y, color=COLOR_TIPO[tipo], marker=MARCA_TIPO[tipo], markersize=6, linewidth=1.6,
            markeredgecolor=SUPERFICIE, markeredgewidth=1.0, label=etiqueta or tipo)


def _leyenda(ax, **kw):
    leg = ax.legend(frameon=False, fontsize=9, **kw)
    for t in leg.get_texts():
        t.set_color(TINTA_2)


def _figura(n_paneles, ancho=5.2):
    fig, ejes = plt.subplots(1, n_paneles, figsize=(ancho * n_paneles, 4.5))
    fig.patch.set_facecolor(SUPERFICIE)
    return fig, (ejes if n_paneles > 1 else [ejes])


def grafica_escalado(escalado, ruta):
    fig, (a, b, c) = _figura(3, 5.0)
    sel = [r for r in escalado if r["metodo"] == "directo"]

    # (a) tiempo de construcción vs píxeles
    for tipo in TIPOS:
        rs = [r for r in sel if r["tipo"] == tipo]
        _serie(a, [r["pixeles"] for r in rs], [r["t_construccion_s"] for r in rs], tipo)
    rr = [r for r in sel if r["tipo"] == "ruido"]
    n0, t0 = rr[0]["pixeles"], rr[0]["t_construccion_s"]
    xs = [r["pixeles"] for r in rr]
    a.plot(xs, [t0 * x / n0 for x in xs], color=EJE, linestyle="--", linewidth=1.2, label="∝ n")
    a.plot(xs, [t0 * (x * math.log(x)) / (n0 * math.log(n0)) for x in xs], color=TINTA_2,
           linestyle=":", linewidth=1.4, label="∝ n log n")
    a.set_xscale("log", base=2)
    a.set_yscale("log")
    _estilo(a, "Tiempo de construcción (método directo)", "píxeles n (tol = 0)", "segundos")
    _leyenda(a, loc="lower right")

    # (b) directo vs integral en el peor caso (ruido)
    for metodo in METODOS:
        rs = [r for r in escalado if r["tipo"] == "ruido" and r["metodo"] == metodo]
        b.plot([r["pixeles"] for r in rs], [r["t_construccion_s"] for r in rs],
               color=COLOR_METODO[metodo], marker="o" if metodo == "directo" else "s", markersize=6,
               linewidth=1.6, markeredgecolor=SUPERFICIE, markeredgewidth=1.0, label=metodo)
    b.set_xscale("log", base=2)
    b.set_yscale("log")
    _estilo(b, "Directo vs integral (ruido, peor caso)", "píxeles n (tol = 0)", "segundos")
    _leyenda(b, loc="upper left")

    # (c) píxeles evaluados por píxel de imagen: ~ log n en el peor caso, ~1 si es uniforme
    for tipo in TIPOS:
        rs = [r for r in sel if r["tipo"] == tipo]
        _serie(c, [r["pixeles"] for r in rs], [r["pixeles_evaluados"] / r["pixeles"] for r in rs], tipo)
    c.set_xscale("log", base=2)
    _estilo(c, "Lecturas de píxel por píxel de la imagen", "píxeles n (tol = 0)", "Σ áreas de los nodos / n")
    _leyenda(c, loc="upper left")
    fig.tight_layout()
    fig.savefig(ruta, dpi=140, facecolor=SUPERFICIE)
    plt.close(fig)


def _eje_tol(ax):
    ax.set_xscale("symlog", linthresh=1)
    ax.set_xlim(left=-0.2)


def grafica_tolerancia(barrido, ruta):
    fig, (a, b) = _figura(2, 5.6)
    for tipo in TIPOS:
        rs = [r for r in barrido if r["tipo"] == tipo]
        _serie(a, [r["tolerancia"] for r in rs], [r["nodos"] for r in rs], tipo)
        _serie(b, [r["tolerancia"] for r in rs], [r["razon_compresion"] for r in rs], tipo)
    a.set_yscale("log")
    _eje_tol(a)
    _estilo(a, "Número de nodos (256×256)", "tolerancia (MSE máximo por región)", "nodos")
    _leyenda(a, loc="center left")
    b.axhline(1.0, color=TINTA_2, linewidth=1.0, linestyle="--")
    b.annotate("sin ganancia (razón = 1)", xy=(1.0, 1.0), xytext=(1.3, 1.25), fontsize=8.5, color=TINTA_2)
    b.set_yscale("log")
    _eje_tol(b)
    _estilo(b, "Razón de compresión (256×256)", "tolerancia (MSE máximo por región)",
            "bytes originales / bytes comprimidos")
    _leyenda(b, loc="center left")
    fig.tight_layout()
    fig.savefig(ruta, dpi=140, facecolor=SUPERFICIE)
    plt.close(fig)


def grafica_calidad(barrido, ruta):
    fig, (a, b) = _figura(2, 5.6)
    for tipo in TIPOS:
        rs = [r for r in barrido if r["tipo"] == tipo]
        _serie(a, [r["mse"] for r in rs], [r["razon_compresion"] for r in rs], tipo)
        _serie(b, [r["tolerancia"] for r in rs], [r["mse"] for r in rs], tipo)
    a.set_xscale("symlog", linthresh=0.1)
    a.set_xlim(left=-0.02)
    a.set_yscale("log")
    a.axhline(1.0, color=TINTA_2, linewidth=1.0, linestyle="--")
    _estilo(a, "Compresión vs error de reconstrucción", "MSE de reconstrucción (0 = sin pérdida)",
            "razón de compresión")
    _leyenda(a, loc="center left")
    xs = [0.0] + [t for t in BARRIDO if t > 0]
    b.plot(xs, [t + 0.25 for t in xs], color=TINTA_2, linestyle=":", linewidth=1.4, label="cota: tol + 0.25")
    b.set_yscale("symlog", linthresh=0.1)
    b.set_ylim(bottom=-0.02)
    _eje_tol(b)
    _estilo(b, "MSE real vs tolerancia", "tolerancia (MSE máximo por región)", "MSE de reconstrucción")
    _leyenda(b, loc="upper left")
    fig.tight_layout()
    fig.savefig(ruta, dpi=140, facecolor=SUPERFICIE)
    plt.close(fig)


def generar_graficas(principal, barrido, escalado, carpeta):
    os.makedirs(carpeta, exist_ok=True)
    grafica_escalado(escalado, os.path.join(carpeta, "escalado_tiempo.png"))
    grafica_tolerancia(barrido, os.path.join(carpeta, "tolerancia_nodos_razon.png"))
    grafica_calidad(barrido, os.path.join(carpeta, "compresion_vs_calidad.png"))


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Experimentos del compresor Quadtree")
    ap.add_argument("--salida", default="resultados", help="carpeta de salida")
    ap.add_argument("--repeticiones", type=int, default=3, help="repeticiones por medición de tiempo (mediana)")
    ap.add_argument("--rapido", action="store_true", help="1 repetición y sin tamaño 512")
    ap.add_argument("--solo-graficas", action="store_true", help="regenerar tablas y gráficas desde los CSV")
    args = ap.parse_args()

    os.makedirs(args.salida, exist_ok=True)
    rutas = {k: os.path.join(args.salida, f"{k}.csv") for k in ("resultados", "barrido_tolerancia", "escalado")}

    if args.solo_graficas:
        principal, barrido, escalado = (_leer_csv(rutas[k]) for k in ("resultados", "barrido_tolerancia", "escalado"))
    else:
        reps = 1 if args.rapido else args.repeticiones
        tamanos = ESCALADO[:-1] if args.rapido else ESCALADO
        t0 = time.perf_counter()
        principal = experimento_principal(reps)
        barrido = experimento_barrido(reps)
        escalado = experimento_escalado(reps, tamanos)
        _guardar_csv(rutas["resultados"], principal)
        _guardar_csv(rutas["barrido_tolerancia"], barrido)
        _guardar_csv(rutas["escalado"], escalado)
        print(f"\nExperimentos terminados en {time.perf_counter() - t0:.1f} s")

    escribir_tablas(os.path.join(args.salida, "tablas.md"), principal, barrido)
    generar_graficas(principal, barrido, escalado, os.path.join(args.salida, "graficas"))
    print(f"Resultados en: {os.path.abspath(args.salida)}")


if __name__ == "__main__":
    main()
