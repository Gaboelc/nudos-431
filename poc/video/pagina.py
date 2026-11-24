"""T14b: la página de prueba del render y del video con el motor.

Cada imagen de ficha va como sale hoy (three.js, build/<slug>/impresion) y como sale con
Blender y el motor, con los nombres puestos por poc/video/nombres.py, a su tamaño impreso
(58 × 64 mm), en color y en gris. La última hoja tiene cuadros de los cuatro videos; los
videos van aparte, en build/poc-video/*.mp4. Con Edge, build/poc-video/prueba.pdf.

Antes: las imágenes de build/poc-video/fichas (escena.py + nombres.py) y los videos
(armar.py). Uso, con el venv del proyecto: python poc/video/pagina.py
"""
from __future__ import annotations

import html
import os
import subprocess
import sys

from PIL import Image

from nudos import RAIZ

BASE = RAIZ / "build" / "poc-video"
FILAS = [
    ("amarre-cuadrado", "paso-3", "Amarre cuadrado, paso 3: las vueltas"),
    ("amarre-cuadrado", "paso-5", "Amarre cuadrado, paso 5: los ahorcados"),
    ("amarre-cuadrado", "paso-7", "Amarre cuadrado, paso 7: el cierre"),
    ("amarre-cuadrado", "terminado-frente", "Amarre cuadrado, terminado"),
    ("as-de-guia", "terminado-frente", "As de guía, terminado"),
]
VIDEOS = [("hoja-amarre-h.png", "Amarre, horizontal (un cuadro por segundo)"),
          ("hoja-as-h.png", "As de guía, horizontal (un cuadro cada 1,3 s)"),
          ("hoja-amarre-v.png", "Amarre, vertical"),
          ("hoja-as-v.png", "As de guía, vertical")]


def guardar(origen, destino, gris: bool) -> None:
    im = Image.open(origen).convert("RGBA")
    fondo = Image.new("RGBA", im.size, (255, 255, 255, 255))
    fondo.alpha_composite(im)
    fondo.convert("L" if gris else "RGB").save(destino)


def main() -> int:
    carpeta = BASE / "pagina"
    carpeta.mkdir(parents=True, exist_ok=True)
    hojas = []
    for gris in (False, True):
        modo = "gris" if gris else "color"
        secciones = []
        for slug, nombre, titulo in FILAS:
            celdas = []
            for clave, pie, origen in [
                ("hoy", "Hoy (three.js)", RAIZ / "build" / slug / "impresion" / f"{nombre}.png"),
                ("blender", "Blender con el motor", BASE / "fichas" / f"{slug}--motor--{nombre}-nombres.png"),
            ]:
                if not origen.exists():
                    continue
                destino = carpeta / f"{slug}--{clave}--{nombre}--{modo}.png"
                guardar(origen, destino, gris)
                celdas.append(f'<figure><img class="ficha" src="{destino.relative_to(BASE).as_posix()}">'
                              f'<figcaption>{html.escape(pie)}</figcaption></figure>')
            secciones.append(f'<section><h2>{html.escape(titulo)}</h2><div class="fila">{"".join(celdas)}</div></section>')
        for k in range(0, len(secciones), 3):
            hojas.append(f'<div class="hoja"><h1>Render y video con el motor, prueba de concepto, en {modo}</h1>'
                         f'{"".join(secciones[k:k + 3])}</div>')
    cuadros = [f'<figure><img class="video" src="{v}"><figcaption>{html.escape(t)}</figcaption></figure>'
               for v, t in VIDEOS if (BASE / v).exists()]
    hojas.append(f'<div class="hoja"><h1>Cuadros de los videos</h1>{"".join(cuadros)}</div>')
    pagina = BASE / "prueba.html"
    pagina.write_text(f"""<!doctype html><html lang="es"><meta charset="utf-8"><title>Render y video</title>
<style>
@page {{ size: 216mm 279mm; margin: 9mm; }}
body {{ font: 9pt system-ui, sans-serif; margin: 0; color: #222; }}
.hoja {{ page-break-after: always; }}
h1 {{ font-size: 11pt; margin: 0 0 2mm; }}
h2 {{ font-size: 9pt; margin: 2mm 0 1mm; }}
.fila {{ display: flex; gap: 6mm; }}
figure {{ margin: 0 0 3mm; }}
img.ficha {{ width: 58mm; height: 64mm; display: block; border: 0.2mm solid #ccc; }}
img.video {{ width: 100%; display: block; border: 0.2mm solid #ccc; }}
figcaption {{ font-size: 7.5pt; color: #555; }}
</style>{"".join(hojas)}</html>""", encoding="utf-8")
    edge = os.environ.get("NUDOS_CHROME", "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
    pdf = BASE / "prueba.pdf"
    subprocess.run([edge, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={RAIZ / 'build' / 'poc-motor' / 'perfil-edge'}",
                    f"--print-to-pdf={pdf}", pagina.as_uri()], check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=120)
    print(pdf.relative_to(RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
