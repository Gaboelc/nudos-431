"""La página de prueba de T16 y T15g: las imágenes de la ficha de los pilotos como salen hoy, con
three.js, y con Blender, en color y en gris, para que Gabriel la apruebe en papel.

`python -m nudos prueba-blender` construye los pilotos con el motor de física (como saldrán las
fichas desde T19), dibuja cada imagen de la ficha con three.js y con Blender y arma
build/blender/prueba.pdf: una hoja por nudo, con cada imagen de hoy junto a la de Blender, y la
misma hoja en gris. Al final, la hoja de T15g: la sección aplastada contra la madera, con la cuerda
redonda al lado, a su tamaño y ampliada.

Las imágenes van al 76 % (44 mm de ancho en vez de 58), como en la página del motor (T15d), para
que cada par quepa en media fila. Las fichas de los pilotos, a tamaño real, salen con
`python -m nudos --motor ficha <slug>`.
"""
from __future__ import annotations

import html
import os
import time
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageOps

from . import BUILD
from .construir import Modelo
from .imprimir import CELDA_MM, Imagen, _guardar, dibujar, dibujar_blender, imagenes
from .mejoras import _pdf
from .procesos import construir_varios
from .prueba_motor import ANCHO_MM, ESTILO, PILOTOS, POR_HOJA
from .spec import cargar

DESTINO = BUILD / "blender"
# T15g: las imágenes donde la cuerda más se aplasta contra la madera (medido el 25 nov de 2026).
APLASTADAS = (("ballestrinque", "terminado-frente"), ("amarre-cuadrado", "paso-3"))
AMPLIAR = 3        # la zona del centro, ampliada tres veces


def construir_pilotos(slugs=PILOTOS) -> dict[str, Modelo]:
    """Los pilotos con el motor de física."""
    antes = os.environ.get("NUDOS_MOTOR")
    try:
        os.environ["NUDOS_MOTOR"] = "1"
        modelos = construir_varios([cargar(s) for s in slugs])
    finally:
        if antes is None:
            os.environ.pop("NUDOS_MOTOR", None)
        else:
            os.environ["NUDOS_MOTOR"] = antes
    return {m.spec.slug: m for m in modelos}


def _gris(carpeta: Path, nombres) -> None:
    for n in nombres:
        with Image.open(carpeta / f"{n}.png") as im:
            _guardar(ImageOps.grayscale(im), carpeta / "gris" / f"{n}.png")


def _zona(carpeta: Path, nombre: str, destino: str) -> None:
    """El centro de la imagen, ampliado AMPLIAR veces."""
    with Image.open(carpeta / f"{nombre}.png") as im:
        w, h = im.size
        cw, ch = w // AMPLIAR, h // AMPLIAR
        caja = ((w - cw) // 2, (h - ch) // 2, (w - cw) // 2 + cw, (h - ch) // 2 + ch)
        _guardar(im.crop(caja).resize(im.size, Image.Resampling.LANCZOS), carpeta / f"{destino}.png")


def pagina(modelos: dict[str, Modelo], carpeta: Path = DESTINO, avisar=print) -> Path:
    """Dibuja las imágenes y escribe carpeta/prueba.pdf. Devuelve la ruta."""
    carpeta.mkdir(parents=True, exist_ok=True)
    pares: dict[str, list[tuple[Imagen, Imagen]]] = {}
    tiempos: dict[str, float] = {}
    for slug, m in modelos.items():
        imgs = imagenes(m)
        hoy = [replace(v, nombre=f"{slug}/hoy-{v.nombre}") for v in imgs]
        bl = [replace(v, nombre=f"{slug}/blender-{v.nombre}") for v in imgs]
        dibujar(hoy, carpeta, render="threejs")
        t = time.perf_counter()
        dibujar_blender(bl, carpeta)
        tiempos[slug] = time.perf_counter() - t
        avisar(f"{slug}: {len(bl)} imágenes con Blender en {tiempos[slug]:.0f} s")
        _gris(carpeta, [v.nombre for v in hoy + bl])
        pares[slug] = list(zip(hoy, bl))
    # T15g: las mismas imágenes con la cuerda redonda.
    aplastadas = []
    for slug, nombre in APLASTADAS:
        if slug not in modelos:
            continue
        img = next(v for v in imagenes(modelos[slug]) if v.nombre == nombre)
        dibujar_blender([replace(img, nombre=f"{slug}/redonda-{nombre}")], carpeta, aplastar=False)
        for x in ("redonda", "blender"):
            _zona(carpeta, f"{slug}/{x}-{nombre}", f"{slug}/{x}-{nombre}-zona")
        _gris(carpeta, [f"{slug}/{x}-{nombre}{z}" for x in ("redonda", "blender") for z in ("", "-zona")])
        aplastadas.append((slug, img))

    def fig(nombre, titulo, nota, gris):
        return (f'<figure><img src="{"gris/" if gris else ""}{nombre}.png">'
                f'<figcaption>{html.escape(titulo)}<span>{html.escape(nota)}</span></figcaption></figure>')

    def hoja(slug, grupo, gris, parte):
        m = modelos[slug]
        celdas = "".join(fig(a.nombre, a.titulo, "hoy (three.js)", gris)
                         + fig(b.nombre, b.titulo, "Blender", gris) for a, b in grupo)
        modo = "escala de grises" if gris else "color"
        return (f'<section class="hoja"><header><h1>Las fichas en Blender · {html.escape(m.spec.nombre)}'
                f'{parte} · {modo}</h1><p>Cada imagen de la ficha como sale hoy y, a su derecha, '
                f'dibujada con Blender, las dos con la cuerda del motor de física. Van al 76 % '
                f'({ANCHO_MM:g} mm de ancho en vez de {CELDA_MM[0]:g}); la línea mide 50 mm. Blender '
                f'tardó {tiempos[slug]:.0f} s en las {len(pares[slug])} imágenes. ¿Se ve mejor la '
                f'cuerda? ¿Se sigue viendo qué tramo va encima en cada cruce? ¿Los nombres quedan '
                f'en su lugar?</p><div class="regla"></div></header>'
                f'<div class="pares">{celdas}</div></section>')

    def hoja_aplastado(gris):
        modo = "escala de grises" if gris else "color"
        celdas = "".join(
            fig(f"{slug}/redonda-{img.nombre}", f"{modelos[slug].spec.nombre}, {img.titulo.lower()}",
                "redonda", gris)
            + fig(f"{slug}/blender-{img.nombre}", f"{modelos[slug].spec.nombre}, {img.titulo.lower()}",
                  "aplastada", gris)
            + fig(f"{slug}/redonda-{img.nombre}-zona", f"El centro, ampliado {AMPLIAR} veces", "redonda", gris)
            + fig(f"{slug}/blender-{img.nombre}-zona", f"El centro, ampliado {AMPLIAR} veces", "aplastada", gris)
            for slug, img in aplastadas)
        return (f'<section class="hoja"><header><h1>T15g: la sección aplastada · {modo}</h1>'
                f'<p>Donde la cuerda aprieta contra la madera, su sección se aplana contra el palo y '
                f'se ensancha de lado, con la misma área. Son las dos imágenes donde más se aplasta '
                f'(hasta un 7 % del radio); a la izquierda de cada par, la cuerda redonda. Entre dos '
                f'cuerdas no se aplasta: el motor las deja siempre a más de un diámetro (1,02 como '
                f'mínimo en los pilotos). La torsión no se ve: con el chicote suelto, la cuerda no '
                f'guarda torsión, y la trenza sigue el marco sin torsión del motor, como ya hacía '
                f'three.js. ¿Se nota el aplastado a tamaño de ficha?</p><div class="regla"></div>'
                f'</header><div class="pares">{celdas}</div></section>')

    hojas = [ESTILO]
    for slug, lista in pares.items():
        grupos = [lista[i:i + POR_HOJA] for i in range(0, len(lista), POR_HOJA)]
        for gris in (False, True):
            for k, grupo in enumerate(grupos):
                parte = f" ({k + 1} de {len(grupos)})" if len(grupos) > 1 else ""
                hojas.append(hoja(slug, grupo, gris, parte))
    if aplastadas:
        hojas += [hoja_aplastado(False), hoja_aplastado(True)]
    return _pdf("\n".join(hojas), carpeta, "prueba")
