"""La página de prueba del motor (T15d): cada piloto como sale hoy y con el motor, en color y
en gris, para que Gabriel la apruebe en papel.

`python -m nudos prueba-motor` construye los pilotos de la fase 2 dos veces, sin el motor y con
él (la opción `--motor` de `construir`, que pone NUDOS_MOTOR=1), dibuja las imágenes de la ficha
de cada uno (los pasos, el error junto al paso bien hecho y el terminado por delante y por
detrás) y arma build/motor/prueba.pdf: una hoja por nudo, con cada imagen de hoy junto a la del
motor, y la misma hoja en gris. Si un nudo tiene fallas con el motor, se dibuja igual y sus
fallas van en la hoja: es una prueba, no una ficha.

Las imágenes van al 76 % (44 mm de ancho en vez de 58) para que cada par quepa en media fila.
"""
from __future__ import annotations

import html
import os
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageOps

from . import BUILD
from .construir import Modelo
from .imprimir import Imagen, _guardar, dibujar, imagenes
from .mejoras import _pdf
from .procesos import construir_varios
from .spec import cargar

DESTINO = BUILD / "motor"
PILOTOS = ("as-de-guia", "ballestrinque", "vuelta-de-escota", "amarre-cuadrado")
ANCHO_MM = 44.0
POR_HOJA = 8        # pares de imágenes por hoja: cuatro filas de dos

ESTILO = f"""<style>
.pares {{ display: grid; grid-template-columns: repeat(4, {ANCHO_MM}mm); gap: 2mm 4mm; }}
.pares img {{ width: {ANCHO_MM}mm; height: {ANCHO_MM * 64 / 58:.2f}mm; }}
.pares figure:nth-child(4n + 3) {{ margin-left: 2mm; }}
.fallas {{ font-size: 7.5pt; color: #8a1c1c; margin: 0 0 2mm; }}
</style>"""


def construir_pilotos(slugs=PILOTOS) -> dict[str, tuple[Modelo, Modelo]]:
    """Cada piloto sin el motor y con él. Los procesos de cada grupo heredan la opción
    (nudos/procesos.py abre un grupo por cada valor de NUDOS_MOTOR)."""
    antes = os.environ.get("NUDOS_MOTOR")
    specs = [cargar(s) for s in slugs]
    try:
        os.environ["NUDOS_MOTOR"] = ""
        hoy = construir_varios(specs)
        os.environ["NUDOS_MOTOR"] = "1"
        motor = construir_varios(specs)
    finally:
        if antes is None:
            os.environ.pop("NUDOS_MOTOR", None)
        else:
            os.environ["NUDOS_MOTOR"] = antes
    return {s: (h, m) for s, h, m in zip(slugs, hoy, motor)}


def _dibujar(modelos: dict[str, tuple[Modelo, Modelo]], carpeta: Path) -> dict[str, list[tuple[Imagen, Imagen]]]:
    """Dibuja las imágenes de los dos modelos de cada nudo, en color y en gris (carpeta/gris/),
    y devuelve los pares (hoy, motor) de cada nudo."""
    pares, todas = {}, []
    for slug, (hoy, motor) in modelos.items():
        a = [replace(v, nombre=f"{slug}/hoy-{v.nombre}") for v in imagenes(hoy)]
        b = {v.nombre: replace(v, nombre=f"{slug}/motor-{v.nombre}") for v in imagenes(motor)}
        pares[slug] = [(v, b[v.nombre.split("/hoy-")[1]]) for v in a
                       if v.nombre.split("/hoy-")[1] in b]
        todas += [v for par in pares[slug] for v in par]
    dibujar(todas, carpeta)
    for v in todas:
        with Image.open(carpeta / f"{v.nombre}.png") as im:
            _guardar(ImageOps.grayscale(im), carpeta / "gris" / f"{v.nombre}.png")
    return pares


def pagina(modelos: dict[str, tuple[Modelo, Modelo]], carpeta: Path = DESTINO) -> Path:
    """Dibuja las imágenes y escribe carpeta/prueba.pdf. Devuelve la ruta."""
    carpeta.mkdir(parents=True, exist_ok=True)
    pares = _dibujar(modelos, carpeta)

    def hoja(slug: str, grupo, gris: bool, parte: str) -> str:
        hoy, motor = modelos[slug]
        celdas = "".join(
            f'<figure><img src="{"gris/" if gris else ""}{a.nombre}.png">'
            f'<figcaption>{html.escape(a.titulo)}<span>hoy</span></figcaption></figure>'
            f'<figure><img src="{"gris/" if gris else ""}{b.nombre}.png">'
            f'<figcaption>{html.escape(b.titulo)}<span>con el motor</span></figcaption></figure>'
            for a, b in grupo)
        fallas = "".join(f"<li>{html.escape(f)}</li>" for f in motor.fallas)
        fallas = f'<ul class="fallas">Con el motor tiene fallas:{fallas}</ul>' if fallas else ""
        modo = "escala de grises" if gris else "color"
        return (f'<section class="hoja"><header><h1>El motor de física · '
                f'{html.escape(hoy.spec.nombre)}{parte} · {modo}</h1>'
                f'<p>Cada imagen de la ficha como sale hoy y, a su derecha, con el motor: los pasos '
                f'asentados y el terminado apretado. Van al 76 % ({ANCHO_MM:g} mm de ancho en vez '
                f'de 58); la línea mide 50 mm. ¿Se ve mejor la cuerda con el motor? ¿Se sigue '
                f'viendo qué tramo va encima en cada cruce?</p><div class="regla"></div>{fallas}'
                f'</header><div class="pares">{celdas}</div></section>')

    hojas = [ESTILO]
    for slug, lista in pares.items():
        grupos = [lista[i:i + POR_HOJA] for i in range(0, len(lista), POR_HOJA)]
        for gris in (False, True):
            for k, grupo in enumerate(grupos):
                parte = f" ({k + 1} de {len(grupos)})" if len(grupos) > 1 else ""
                hojas.append(hoja(slug, grupo, gris, parte))
    return _pdf("\n".join(hojas), carpeta, "prueba")
