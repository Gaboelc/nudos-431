"""T14b: arma los videos: fondo blanco, fundidos, títulos de los pasos y ffmpeg.

- El amarre (build/poc-video/amarre-h|v): cada cuadro dice hasta qué nodo llegó la mano
  (cuadros_amarre.py), y con eso, en qué paso de la ficha está.
- El as de guía (as-h|v-a y -b): en los fundidos se mezcla el cuadro del paso siguiente.
- El título de cada paso va abajo: el número en Big Shoulders Display y el texto de la ficha en
  Literata, las fuentes del visor (sitio/vendor/fuentes). Es el texto propio de la especificación.

Uso, con el venv del proyecto: python poc/video/armar.py [amarre|as] [h|v]
Deja build/poc-video/<nudo>-<h|v>.mp4.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from nudos.spec import cargar

RAIZ = Path(__file__).resolve().parents[2]
BASE = RAIZ / "build" / "poc-video"
FUENTES = RAIZ / "sitio" / "vendor" / "fuentes"
TINTA = (22, 32, 47)
# Dónde termina cada paso del amarre, en nodos de la cuerda (atar_amarre.py, hitos).
FIN_PASO_AMARRE = [240, 549, 1192, 1477, 2059, 2233, 2334]
FPS = 30


def titulo(im: Image.Image, n: int, texto: str) -> Image.Image:
    W, H = im.size
    esc = min(W, H) / 720
    d = ImageDraw.Draw(im, "RGBA")
    f_num = ImageFont.truetype(str(FUENTES / "big-shoulders-display-latin-800-normal.woff2"), round(54 * esc))
    f_txt = ImageFont.truetype(str(FUENTES / "literata-latin-600-normal.woff2"), round(28 * esc))
    margen = round(32 * esc)
    num = f"{n}"
    wn = d.textlength(num, font=f_num)
    y = H - margen - round(54 * esc)
    d.rounded_rectangle([margen - 14 * esc, y - 10 * esc, margen + wn + 18 * esc + d.textlength(texto, font=f_txt) + 14 * esc,
                         H - margen + 6 * esc], radius=10 * esc, fill=(255, 255, 255, 215))
    d.text((margen, y - 6 * esc), num, font=f_num, fill=TINTA)
    d.text((margen + wn + 18 * esc, y + 14 * esc), texto, font=f_txt, fill=TINTA)
    return im


def sobre_blanco(ruta: Path) -> Image.Image:
    im = Image.open(ruta).convert("RGBA")
    fondo = Image.new("RGBA", im.size, (255, 255, 255, 255))
    fondo.alpha_composite(im)
    return fondo.convert("RGB")


def ffmpeg(carpeta: Path, salida: Path, pausa_final: float) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-framerate", str(FPS),
                    "-i", str(carpeta / "f-%04d.png"),
                    "-vf", f"tpad=stop_mode=clone:stop_duration={pausa_final},format=yuv420p",
                    "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-movflags", "+faststart", str(salida)],
                   check=True)


def amarre(o: str) -> None:
    spec = cargar("amarre-cuadrado")
    origen = BASE / f"amarre-{o}"
    final = BASE / f"amarre-{o}-final"
    final.mkdir(exist_ok=True)
    cuadros = sorted(origen.glob("cuadro-*.png"))
    n = len(cuadros)
    Ks = np.unique(np.round(40 + (2334 - 40) * np.linspace(0, 1, n)).astype(int))
    for i, ruta in enumerate(cuadros):
        K = Ks[min(i, len(Ks) - 1)]
        paso = next(k for k, fin in enumerate(FIN_PASO_AMARRE, 1) if K <= fin)
        im = titulo(sobre_blanco(ruta), paso, spec.pasos[paso - 1].titulo)
        im.save(final / f"f-{i:04d}.png")
    ffmpeg(final, BASE / f"amarre-{o}.mp4", 2.5)


def as_de_guia(o: str) -> None:
    spec = cargar("as-de-guia")
    alfa = np.load(BASE / "as-pasos-alfa.npy")
    a, b = BASE / f"as-{o}-a", BASE / f"as-{o}-b"
    final = BASE / f"as-{o}-final"
    final.mkdir(exist_ok=True)
    titulos = [(p.n, p.titulo) for p in spec.pasos] + [(len(spec.pasos), "Apriétalo")]
    paso, cambio = 0, False
    for f in range(len(alfa)):
        im = sobre_blanco(a / f"cuadro-{f:04d}.png")
        if alfa[f] > 0:
            im = Image.blend(im, sobre_blanco(b / f"cuadro-{f:04d}.png"), float(alfa[f]))
            cambio = True
        elif cambio:
            paso, cambio = paso + 1, False
        n, t = titulos[min(paso, len(titulos) - 1)]
        titulo(im, n, t).save(final / f"f-{f:04d}.png")
    ffmpeg(final, BASE / f"as-de-guia-{o}.mp4", 1.0)


if __name__ == "__main__":
    nudo, o = sys.argv[1], sys.argv[2]
    {"amarre": amarre, "as": as_de_guia}[nudo](o)
    print("listo")
