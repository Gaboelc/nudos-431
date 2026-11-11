"""Página de prueba de las mejoras del render (T7b).

Las mejoras se deciden en papel, no en la pantalla: esta página pone, a su tamaño impreso,
algunas imágenes de los nudos ya aprobados como salen hoy y con cada mejora por separado
(y con las cuatro juntas), en color y en gris. Gabriel la imprime y elige cuáles entran.

Todo queda en build/mejoras/: las imágenes de cada variante en <variante>/, sus versiones
en gris en gris/<variante>/ y la página en prueba.pdf, con una hoja en color y otra en gris
para cada imagen, para imprimirlas por las dos caras.
"""
from __future__ import annotations

import html
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageOps

from . import BUILD
from .construir import Modelo, construir
from .exportar import SITIO
from .imprimir import CELDA_MM, MEJORAS, ImpresionError, Imagen, _guardar, chrome, dibujar, imagenes
from .spec import cargar

DESTINO = BUILD / "mejoras"

# Qué se compara: (slug, imagen de la ficha). El paso 7 del as de guía, el par del error
# del ballestrinque, el paso de la vuelta de escota donde la delgada pasa bajo sí misma y
# los ahorcados del amarre, que pasan sobre las vueltas y bajo los palos.
MUESTRAS = (
    ("as-de-guia", "paso-7"),
    ("ballestrinque", "error-correcto"),
    ("ballestrinque", "error"),
    ("vuelta-de-escota", "paso-4"),
    ("amarre-cuadrado", "paso-5"),
)

# (carpeta, título, mejoras, qué mirar)
VARIANTES = (
    ("hoy", "Hoy", (), "Como salen hoy las imágenes de las fichas."),
    ("contorno", "1. Contorno", ("contorno",),
     "Un borde de tinta de 0,25 mm en cada cuerda y en los palos. En cada cruce, el borde de "
     "la de encima corta a la de abajo."),
    ("contacto", "2. Sombra de contacto", ("contacto",),
     "La cuerda se oscurece justo donde otra la toca o la cruza, y donde toca un palo."),
    ("supermuestreo", "3. Supermuestreo", ("supermuestreo",),
     "Cada imagen se dibuja al doble y se reduce: bordes y letras más limpios."),
    ("sombras-suaves", "4. Sombras suaves", ("sombras-suaves",),
     "La sombra sobre la mesa es más clara y de borde blando, sobre todo la del poste y la "
     "de los palos."),
    ("todas", "Las cuatro juntas", MEJORAS, "Las cuatro mejoras a la vez."),
)


def lista(modelos: dict[str, Modelo]) -> list[tuple[str, Imagen, list[Imagen]]]:
    """Para cada muestra: su nudo, la imagen de la ficha y esa imagen en cada variante."""
    out = []
    for slug, nombre in MUESTRAS:
        base = {i.nombre: i for i in imagenes(modelos[slug])}[nombre]
        out.append((slug, base, [replace(base, nombre=f"{clave}/{slug}-{nombre}", mejoras=mej)
                                 for clave, _, mej, _ in VARIANTES]))
    return out


def construir_muestras() -> dict[str, Modelo]:
    """Construye los nudos de las muestras. Ninguno puede tener fallas."""
    modelos = {}
    for slug in dict.fromkeys(s for s, _ in MUESTRAS):
        m = construir(cargar(slug))
        if m.fallas:
            raise ImpresionError(f"{slug} tiene fallas; no se arma la página de prueba:\n"
                                 + "\n".join(f"  - {f}" for f in m.fallas))
        modelos[slug] = m
    return modelos


def pagina_mejoras(modelos: dict[str, Modelo], carpeta: Path = DESTINO) -> Path:
    """Dibuja las imágenes y escribe carpeta/prueba.pdf. Devuelve la ruta del PDF."""
    muestras = lista(modelos)
    dibujar([v for _, _, variantes in muestras for v in variantes], carpeta)
    # Versiones en gris: lo que daría una impresora sin color.
    for _, _, variantes in muestras:
        for v in variantes:
            with Image.open(carpeta / f"{v.nombre}.png") as im:
                _guardar(ImageOps.grayscale(im), carpeta / "gris" / f"{v.nombre}.png")

    leyenda = "".join(f"<li><b>{html.escape(t)}.</b> {html.escape(q)}</li>"
                      for _, t, _, q in VARIANTES)

    def hoja(slug: str, base: Imagen, variantes: list[Imagen], gris: bool) -> str:
        celdas = "".join(
            f'<figure><img src="{"gris/" if gris else ""}{v.nombre}.png">'
            f'<figcaption>{html.escape(t)}</figcaption></figure>'
            for v, (_, t, _, _) in zip(variantes, VARIANTES))
        nudo = modelos[slug].spec.nombre
        modo = "escala de grises" if gris else "color"
        return (f'<section class="hoja"><header><h1>Mejoras del render · {html.escape(nudo)}, '
                f'{html.escape(base.titulo.lower())} · {modo}</h1>'
                f'<p>Imprime a tamaño real (100 %, sin «ajustar a la página»). Cada imagen mide '
                f'{CELDA_MM[0]:g} × {CELDA_MM[1]:g} mm, como en la ficha, y la línea mide 50 mm. '
                f'Compara cada mejora con «Hoy»: ¿se ve mejor qué tramo va encima en cada cruce?'
                f'</p><div class="regla"></div></header>'
                f'<div class="rejilla">{celdas}</div><ul class="leyenda">{leyenda}</ul></section>')

    hojas = "\n".join(hoja(slug, base, variantes, gris)
                      for slug, base, variantes in muestras for gris in (False, True))
    fuentes = (SITIO / "vendor" / "fuentes").as_uri()
    documento = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><style>
@font-face {{ font-family: "Literata"; font-weight: 400; src: url("{fuentes}/literata-latin-400-normal.woff2"); }}
@font-face {{ font-family: "Literata"; font-weight: 600; src: url("{fuentes}/literata-latin-600-normal.woff2"); }}
@page {{ size: letter; margin: 12mm; }}
body {{ margin: 0; font-family: "Literata", serif; color: #16202f; }}
.hoja {{ break-after: page; }}
.hoja:last-child {{ break-after: auto; }}
h1 {{ font-size: 12pt; font-weight: 600; margin: 0 0 1.5mm; }}
p {{ font-size: 8.5pt; line-height: 1.35; margin: 0 0 2mm; max-width: 186mm; }}
.regla {{ width: 50mm; height: 0; border-top: 0.4mm solid #16202f; margin: 0 0 4mm; }}
.rejilla {{ display: grid; grid-template-columns: repeat(3, {CELDA_MM[0]}mm); gap: 3mm 6mm; }}
figure {{ margin: 0; }}
img {{ display: block; width: {CELDA_MM[0]}mm; height: {CELDA_MM[1]}mm; outline: 0.2mm solid #ccd4db; }}
figcaption {{ font-size: 8pt; font-weight: 600; margin-top: 1mm; }}
.leyenda {{ font-size: 8pt; line-height: 1.35; margin: 6mm 0 0; padding-left: 4mm; max-width: 186mm; }}
.leyenda li {{ margin-bottom: 1mm; }}
</style></head><body>
{hojas}
</body></html>"""
    origen = carpeta / "prueba.html"
    origen.write_text(documento, encoding="utf-8")
    destino = carpeta / "prueba.pdf"
    with chrome() as navegador:
        pagina = navegador.new_page()
        pagina.goto(origen.as_uri(), wait_until="load")
        pagina.pdf(path=str(destino), prefer_css_page_size=True, print_background=True)
    return destino
