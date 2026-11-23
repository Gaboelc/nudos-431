"""Prueba de concepto de T15: un amarre menos tieso cambiando las medidas de su plantilla.

nudos/plantillas/amarre.py traza la cuerda con unas medidas fijas (PASO_VUELTAS, ESCALON,
ABRIR, LIBRE, CARRIL, RADIO_ESQUINA…). Aquí se cambian para esta corrida, se construye el
amarre cuadrado entero (pasos, error y comprobaciones de siempre) y, si no tiene fallas, se
dejan los trabajos de sus imágenes para Blender.

Uso, desde la raíz del repositorio:
    .venv/Scripts/python poc/cuerda/plantilla.py --nombre ajustada RADIO_ESQUINA=2.4 ESCALON=0.5 ...
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import nudos.plantillas.amarre as amarre
from nudos import RAIZ
from nudos.construir import construir
from nudos.imprimir import CELDA_MM, imagenes, px, trabajo
from nudos.spec import cargar

SALIDA = RAIZ / "build" / "poc-cuerda"
IMAGENES = ("paso-3", "paso-5", "paso-7", "terminado-frente")


def cintura(k: float) -> None:
    """Cada esquina de una vuelta, a media altura, se mete k diámetros hacia el eje del cruce
    (x = y = 0), como cuando los ahorcados la aprietan. Los extremos, sobre los palos, no se
    mueven. Es el mismo lugar donde la plantilla ya aparta las esquinas vecinas (`abre`)."""
    import math

    import numpy as np

    def curva(self):
        P0, P1 = np.asarray(self.P0, float), np.asarray(self.P1, float)
        largo = float(np.linalg.norm(P1 - P0))
        u = np.linspace(0, 1, max(8, int(1.3 * largo / amarre.PASO)))[:, None]
        C = amarre._hermite(P0, P1, self.t0, self.t1, self.abre)
        medio = 0.5 * (P0 + P1)
        hacia = -np.array([medio[0], medio[1], 0.0])
        n = np.linalg.norm(hacia)
        if n > 1e-9:
            C = C + np.sin(math.pi * np.linspace(0, 1, len(C)))[:, None] ** 2 * (k / n) * hacia
        return C

    amarre._Esquina.curva = curva


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--slug", default="amarre-cuadrado")
    a.add_argument("--nombre", required=True)
    a.add_argument("medidas", nargs="*", help="NOMBRE=valor de nudos/plantillas/amarre.py")
    args = a.parse_args()
    for m in args.medidas:
        clave, valor = m.split("=")
        if clave == "CINTURA":
            cintura(float(valor))
            print(f"CINTURA: 0 → {valor}")
            continue
        print(f"{clave}: {getattr(amarre, clave)} → {valor}")
        setattr(amarre, clave, float(valor))
    inicio = time.time()
    try:
        modelo = construir(cargar(args.slug))
    except Exception as e:   # la plantilla misma no pudo trazar la cuerda
        print(f"No se pudo construir: {e}")
        return 1
    print(f"{time.time() - inicio:.0f} s")
    for f in modelo.fallas[:12]:
        print("  falla:", f[:170])
    if modelo.fallas:
        return 1
    ultimo = modelo.pasos[-1]
    print(f"Sin fallas. Largo del último paso: {ultimo.medidas['largo']:.1f}; separación "
          f"{ultimo.medidas['separacion_min']:.3f}; curvatura {ultimo.medidas['curvatura_min']:.3f}")
    (SALIDA / "trabajos").mkdir(parents=True, exist_ok=True)
    por_nombre = {i.nombre: i for i in imagenes(modelo)}
    for n in IMAGENES:
        if n in por_nombre:
            t = trabajo(por_nombre[n]) | {"ancho": px(CELDA_MM[0]), "alto": px(CELDA_MM[1]),
                                           "slug": args.slug, "nombre": f"{args.nombre}--{n}"}
            (SALIDA / "trabajos" / f"{args.slug}--{args.nombre}--{n}.json").write_text(json.dumps(t), encoding="utf-8")
    print("trabajos en build/poc-cuerda/trabajos/")
    # Las mismas imágenes con el render de hoy (three.js con Edge), para la ficha de hoy.
    from nudos.imprimir import dibujar
    destino = SALIDA / "threejs" / args.nombre
    destino.mkdir(parents=True, exist_ok=True)
    dibujar([por_nombre[n] for n in IMAGENES if n in por_nombre], destino)
    print(f"three.js en {destino.relative_to(RAIZ)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
