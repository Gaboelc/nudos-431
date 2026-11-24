"""Prueba de concepto de la fase 6 (T14): los trabajos de imagen para Blender.

Construye los nudos de la prueba y escribe, por cada imagen de impresión elegida, el mismo
trabajo que hoy recibe render/impresion.js (nudos/imprimir.py, trabajo()), más su tamaño en
px. Así Blender dibuja exactamente lo mismo que three.js: los mismos puntos, el mismo
resaltado, el mismo anfitrión y la misma vista.

Uso, desde la raíz del repositorio:
    .venv/Scripts/python poc/blender/exportar.py
Deja los trabajos en build/poc-blender/trabajos/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from nudos import RAIZ
from nudos.construir import construir
from nudos.imprimir import CELDA_MM, imagenes, px, trabajo
from nudos.spec import cargar

SALIDA = RAIZ / "build" / "poc-blender"
# Las imágenes de la página de prueba: las mismas de la página de T7b, más el terminado del
# amarre, que es donde más se nota la cuerda tiesa.
PRUEBA = {
    "as-de-guia": ["paso-7", "terminado-frente"],
    "ballestrinque": ["error-correcto", "error"],
    "amarre-cuadrado": ["paso-5", "terminado-frente"],
}


def main() -> int:
    carpeta = SALIDA / "trabajos"
    carpeta.mkdir(parents=True, exist_ok=True)
    ancho, alto = px(CELDA_MM[0]), px(CELDA_MM[1])
    for slug, nombres in PRUEBA.items():
        modelo = construir(cargar(slug))
        if modelo.fallas:
            print(f"{slug}: tiene fallas", file=sys.stderr)
            return 1
        por_nombre = {img.nombre: img for img in imagenes(modelo)}
        for nombre in nombres:
            t = trabajo(por_nombre[nombre]) | {"ancho": ancho, "alto": alto, "slug": slug,
                                                "nombre": nombre}
            ruta = carpeta / f"{slug}--{nombre}.json"
            ruta.write_text(json.dumps(t), encoding="utf-8")
            print(ruta.relative_to(RAIZ))
    # El video: el amarre cuadrado entero, la cuerda de su último paso.
    modelo = construir(cargar("amarre-cuadrado"))
    ultima = next(i for i in imagenes(modelo) if i.nombre == f"paso-{modelo.pasos[-1].n}")
    t = trabajo(ultima) | {"ancho": 1280, "alto": 720, "slug": "amarre-cuadrado",
                           "nombre": "video", "resaltar": False}
    (carpeta / "amarre-cuadrado--video.json").write_text(json.dumps(t), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
