# Compresión de imágenes con Quadtree (Divide y Vencerás)

Prototipo de compresión con pérdida controlada basado en un **Quadtree** construido con la estrategia
**Divide y Vencerás**. Una región se representa con un solo color si es suficientemente uniforme; si no,
se divide en hasta cuatro subregiones que se procesan recursivamente.

No se usa ninguna biblioteca que implemente Quadtrees ni compresión. Pillow sólo lee/escribe archivos de
imagen, NumPy maneja las matrices y Matplotlib dibuja las gráficas.

## Instalación y ejecución rápida

Requiere Python 3.9 o superior.

```bash
pip install -r requirements.txt          # numpy, Pillow, matplotlib

python -m unittest discover -s tests -v  # pruebas de correctitud (≈2 s)
python generar_imagenes.py               # imágenes de prueba -> imagenes_prueba/
python evidencias.py                     # ejemplos con original/reconstruida/métricas -> evidencias/
python experimentos.py                   # experimentos completos -> resultados/ (varios minutos)
python experimentos.py --rapido          # versión corta: 1 repetición, sin tamaño 512 (~1 min)
python experimentos.py --solo-graficas   # regenera tablas y gráficas desde los CSV
```

Para comprimir una imagen propia:

```bash
python comprimir.py comprimir foto.png --tolerancia 100 --modo rgb --salida salida/
python comprimir.py descomprimir salida/foto.qt reconstruida.png
```

Opciones de `comprimir`: `--tolerancia` (MSE máximo por región; `0` = sin pérdida), `--modo rgb|gris`,
`--metodo directo|integral`, `--repeticiones N` (mediana de tiempos). Genera el archivo `.qt`, la imagen
reconstruida y una figura *original | reconstruida | divisiones del árbol*, e imprime las métricas.

## Estructura del repositorio

```
quadtree/
  nodo.py            NodoQuadtree (región, color si es hoja, referencias a hijos)
  constructor.py     dividir_region + criterio de uniformidad + construcción recursiva (Divide y Vencerás)
  reconstruccion.py  reconstruir() a partir del árbol; dibujar_divisiones()
  almacenamiento.py  formato binario .qt: serializar() / deserializar() / desglose de bits
  metricas.py        MSE, PSNR, razón de compresión, estadísticas del árbol
  evaluacion.py      comprimir_y_evaluar(): tiempos separados + métricas en una llamada
  generador.py       imágenes sintéticas reproducibles (semilla fija)
  imagen.py          carga/guardado como matrices (alto, ancho, canales) uint8
  visualizacion.py   figuras comparativas
tests/               pruebas unittest
generar_imagenes.py  crea imagenes_prueba/
experimentos.py      experimentos + tablas + gráficas -> resultados/
evidencias.py        ejemplos para el Entregable 4 -> evidencias/
comprimir.py         interfaz de consola
```

## Decisiones de diseño

**Representación.** Imagen = `ndarray` `uint8` de forma `(alto, ancho, canales)` con 3 canales (RGB) o 1
(grises; también con eje de canales, para tratar ambos casos igual). Un píxel es la tupla de sus canales.

**Criterio de uniformidad.** Para una región de `n` píxeles y `C` canales:

```
MSE_región = Σ_c Σ_p (p_c − m_c)² / (n·C)  ≤  tolerancia        (m_c = media del canal c)
```

Es decir, la varianza media respecto al color medio. Se evalúa con aritmética **entera**
(`Σ_c [n·Σp² − (Σp)²] ≤ tol·n²·C`), así que `tolerancia = 0` exige uniformidad exacta sin errores de redondeo
y la compresión es **sin pérdida**. El color de una hoja es la media por canal redondeada (mitad hacia arriba).
Consecuencia verificada en las pruebas: **MSE global ≤ tolerancia + 0.25** (error de cada región más el
redondeo de la media).

**Partición para dimensiones arbitrarias.** Una dimensión `d` se parte en `⌈d/2⌉` y `d − ⌈d/2⌉`; si `d = 1`
no se parte en esa dirección. Así los hijos son disjuntos, cubren todos los píxeles, nunca están vacíos y
cada uno tiene estrictamente menos píxeles que su padre (la recursión siempre avanza al caso base). Un nodo
interno tiene 4 hijos, o 2 si la región mide una sola fila o columna.

**Divide y Vencerás.** *Dividir*: si la región no es uniforme y tiene más de 1 píxel, se obtienen sus
subregiones. *Resolver*: recursión sobre cada una; casos base: región uniforme o de 1×1 → hoja con color.
*Combinar*: los nodos resultantes se enlazan bajo un nodo padre.

**Formato de almacenamiento (.qt).** Cabecera de 5 bytes (ancho 16 bits, alto 16 bits, canales 8 bits) y flujo
de bits en preorden: 1 bit por nodo con más de 1 píxel (1 = interno, 0 = hoja) y 8 bits por canal en cada hoja.
Las posiciones y tamaños no se guardan: se recalculan con la misma función de partición. El **tamaño real** es
la longitud en bytes del archivo; los experimentos decodifican el archivo y comprueban que la imagen resultante
coincide con la reconstruida desde el árbol.

**Métricas.** MSE y PSNR (sobre todos los valores de la imagen), razón de compresión
`bytes_originales / bytes_comprimidos` con `bytes_originales = alto·ancho·canales` (matriz cruda), ahorro (%)
y bits por píxel. Una razón < 1 significa que el método **expande** la imagen; esos casos se reportan en
`resultados/tablas.md`.

**Optimización opcional.** `--metodo integral` evalúa cada región en O(1) con imágenes integrales de `p` y `p²`
(preprocesamiento Θ(n·C), memoria extra de 2 tablas `int64`). Produce exactamente el mismo árbol (verificado en
las pruebas). En esta implementación en Python el tiempo real casi no cambia porque domina el costo por nodo del
intérprete; la ventaja teórica se aprecia mejor en el conteo `pixeles_evaluados` de los resultados.

## Resumen del análisis de complejidad

Entrada: `n = alto·ancho` píxeles. Operación fundamental: lectura de un píxel (más O(1) aritmética por región).

| | Mejor caso | Peor caso |
|---|---|---|
| Recurrencia (directo) | `T(n) = Θ(n)` — imagen uniforme, una sola comprobación | `T(n) = 4T(n/4) + Θ(n)` ⇒ `Θ(n log n)` (método maestro, caso 2) |
| Recurrencia (integral) | `Θ(n)` de preprocesamiento | `T(n) = 4T(n/4) + Θ(1)` ⇒ `Θ(n)` (caso 1) + preprocesamiento `Θ(n)` |
| Espacio del árbol | `O(1)` | `O(n)` (a lo sumo `2n − 1` nodos) |
| Pila de recursión | `O(log n)` en ambos: profundidad ≤ `⌈log₂ max(alto, ancho)⌉` | |

El costo de **recorrer** el árbol es Θ(nodos) y el de **reconstruir** la imagen es Θ(n) (cada píxel se escribe
una vez); `comprimir_y_evaluar` mide por separado construcción, serialización y reconstrucción. El desarrollo
completo va en el reporte técnico.

## Experimentos

`experimentos.py` produce en `resultados/`:

* `resultados.csv` — 4 tipos (uniforme, regiones, detalle, ruido) × 3 tamaños (64, 128, 256) × 3 tolerancias
  (0, 50, 500) × 2 métodos. Columnas: imagen, dimensiones, tolerancia, tiempos de construcción /
  serialización / reconstrucción, nodos, hojas, profundidad, bytes originales y comprimidos, razón, MSE, PSNR…
* `barrido_tolerancia.csv` — 256×256 con 11 tolerancias (0 a 2500).
* `escalado.csv` — tamaños 32 a 512 con tolerancia 0.
* `tablas.md` y `graficas/*.png`.

Las imágenes se generan con semilla fija, de modo que todo salvo los tiempos es idéntico en cada ejecución.
El tipo **ruido** (peor caso, sin redundancia) se añade a los tres tipos exigidos para mostrar cuándo el
Quadtree no comprime.

## Dependencias

| Biblioteca | Uso |
|---|---|
| NumPy | matrices de píxeles y sumas por región |
| Pillow | leer/escribir archivos de imagen |
| Matplotlib | figuras comparativas y gráficas |

## Uso de IA generativa

Se utilizó Claude (Anthropic) como asistente para generar la estructura inicial del repositorio:
el código del paquete `quadtree/`, las pruebas, los scripts de experimentos y evidencias, y el
borrador de este README. El equipo escribió las instrucciones (prompts) a partir del enunciado
del proyecto.

**Revisión del equipo:**
- Leímos y ejecutamos todo el código; las pruebas pasan en nuestras máquinas.
- Revisamos el criterio de uniformidad, la partición para dimensiones impares y el formato de
  almacenamiento, y podemos explicarlos.
- Modificamos: Ninguna

**Verificación de comprensión:** Cessar Emilio Lopez Rios fue el encargado de verificar y atender la recurrencia de este proyecto desde el codigo .

Integrantes: 

- Hernandez Tello Axel 
- Lopez Rios Cesar Emilio
- Solorio Mateo Alma Angelica 
- Tellez Sanchez Bryan Alexis 

## Limitaciones

* Prototipo en Python puro con recursión por nodo: pensado para imágenes de hasta unos cientos de píxeles por lado.
* Las dimensiones están limitadas a 65 535 por el formato (16 bits).
* Un único color por hoja (la media): no hay predicción ni codificación de entropía, por lo que en imágenes
  naturales con mucho detalle y tolerancia baja el árbol puede ocupar más que la imagen original.
