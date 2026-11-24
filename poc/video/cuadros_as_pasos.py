"""T14b: los cuadros del video del as de guía, paso por paso.

Animar el atado de un nudo libre pide planear la mano: para que el chicote pase por debajo de
un tramo hay que levantarlo o meterlo por debajo, y un camino recto hacia el paso siguiente
deja la cuerda encima y forma el cruce al revés (ver LEEME.md). Eso es T17. Mientras tanto,
el video muestra cada paso de la ficha asentado con el motor (el firme fijo, la cuerda sobre
la mesa con su peso y su roce), unos segundos cada uno, con un fundido al siguiente, y al final
el terminado apretado (build/poc-motor/as-de-guia-terminado.npy, de asentar_as.py
--desde-apretado). La cámara gira despacio durante todo el video.

Deja build/poc-video/as-pasos-a.npz (la cuerda de cada cuadro), as-pasos-b.npz (en los
fundidos, la del paso siguiente) y as-pasos-alfa.npy (cuánto del siguiente en cada cuadro).

Uso (en el entorno de la prueba): python poc/video/cuadros_as_pasos.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "motor"))
from motor import Escena, Material, Motor   # noqa: E402
from pruebas import secuencia   # noqa: E402

from nudos.construir import construir   # noqa: E402
from nudos.spec import cargar   # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "build" / "poc-video"
QUIETO, FUNDIDO, FINAL = 40, 14, 60


def main() -> int:
    modelo = construir(cargar("as-de-guia"))
    pasos = []
    for r in modelo.pasos:
        m = Motor(Escena(r.puntos, Material(), [], mesa=0.0, fijos=np.arange(3), proximal=0.5, vecinos=2.0))
        Y = m.resolver(pasos=40, kappa=0.3, quieto=5e-4, mostrar=False)
        ok = " ".join(secuencia(Y)) == " ".join(r.secuencia)
        print(f"paso {r.n}: {len(m.registro)} pasos del motor; secuencia {'igual' if ok else 'DISTINTA'}", flush=True)
        pasos.append(Y)
    pasos.append(np.load(RAIZ / "build" / "poc-motor" / "as-de-guia-terminado.npy"))
    a, b, alfa = {}, {}, []
    f = 0
    for k, Y in enumerate(pasos):
        quieto = FINAL if k == len(pasos) - 1 else QUIETO
        for _ in range(quieto):
            a[f"c{f:04d}"] = Y
            alfa.append(0.0)
            f += 1
        if k < len(pasos) - 1:
            for i in range(FUNDIDO):
                a[f"c{f:04d}"] = Y
                b[f"c{f:04d}"] = pasos[k + 1]
                x = (i + 1) / (FUNDIDO + 1)
                alfa.append(x * x * (3 - 2 * x))
                f += 1
    np.savez_compressed(SALIDA / "as-pasos-a.npz", **a)
    np.savez_compressed(SALIDA / "as-pasos-b.npz", **b)
    np.save(SALIDA / "as-pasos-alfa.npy", np.array(alfa))
    print(f"{f} cuadros, {len(b)} de fundido")
    return 0


if __name__ == "__main__":
    sys.exit(main())
