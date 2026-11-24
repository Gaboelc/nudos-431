"""Prueba de concepto del motor (T14a): renderiza los trabajos y arma la página de prueba.

Cada imagen va como sale hoy, con la v2 de la plantilla (poc/cuerda-ajustada, solo el amarre)
y con el motor, a su tamaño impreso (58 × 64 mm), en color y en gris, todas dibujadas con la
misma escena de Blender (poc/blender/escena.py). Con Edge, build/poc-motor/prueba.pdf.

Uso, con el venv del proyecto, desde la raíz del repositorio:
    .venv/Scripts/python poc/motor/pagina.py [--sin-render]
"""
from __future__ import annotations

import argparse
import html
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image

from nudos import RAIZ

BASE = RAIZ / "build" / "poc-motor"
BLENDER = os.environ.get("NUDOS_BLENDER", "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe")
FILAS = [
    ("amarre-cuadrado", "paso-3", "Amarre cuadrado, paso 3: las vueltas"),
    ("amarre-cuadrado", "paso-5", "Amarre cuadrado, paso 5: los ahorcados"),
    ("amarre-cuadrado", "paso-7", "Amarre cuadrado, paso 7: el cierre"),
    ("amarre-cuadrado", "terminado-frente", "Amarre cuadrado, terminado"),
    ("as-de-guia", "terminado-frente", "As de guía, terminado"),
]


def renderizar(trabajo: Path, salida: Path) -> None:
    salida.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([BLENDER, "--background", "--factory-startup", "--python",
                    str(RAIZ / "poc" / "blender" / "escena.py"), "--", "--trabajo", str(trabajo),
                    "--salida", str(salida), "--muestras", "256"],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def sobre_blanco(origen: Path, destino: Path, gris: bool) -> None:
    im = Image.open(origen).convert("RGBA")
    fondo = Image.new("RGBA", im.size, (255, 255, 255, 255))
    fondo.alpha_composite(im)
    fondo.convert("L" if gris else "RGB").save(destino)


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--sin-render", action="store_true")
    args = a.parse_args()
    render = BASE / "render"
    if not args.sin_render:
        for t in sorted((BASE / "trabajos").glob("*.json")):
            print("renderizando", t.stem, flush=True)
            renderizar(t, render / f"{t.stem}.png")
    columnas = [("hoy", "Hoy", render), ("v2", "v2 de la plantilla", RAIZ / "build" / "poc-cuerda" / "render"),
                ("motor", "Motor", render)]
    pagina_dir = BASE / "pagina"
    pagina_dir.mkdir(parents=True, exist_ok=True)
    hojas = []
    for gris in (False, True):
        modo = "gris" if gris else "color"
        secciones = []
        for slug, nombre, titulo in FILAS:
            celdas = []
            for clave, pie, carpeta in columnas:
                if clave == "v2" and slug != "amarre-cuadrado":
                    continue
                origen = carpeta / (f"{clave}--{nombre}.png" if clave == "v2" else f"{slug}--{clave}--{nombre}.png")
                if not origen.exists():
                    continue
                destino = pagina_dir / f"{slug}--{clave}--{nombre}--{modo}.png"
                sobre_blanco(origen, destino, gris)
                celdas.append(f'<figure><img src="{destino.relative_to(BASE).as_posix()}"><figcaption>{html.escape(pie)}</figcaption></figure>')
            secciones.append(f"<section><h2>{html.escape(titulo)}</h2><div class=\"fila\">{''.join(celdas)}</div></section>")
        for k in range(0, len(secciones), 3):
            hojas.append(f'<div class="hoja"><h1>Motor de física, prueba de concepto, en {modo}</h1>{"".join(secciones[k:k + 3])}</div>')
    pagina = BASE / "prueba.html"
    pagina.write_text(f"""<!doctype html><html lang="es"><meta charset="utf-8"><title>Prueba del motor</title>
<style>
@page {{ size: 216mm 279mm; margin: 9mm; }}
body {{ font: 9pt system-ui, sans-serif; margin: 0; color: #222; }}
.hoja {{ page-break-after: always; }}
h1 {{ font-size: 11pt; margin: 0 0 2mm; }}
h2 {{ font-size: 9pt; margin: 2mm 0 1mm; }}
.fila {{ display: flex; gap: 4mm; }}
figure {{ margin: 0; }}
img {{ width: 58mm; height: 64mm; display: block; border: 0.2mm solid #ccc; }}
figcaption {{ font-size: 7.5pt; color: #555; }}
</style>{"".join(hojas)}</html>""", encoding="utf-8")
    edge = os.environ.get("NUDOS_CHROME", "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe")
    pdf = BASE / "prueba.pdf"
    subprocess.run([edge, "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={BASE / 'perfil-edge'}",
                    f"--print-to-pdf={pdf}", pagina.as_uri()], check=True, stdout=subprocess.DEVNULL,
                   stderr=subprocess.DEVNULL, timeout=120)
    print(pdf.relative_to(RAIZ))
    return 0


if __name__ == "__main__":
    sys.exit(main())
