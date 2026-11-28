"""La página de prueba del amarre tallado: las fotos del amarre real de Gabriel arriba y, debajo,
dos columnas, «Hoy» y «Tallado», cada una con el terminado por delante y por detrás y los pasos 3
y 5, para revisarla impresa en papel, en color y en gris.

`python -m nudos prueba-tallado [--hoy <carpeta>] [--tallado <carpeta>]` lee de cada carpeta
`terminado-frente.png`, `terminado-reverso.png`, `paso-3.png` y `paso-5.png`, como los deja
`python -m nudos imprimir` en build/<slug>/impresion/ (por omisión, la del amarre cuadrado de hoy
en las dos). Las fotos son entradas/t15e/amarre-cuadrado-*.jpg (en un worktree, NUDOS_ENTRADAS). Deja en revision/tallado/
(fuera de git, porque lleva fotos) tallado-color.pdf y tallado-gris.pdf.
"""
from __future__ import annotations

import html
import os
from pathlib import Path

from PIL import Image, ImageOps

from . import BUILD, RAIZ
from .mejoras import _pdf

DESTINO = RAIZ / "revision" / "tallado"
HOY = BUILD / "amarre-cuadrado" / "impresion"
FOTOS = tuple(Path(os.environ.get("NUDOS_ENTRADAS", RAIZ / "entradas")) / "t15e" / f"amarre-cuadrado-{n}.jpg" for n in (1, 2, 3, 4))
IMAGENES = (("terminado-frente", "Terminado, de frente"), ("terminado-reverso", "Terminado, por detrás"),
            ("paso-3", "Paso 3"), ("paso-5", "Paso 5"))
ANCHO_MM = 44.0     # cada foto y cada imagen: cuatro fotos en una fila y dos imágenes por columna

ESTILO = f"""<style>
.fotos, .imgs {{ display: grid; grid-template-columns: repeat(4, {ANCHO_MM}mm); gap: 2mm 4mm; }}
.fotos img {{ width: {ANCHO_MM}mm; height: {ANCHO_MM * 4 / 3:.2f}mm; object-fit: cover; }}
.columnas {{ display: grid; grid-template-columns: repeat(2, 92mm); gap: 6mm; margin-top: 4mm; }}
.columnas h2 {{ font-size: 11pt; margin: 0 0 2mm; }}
.imgs {{ grid-template-columns: repeat(2, {ANCHO_MM}mm); }}
.imgs img {{ width: {ANCHO_MM}mm; height: {ANCHO_MM * 64 / 58:.2f}mm; }}
</style>"""


def _preparar(ruta: Path, carpeta: Path, gris: bool, nombre: str) -> str:
    """La dirección de la imagen para el documento; en gris, una copia en carpeta/gris/."""
    if not ruta.is_file():
        raise FileNotFoundError(f"falta {ruta}")
    if not gris:
        return ruta.resolve().as_uri()
    destino = carpeta / "gris" / f"{nombre}.png"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(ruta) as im:
        ImageOps.grayscale(im).save(destino)
    return destino.resolve().as_uri()


def hoja(hoy: Path, tallado: Path, carpeta: Path, gris: bool, fotos=FOTOS) -> str:
    """El HTML de la hoja, en color o en gris (las copias en gris se escriben en carpeta/gris/)."""
    fotos_html = "".join(
        f'<figure><img src="{_preparar(Path(f), carpeta, gris, f"foto-{i}")}">'
        f'<figcaption>Amarre real<span>{html.escape(Path(f).name)}</span></figcaption></figure>'
        for i, f in enumerate(fotos, 1))
    columnas = ""
    for clave, titulo, origen in (("hoy", "Hoy", hoy), ("tallado", "Tallado", tallado)):
        celdas = "".join(
            f'<figure><img src="{_preparar(Path(origen) / f"{n}.png", carpeta, gris, f"{clave}-{n}")}">'
            f'<figcaption>{t}</figcaption></figure>' for n, t in IMAGENES)
        columnas += f'<div><h2>{titulo}</h2><div class="imgs">{celdas}</div></div>'
    modo = "escala de grises" if gris else "color"
    return (f'<section class="hoja"><header><h1>Amarre cuadrado, tallado · {modo}</h1>'
            f'<p>Arriba, el amarre real. Abajo, a la izquierda, el del libro como sale hoy y, a la '
            f'derecha, el prototipo más apretado. Las imágenes van al 76 % ({ANCHO_MM:g} mm de ancho '
            f'en vez de 58); la línea mide 50 mm. ¿Se ve tan apretado como el real? ¿Se sigue viendo '
            f'qué tramo va encima en cada cruce?</p><div class="regla"></div></header>'
            f'<div class="fotos">{fotos_html}</div><div class="columnas">{columnas}</div></section>')


def pagina(hoy: Path = HOY, tallado: Path | None = None, carpeta: Path = DESTINO,
           fotos=FOTOS, pdf: bool = True) -> list[Path]:
    """Escribe carpeta/tallado-color.pdf y tallado-gris.pdf (o, con pdf=False, solo los .html)."""
    tallado = hoy if tallado is None else tallado
    carpeta.mkdir(parents=True, exist_ok=True)
    salidas = []
    for gris in (False, True):
        nombre = "tallado-gris" if gris else "tallado-color"
        cuerpo = ESTILO + hoja(hoy, tallado, carpeta, gris, fotos)
        if pdf:
            salidas.append(_pdf(cuerpo, carpeta, nombre))
        else:
            ruta = carpeta / f"{nombre}.html"
            ruta.write_text(cuerpo, encoding="utf-8")
            salidas.append(ruta)
    return salidas
