"""Prueba de concepto de la fase 6: la página de prueba, hoy y en Blender, en color y en gris.

Pone cada imagen de la prueba como sale hoy (build/<slug>/impresion/) junto a la de Blender
(build/poc-blender/render/), a su tamaño impreso (58 × 64 mm), y el amarre apretado de T15
junto al de hoy. Con Edge la convierte en build/poc-blender/prueba.pdf, como la de T7b.

Uso, desde la raíz del repositorio y después de renderizar:
    .venv/Scripts/python poc/blender/pagina.py
"""
from __future__ import annotations

import html
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image

from nudos import RAIZ

BASE = RAIZ / "build" / "poc-blender"
PARES = [
    ("as-de-guia", "paso-7", "As de guía, paso 7"),
    ("as-de-guia", "terminado-frente", "As de guía, terminado"),
    ("ballestrinque", "error-correcto", "Ballestrinque, paso 5 bien"),
    ("ballestrinque", "error", "Ballestrinque, el error"),
    ("amarre-cuadrado", "paso-5", "Amarre cuadrado, paso 5"),
    ("amarre-cuadrado", "terminado-frente", "Amarre cuadrado, terminado"),
]
APRETADO = ("amarre-cuadrado", "terminado-apretado", "Amarre cuadrado, terminado apretado (T15)")


def sobre_blanco(origen: Path, destino: Path, gris: bool) -> None:
    im = Image.open(origen).convert("RGBA")
    fondo = Image.new("RGBA", im.size, (255, 255, 255, 255))
    fondo.alpha_composite(im)
    out = fondo.convert("L" if gris else "RGB")
    out.save(destino)


def celda(ruta: Path, pie: str) -> str:
    return (f'<figure><img src="{ruta.relative_to(BASE).as_posix()}">'
            f"<figcaption>{html.escape(pie)}</figcaption></figure>")


def main() -> int:
    carpeta = BASE / "pagina"
    carpeta.mkdir(parents=True, exist_ok=True)
    hojas = []
    for gris in (False, True):
        filas = []
        modo = "gris" if gris else "color"
        lista = PARES + ([APRETADO] if (BASE / "render" / f"{APRETADO[0]}--{APRETADO[1]}.png").exists() else [])
        for slug, nombre, titulo in lista:
            if nombre == "terminado-apretado":
                hoy = BASE / "render" / f"{slug}--terminado-frente.png"
                izq = "Blender, como hoy"
                der = "Blender, apretado"
            else:
                hoy = RAIZ / "build" / slug / "impresion" / f"{nombre}.png"
                izq, der = "Hoy (three.js)", "Blender"
            nuevo = BASE / "render" / f"{slug}--{nombre}.png"
            a, b = carpeta / f"{slug}--{nombre}--hoy-{modo}.png", carpeta / f"{slug}--{nombre}--blender-{modo}.png"
            sobre_blanco(hoy, a, gris)
            sobre_blanco(nuevo, b, gris)
            filas.append(f'<section><h2>{html.escape(titulo)}</h2><div class="par">'
                         f"{celda(a, izq)}{celda(b, der)}</div></section>")
        for k in range(0, len(filas), 3):
            hojas.append(f'<div class="hoja"><h1>Prueba de Blender, en {modo}</h1>{"".join(filas[k:k + 3])}</div>')
    pagina = BASE / "prueba.html"
    pagina.write_text(f"""<!doctype html><html lang="es"><meta charset="utf-8">
<title>Prueba de Blender</title>
<style>
@page {{ size: 216mm 279mm; margin: 10mm; }}
body {{ font: 9pt system-ui, sans-serif; margin: 0; color: #222; }}
.hoja {{ page-break-after: always; }}
h1 {{ font-size: 11pt; margin: 0 0 3mm; }}
h2 {{ font-size: 9pt; margin: 2mm 0 1mm; }}
.par {{ display: flex; gap: 6mm; }}
figure {{ margin: 0; }}
img {{ width: 58mm; height: 64mm; display: block; border: 0.2mm solid #ccc; }}
figcaption {{ font-size: 7.5pt; color: #555; }}
</style>
{"".join(hojas)}
</html>""", encoding="utf-8")
    navegador = os.environ.get("NUDOS_CHROME", "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
    pdf = BASE / "prueba.pdf"
    perfil = BASE / "perfil-edge"
    subprocess.run([navegador, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--user-data-dir={perfil}",
                    f"--print-to-pdf={pdf}", pagina.as_uri()], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    print(pdf.relative_to(RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
