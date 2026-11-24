"""T14b: los cuadros del video del as de guía, con el motor (poc/motor).

Los pasos de la ficha (nudos/libre.py) se dibujan con el chicote de distinto largo, porque la
ficha muestra solo lo que entra en el encuadre. Para el video la cuerda mide siempre lo mismo:
el chicote de cada paso se alarga en recto, fuera del encuadre, hasta el largo del último. Así
cada nodo es el mismo punto de la cuerda en todos los pasos.

Entre un paso y el siguiente, los nodos que cambian de lugar se atraen hacia el paso nuevo con
resortes que se endurecen de a poco (Motor.objetivos), y el motor mueve la cuerda sin que se
atraviese: cada cuadro parte del anterior. Después se sueltan los resortes y la cuerda se
asienta. Al final de cada pasaje se compara la secuencia con la de la ficha.

Uso (en el entorno de la prueba, desde la raíz del repositorio):
    python poc/video/cuadros_as.py [--fps 30]
Deja build/poc-video/as-de-guia-cuadros.npz.
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "motor"))
from motor import Escena, Material, Motor   # noqa: E402
from pruebas import secuencia   # noqa: E402

from nudos.construir import construir   # noqa: E402
from nudos.spec import cargar   # noqa: E402

SALIDA = Path(__file__).resolve().parents[2] / "build" / "poc-video"


ALTO_MANO = 3.5   # la cuerda que sobra va en el aire, a esta altura del eje, sobre todo lo de la mesa


def alargar(P: np.ndarray, n: int, h: float) -> np.ndarray:
    """P con el chicote alargado hasta n nodos como lo sostiene una mano: sigue recto 1,5
    diámetros en la dirección en que venía (sin quiebre), sube hasta ALTO_MANO en un cuarto de
    vuelta y sigue en el aire en esa dirección. Así no pasa por ninguna cuerda de la mesa. Si P
    tiene más de n nodos, se recorta."""
    if len(P) >= n:
        return P[:n].copy()
    d = P[-1] - P[-3]
    d[2] = 0.0
    d = d / np.linalg.norm(d)
    pts = [P[-1] + k * h * d for k in range(1, int(1.5 / h) + 1)]
    base = pts[-1]
    r = ALTO_MANO - base[2]
    for a in np.arange(h / r, math.pi / 2, h / r):
        pts.append(base + r * math.sin(a) * d + np.array([0, 0, r * (1 - math.cos(a))]))
    tope = base + r * d + np.array([0, 0, r])
    k = 1
    while len(P) + len(pts) < n:
        pts.append(tope + k * h * d)
        k += 1
    return np.vstack([P, np.array(pts[:n - len(P)])])


def distancia_minima(Y, k=8):
    d = np.linalg.norm(Y[:, None] - Y[None], axis=2)
    i, j = np.triu_indices(len(Y), k + 1)
    return float(d[i, j].min())


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--fps", type=int, default=30)
    a.add_argument("--pasaje", type=float, default=2.0, help="segundos de cada pasaje")
    a.add_argument("--quieto", type=float, default=0.5, help="segundos que se asienta cada paso")
    args = a.parse_args()
    SALIDA.mkdir(parents=True, exist_ok=True)
    modelo = construir(cargar("as-de-guia"))
    h = modelo.pasos[-1].h
    n = max(len(r.puntos) for r in modelo.pasos)
    pasos = [alargar(r.puntos, n, h) for r in modelo.pasos]
    for k, P in enumerate(pasos, 1):
        print(f"paso {k}: distancia mínima {distancia_minima(P):.3f}; secuencia {' '.join(secuencia(P[:len(modelo.pasos[k - 1].puntos)])) or 'sin cruces'} "
              f"(ficha: {' '.join(modelo.pasos[k - 1].secuencia) or 'sin cruces'})", flush=True)
    mat = Material()
    cuadros, marcas = [], []
    t0 = time.time()
    Y = pasos[0]
    m = Motor(Escena(Y, mat, [], mesa=0.0, fijos=np.arange(3), proximal=0.5, vecinos=2.0))
    m.objetivos = {n - 1: (Y[-1].copy(), 500.0)}
    Y = m.resolver(pasos=30, kappa=0.3, quieto=5e-4, mostrar=False)
    cuadros += [Y.copy()] * round(args.quieto * args.fps)
    marcas.append(len(cuadros) - 1)
    for k in range(1, len(pasos)):
        B = pasos[k]
        mueve = np.flatnonzero(np.linalg.norm(B - Y, axis=1) > 0.3)
        m = Motor(Escena(Y, mat, [], mesa=0.0, fijos=np.arange(3), proximal=0.5, vecinos=2.0))
        F = round(args.pasaje * args.fps)
        mano0 = Y[-1].copy()
        for f in range(1, F + 1):
            x = f / F
            suave = x * x * (3 - 2 * x)
            rig = 40.0 * x ** 2
            m.objetivos = {int(i): (B[i], rig) for i in mueve}
            m.objetivos[n - 1] = (mano0 + suave * (B[-1] - mano0), 500.0)   # la mano
            Y = m.resolver(x0=Y, pasos=3, kappa=0.3, quieto=1e-4, mostrar=False)
            cuadros.append(Y.copy())
        m.objetivos = {n - 1: (B[-1], 500.0)}
        for f in range(round(args.quieto * args.fps)):
            Y = m.resolver(x0=Y, pasos=2, kappa=0.3, quieto=1e-4, mostrar=False)
            cuadros.append(Y.copy())
        marcas.append(len(cuadros) - 1)
        lejos = float(np.linalg.norm(Y[mueve] - B[mueve], axis=1).max()) if len(mueve) else 0.0
        nk = len(modelo.pasos[k].puntos)   # la secuencia, solo con la cuerda de la ficha
        obt, dec = " ".join(secuencia(Y[:nk])), " ".join(modelo.pasos[k].secuencia)
        print(f"pasaje {k}→{k + 1}: {len(mueve)} nodos se mueven; queda a {lejos:.2f} d del paso; "
              f"secuencia {'igual' if obt == dec else 'DISTINTA: ' + obt}; {time.time() - t0:.0f} s", flush=True)
    cuadros += [Y.copy()] * round(1.5 * args.fps)
    np.savez_compressed(SALIDA / "as-de-guia-cuadros.npz", marcas=np.array(marcas),
                        **{f"c{k:04d}": c for k, c in enumerate(cuadros)})
    print(f"{len(cuadros)} cuadros en {time.time() - t0:.0f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
