"""Prueba de concepto del motor (T14a): el as de guía terminado, asentado.

Para asentar un as de guía se sostiene el firme y se tira de la gaza, y el chicote se acomoda
con un tirón más suave. Así el motor: la punta del firme fija, la gaza tirada hacia abajo
(desde su punto más bajo) con T newtons y el chicote con T/3, hacia donde sigue. Parte del
último paso de hoy (relajado por nudos/libre.py) y se comprueba como hoy (_resultado: la
secuencia vista desde arriba, la separación, la curvatura y el estiramiento).

Uso (en el entorno de la prueba, desde la raíz del repositorio):
    python poc/motor/asentar_as.py [--tension 60]
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from motor import Escena, Material, Motor   # noqa: E402

from nudos import RAIZ   # noqa: E402
from nudos.construir import construir   # noqa: E402
from nudos.libre import _resultado   # noqa: E402
from nudos.spec import cargar   # noqa: E402

SALIDA = RAIZ / "build" / "poc-motor"


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--tension", type=float, default=60.0)
    args = a.parse_args()
    SALIDA.mkdir(parents=True, exist_ok=True)
    modelo = construir(cargar("as-de-guia"))
    r = modelo.pasos[-1]
    X, h = r.puntos, r.h
    n = len(X)
    # El punto más bajo de la gaza: el de menor y en la mitad de la cuerda.
    medio = np.arange(n // 4, 3 * n // 4)
    gaza = int(medio[np.argmin(X[medio, 1])])
    chicote = X[-1] - X[-6]
    chicote /= np.linalg.norm(chicote)
    T = args.tension
    e = Escena(X, Material(), [], mesa=0.0, fijos=np.arange(3),
               fuerzas={gaza: np.array([0, -T, 0]), n - 1: (T / 3) * chicote})
    m = Motor(e)
    t0 = time.time()
    Y = m.resolver(pasos=150, quieto=5e-4)
    res = _resultado(r.n, Y, h, r.secuencia, None)
    print(f"as de guía: {n} nodos, {len(m.registro)} pasos, {time.time() - t0:.0f} s")
    print(f"  largo {r.medidas['largo']:.1f} → {res.medidas['largo']:.1f}; separación {res.medidas['separacion_min']:.3f}; "
          f"curvatura {res.medidas['curvatura_min']:.3f}; estiramiento {res.medidas['estiramiento_max']:.4f}")
    print(f"  fallas: {res.fallas or 'ninguna'}")
    np.save(SALIDA / "as-de-guia-terminado.npy", Y)
    return 0


if __name__ == "__main__":
    sys.exit(main())
