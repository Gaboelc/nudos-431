"""Prueba de concepto del motor (T14a): los trabajos de imagen para Blender.

Cambia en el modelo de hoy la cuerda de cada paso por la que dio el motor y escribe el mismo
trabajo que recibe render/impresion.js (nudos/imprimir.py, trabajo()), para dibujarlo con
poc/blender/escena.py. En el amarre, cada paso es la cuerda asentada hasta su hito
(atar_amarre.py) más el resto del paso de hoy, que cae a la mesa, empalmado a la punta
asentada. En el as de guía, el terminado es el que asentó el motor (asentar_as.py).

Uso (en el entorno de la prueba, desde la raíz del repositorio):
    python poc/motor/exportar.py
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from atar_amarre import EMPALME, zonas_y_hitos   # noqa: E402

from nudos import RAIZ   # noqa: E402
from nudos.construir import construir   # noqa: E402
from nudos.imprimir import CELDA_MM, imagenes, px, trabajo   # noqa: E402
from nudos.spec import cargar   # noqa: E402

SALIDA = RAIZ / "build" / "poc-motor"
# El hito de cada paso del amarre cuadrado («vueltas» y «ahorcados» son los últimos).
HITO_DEL_PASO = {1: "inicio", 2: "vuelta-1", 3: "vuelta-3", 4: "ahorcado-1", 5: "ahorcado-3", 6: "cierre-1", 7: "cierre"}


def escribir(slug, img, nombre):
    t = trabajo(img) | {"ancho": px(CELDA_MM[0]), "alto": px(CELDA_MM[1]), "slug": slug, "nombre": nombre}
    (SALIDA / "trabajos").mkdir(parents=True, exist_ok=True)
    (SALIDA / "trabajos" / f"{slug}--{nombre}.json").write_text(json.dumps(t), encoding="utf-8")


def amarre():
    spec = cargar("amarre-cuadrado")
    modelo = construir(spec)
    X = modelo.pasos[-1].puntos
    _, hitos, _, _ = zonas_y_hitos(spec, len(spec.pasos), X)
    pasos = []
    for r in modelo.pasos:
        hito = HITO_DEL_PASO[r.n]
        ruta = SALIDA / f"amarre-{hito}.npy"
        if not ruta.exists():
            pasos.append(r)
            continue
        Y = np.load(ruta)
        K = hitos[hito]
        resto = r.puntos[K + 1:].copy()
        if len(resto):
            w = np.clip(1 - np.arange(1, len(resto) + 1) / EMPALME, 0, 1)[:, None]
            resto = resto + w * (Y[-1] - r.puntos[K])
            resto[:, 2] = np.maximum(resto[:, 2], 0.5)
        pasos.append(dataclasses.replace(r, puntos=np.vstack([Y, resto])))
    nuevo = dataclasses.replace(modelo, pasos=pasos)
    por_nombre = {i.nombre: i for i in imagenes(nuevo)}
    for n in ("paso-3", "paso-5", "paso-7", "terminado-frente"):
        escribir("amarre-cuadrado", por_nombre[n], f"motor--{n}")
    por_hoy = {i.nombre: i for i in imagenes(modelo)}
    for n in ("paso-3", "paso-5", "paso-7", "terminado-frente"):
        escribir("amarre-cuadrado", por_hoy[n], f"hoy--{n}")


def as_de_guia():
    modelo = construir(cargar("as-de-guia"))
    ruta = SALIDA / "as-de-guia-terminado.npy"
    por_hoy = {i.nombre: i for i in imagenes(modelo)}
    escribir("as-de-guia", por_hoy["terminado-frente"], "hoy--terminado-frente")
    if ruta.exists():
        Y = np.load(ruta)
        base = modelo.apretado or modelo.pasos[-1]
        nuevo = dataclasses.replace(modelo, apretado=dataclasses.replace(base, puntos=Y, resaltado=None))
        img = {i.nombre: i for i in imagenes(nuevo)}["terminado-frente"]
        escribir("as-de-guia", img, "motor--terminado-frente")


if __name__ == "__main__":
    amarre()
    as_de_guia()
    print("trabajos en build/poc-motor/trabajos/")
