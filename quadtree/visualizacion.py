"""Figuras comparativas: original | reconstruida | divisiones del Quadtree."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from .reconstruccion import dibujar_divisiones  # noqa: E402


def _mostrar(ax, imagen, titulo):
    if imagen.shape[2] == 1:
        ax.imshow(imagen[:, :, 0], cmap="gray", vmin=0, vmax=255, interpolation="nearest")
    else:
        ax.imshow(imagen, interpolation="nearest")
    ax.set_title(titulo, fontsize=11)
    ax.set_xticks([])
    ax.set_yticks([])


def figura_comparativa(original, reconstruida, raiz, titulo, resumen, ruta):
    """Guarda una figura con las tres vistas y un resumen de configuración y métricas."""
    fig, ejes = plt.subplots(1, 3, figsize=(13, 5.6))
    _mostrar(ejes[0], original, "Original")
    _mostrar(ejes[1], reconstruida, "Reconstruida")
    _mostrar(ejes[2], dibujar_divisiones(reconstruida, raiz), "Divisiones del Quadtree")
    fig.suptitle(titulo, fontsize=13, fontweight="bold")
    fig.text(0.5, 0.03, resumen, ha="center", va="bottom", fontsize=10, family="monospace")
    fig.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.17, wspace=0.05)
    fig.savefig(ruta, dpi=130)
    plt.close(fig)
