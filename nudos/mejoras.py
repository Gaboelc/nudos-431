"""Páginas de prueba de las mejoras del render (T7b) y del nudo terminado apretado (T7c).

Las mejoras se deciden en papel, no en la pantalla: estas páginas ponen, a su tamaño impreso,
imágenes de los nudos ya aprobados con y sin cada mejora, en color y en gris.

- prueba.pdf: algunas imágenes sin mejoras, con cada mejora por separado y con todas juntas.
  Con ella Gabriel eligió las que entraron (el 10 de noviembre de 2026: todas menos el
  contorno de tinta, que se quitó). Sirve para volver a mirarlas o para probar una nueva.
- apretado.pdf: el nudo terminado, por delante y por detrás, como sale hoy, a medias (la
  mitad de las rondas) y apretado (nudos/apretar.py). La columna a medias está por si el
  apretado del todo esconde algún cruce. Va cada nudo que se aprieta; el amarre no, porque su
  plantilla ya traza la cuerda tensa.

Todo queda en build/mejoras/: las imágenes de cada variante en <variante>/ y las del
apretado en apretado/, sus versiones en gris en gris/ y las dos páginas, con una hoja en color
y otra en gris para cada imagen o nudo, para imprimirlas por las dos caras.
"""
from __future__ import annotations

import html
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageOps

from . import BUILD
from .apretar import RONDAS, apretado
from .construir import Modelo, construir
from .exportar import SITIO
from .imprimir import (CELDA_MM, MEJORAS, ImpresionError, Imagen, _guardar, chrome, dibujar,
                       imagenes, terminado)
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
    ("sin-mejoras", "Sin mejoras", (), "Como salían las imágenes de las fichas antes de T7b."),
    ("contacto", "1. Sombra de contacto", ("contacto",),
     "La cuerda se oscurece justo donde otra la toca o la cruza, y donde toca un palo."),
    ("supermuestreo", "2. Supermuestreo", ("supermuestreo",),
     "Cada imagen se dibuja al doble y se reduce: bordes y letras más limpios."),
    ("sombras-suaves", "3. Sombras suaves", ("sombras-suaves",),
     "La sombra sobre la mesa es más clara y de borde blando, sobre todo la del poste y la "
     "de los palos."),
    ("todas", "Todas juntas", MEJORAS, "Como salen ahora las imágenes de las fichas."),
)

# Los nudos del apretado: los publicados que se aprietan.
APRETADOS = ("as-de-guia", "ballestrinque", "vuelta-de-escota")
# (clave, título, rondas, qué es). Con 0 rondas es el último paso tal cual.
GRADOS = (
    ("hoy", "Hoy", 0, "El último paso, como sale hoy en la ficha: la cuerda con el largo que "
     "tenía al atarlo."),
    ("a-medias", "A medias", RONDAS // 2, f"La cuerda acortada dentro del nudo la mitad de las "
     f"rondas ({RONDAS // 2} de {RONDAS}), por si el apretado del todo esconde algún cruce."),
    ("apretado", "Apretado", RONDAS, "Apretado del todo: la ronda más apretada que conserva "
     "todos los cruces y los límites."),
)


def lista(modelos: dict[str, Modelo]) -> list[tuple[str, Imagen, list[Imagen]]]:
    """Para cada muestra: su nudo, la imagen de la ficha y esa imagen en cada variante."""
    out = []
    for slug, nombre in MUESTRAS:
        base = {i.nombre: i for i in imagenes(modelos[slug])}[nombre]
        out.append((slug, base, [replace(base, nombre=f"{clave}/{slug}-{nombre}", mejoras=mej)
                                 for clave, _, mej, _ in VARIANTES]))
    return out


def lista_apretado(modelos: dict[str, Modelo]) -> list[tuple[str, list[tuple[tuple[str, str], list[Imagen]]]]]:
    """Para cada nudo que se aprieta y cada uno de los GRADOS: cuánta cuerda se quitó del nudo,
    por delante y por detrás, y las imágenes del terminado por delante y por detrás, con las
    mejoras de las fichas."""
    out = []
    for slug in APRETADOS:
        m = modelos[slug]
        final = m.pasos[-1]
        grados = []
        for clave, _, rondas, _ in GRADOS:
            if rondas == 0:
                delante, detras = final, m.reverso
            elif rondas == RONDAS:
                delante, detras = m.apretado, m.reverso_apretado
            else:
                delante, detras = apretado(m.spec, final, m.reverso, rondas)
            # Sobre un poste, por detrás es el mismo nudo mirado desde el otro lado.
            cuanto = (_cuanto(final, delante, rondas), _cuanto(final, delante, rondas)
                      if m.reverso is None else _cuanto(m.reverso, detras, rondas))
            grados.append((cuanto, terminado(m, delante, detras, prefijo=f"apretado/{slug}-{clave}")))
        out.append((slug, grados))
    return out


def _cuanto(antes, despues, rondas: int) -> str:
    """Cuánta cuerda se quitó del nudo al apretarlo, para el pie de la imagen."""
    if not rondas:
        return "como en la ficha"
    if despues is antes:
        return "no se pudo apretar: queda como hoy"
    menos = antes.medidas["largo"] - despues.medidas["largo"]
    if menos < 0.5:
        return "casi el mismo largo de cuerda"
    return f"{menos:.1f}".replace(".", ",") + " diámetros de cuerda menos"


def construir_muestras() -> dict[str, Modelo]:
    """Construye los nudos de las muestras. Ninguno puede tener fallas."""
    modelos = {}
    for slug in dict.fromkeys([s for s, _ in MUESTRAS] + list(APRETADOS)):
        m = construir(cargar(slug))
        if m.fallas:
            raise ImpresionError(f"{slug} tiene fallas; no se arma la página de prueba:\n"
                                 + "\n".join(f"  - {f}" for f in m.fallas))
        modelos[slug] = m
    return modelos


def pagina_mejoras(modelos: dict[str, Modelo], carpeta: Path = DESTINO) -> Path:
    """Dibuja las imágenes y escribe carpeta/prueba.pdf. Devuelve la ruta del PDF."""
    muestras = lista(modelos)
    _dibujar_con_gris([v for _, _, variantes in muestras for v in variantes], carpeta)
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
                f'Compara cada mejora con «Sin mejoras»: ¿se ve mejor qué tramo va encima en cada cruce?'
                f'</p><div class="regla"></div></header>'
                f'<div class="rejilla">{celdas}</div><ul class="leyenda">{leyenda}</ul></section>')

    hojas = "\n".join(hoja(slug, base, variantes, gris)
                      for slug, base, variantes in muestras for gris in (False, True))
    return _pdf(hojas, carpeta, "prueba")


def pagina_apretado(modelos: dict[str, Modelo], carpeta: Path = DESTINO) -> Path:
    """Dibuja las imágenes del terminado y escribe carpeta/apretado.pdf. Devuelve la ruta."""
    nudos = lista_apretado(modelos)
    _dibujar_con_gris([i for _, grados in nudos for _, imgs in grados for i in imgs], carpeta)
    leyenda = "".join(f"<li><b>{html.escape(t)}.</b> {html.escape(q)}</li>"
                      for _, t, _, q in GRADOS)

    def hoja(slug: str, grados, gris: bool) -> str:
        s = modelos[slug].spec
        celdas = []
        for lado, cual in ((0, "por delante"), (1, "por detrás")):
            for (cuanto, imgs), (_, titulo, _, _) in zip(grados, GRADOS):
                celdas.append(f'<figure><img src="{"gris/" if gris else ""}{imgs[lado].nombre}.png">'
                              f'<figcaption>{html.escape(titulo)}, {cual}'
                              f'<span>{html.escape(cuanto[lado])}</span></figcaption></figure>')
        modo = "escala de grises" if gris else "color"
        notas = []
        if s.anfitrion is not None:
            notas.append("Sobre el poste, por detrás es el mismo nudo mirado desde el otro lado.")
        if s.cuerdas and len({c.grosor for c in s.cuerdas}) > 1:
            notas.append("Con cuerdas de distinto grosor, la gruesa conserva su forma y se ajusta "
                         "la delgada alrededor.")
        return (f'<section class="hoja"><header><h1>Nudo terminado apretado · '
                f'{html.escape(s.nombre)} · {modo}</h1>'
                f'<p>Imprime a tamaño real (100 %, sin «ajustar a la página»). Cada imagen mide '
                f'{CELDA_MM[0]:g} × {CELDA_MM[1]:g} mm, como en la ficha, y la línea mide 50 mm. '
                f'Arriba, el nudo por delante; abajo, por detrás. ¿Cuál se parece más a como queda '
                f'el nudo de verdad? ¿Se sigue viendo qué tramo va encima en cada cruce? '
                f'{html.escape(" ".join(notas))}</p><div class="regla"></div></header>'
                f'<div class="rejilla">{"".join(celdas)}</div>'
                f'<ul class="leyenda">{leyenda}</ul></section>')

    hojas = "\n".join(hoja(slug, grados, gris) for slug, grados in nudos for gris in (False, True))
    return _pdf(hojas, carpeta, "apretado")


def _dibujar_con_gris(imgs: list[Imagen], carpeta: Path) -> None:
    """Dibuja las imágenes y guarda además su versión en gris, lo que daría una impresora
    sin color, en carpeta/gris/."""
    dibujar(imgs, carpeta)
    for v in imgs:
        with Image.open(carpeta / f"{v.nombre}.png") as im:
            _guardar(ImageOps.grayscale(im), carpeta / "gris" / f"{v.nombre}.png")


def _pdf(hojas: str, carpeta: Path, nombre: str) -> Path:
    """Escribe carpeta/<nombre>.pdf, en tamaño carta, con estas hojas. Devuelve la ruta."""
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
figcaption span {{ display: block; font-weight: 400; }}
.leyenda {{ font-size: 8pt; line-height: 1.35; margin: 6mm 0 0; padding-left: 4mm; max-width: 186mm; }}
.leyenda li {{ margin-bottom: 1mm; }}
</style></head><body>
{hojas}
</body></html>"""
    origen = carpeta / f"{nombre}.html"
    origen.write_text(documento, encoding="utf-8")
    destino = carpeta / f"{nombre}.pdf"
    with chrome() as navegador:
        pagina = navegador.new_page()
        pagina.goto(origen.as_uri(), wait_until="load")
        pagina.pdf(path=str(destino), prefer_css_page_size=True, print_background=True)
    return destino
