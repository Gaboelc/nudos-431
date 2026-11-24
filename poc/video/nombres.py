"""T14b: los nombres «Firme» y «Chicote» sobre las imágenes de Blender, como en las fichas.

render/impresion.js pone los nombres en HTML sobre la imagen de three.js. Aquí se dibujan con
PIL sobre la de Blender, con el mismo estilo (IBM Plex Mono a 8 pt en mayúsculas, fondo blanco
al 90 %, esquinas redondeadas y una línea fina hasta la cuerda) y en el lugar que escribe
poc/blender/escena.py (<imagen>.anclas.json): el primer punto de la cuerda dentro del cuadro
para «Firme» y la punta para «Chicote». Cada nombre se aparta de la cuerda, del lado que da al
borde, y no entra en la esquina que la ficha tapa con el número del paso.

Uso, con el venv del proyecto: python poc/video/nombres.py <png> [--nombres firme chicote]
       [--reservado 274 213] (px de la esquina de arriba a la izquierda)
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[2]
PT = 300 / 72
TINTA = (22, 32, 47)
FUENTE = RAIZ / "sitio" / "vendor" / "fuentes" / "ibm-plex-mono-latin-400-normal.woff2"
TEXTOS = {"firme": "FIRME", "chicote": "CHICOTE"}


def poner(im: Image.Image, anclas: dict, nombres, reservado=(0, 0)) -> Image.Image:
    im = im.convert("RGBA")
    capa = Image.new("RGBA", im.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    fuente = ImageFont.truetype(str(FUENTE), round(8 * PT))
    W, H = im.size
    cx, cy = W / 2, H / 2
    for clave in nombres:
        if clave not in anclas:
            continue
        (px, py), (hx, hy) = anclas[clave]["punto"], anclas[clave]["hacia"]
        texto = " ".join(TEXTOS[clave])[::1].replace(" ", " ") if False else TEXTOS[clave]
        caja = d.textbbox((0, 0), texto, font=fuente)
        tw, th = caja[2] - caja[0] + 2 * 3 * PT + len(texto) * 0.09 * 8 * PT, caja[3] - caja[1] + 2 * 1.2 * PT
        # Perpendicular a la cuerda, del lado que se aleja del centro de la imagen.
        tx, ty = px - hx, py - hy
        n = math.hypot(tx, ty) or 1.0
        ox, oy = -ty / n, tx / n
        if ox * (px - cx) + oy * (py - cy) < 0:
            ox, oy = -ox, -oy
        lejos = 26 * PT
        x = px + ox * lejos - tw / 2
        y = py + oy * lejos - th / 2
        x = min(max(x, 4 * PT), W - tw - 4 * PT)
        y = min(max(y, 4 * PT), H - th - 4 * PT)
        if x < reservado[0] and y < reservado[1]:
            y = reservado[1] + 2 * PT
        # La línea hasta la cuerda, desde el borde más cercano de la etiqueta.
        bx = min(max(px, x), x + tw)
        by = min(max(py, y), y + th)
        d.line([(bx, by), (px, py)], fill=(*TINTA, 178), width=max(1, round(0.6 * PT)))
        d.rounded_rectangle([x, y, x + tw, y + th], radius=1.5 * PT, fill=(255, 255, 255, 230))
        # Las letras, con el espaciado de 0,09 em de la ficha.
        cursor = x + 3 * PT
        for letra in texto:
            d.text((cursor, y + 1.2 * PT - caja[1]), letra, font=fuente, fill=(*TINTA, 255))
            cursor += d.textlength(letra, font=fuente) + 0.09 * 8 * PT
    return Image.alpha_composite(im, capa)


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("png")
    a.add_argument("--nombres", nargs="+", default=["firme", "chicote"])
    a.add_argument("--reservado", nargs=2, type=float, default=[0, 0])
    a.add_argument("--salida")
    args = a.parse_args()
    ruta = Path(args.png)
    anclas = json.loads(ruta.with_suffix(".anclas.json").read_text(encoding="utf-8"))
    im = Image.open(ruta)
    fondo = Image.new("RGBA", im.size, (255, 255, 255, 255))
    fondo.alpha_composite(im.convert("RGBA"))
    poner(fondo, anclas, args.nombres, args.reservado).convert("RGB").save(args.salida or ruta.with_name(ruta.stem + "-nombres.png"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
