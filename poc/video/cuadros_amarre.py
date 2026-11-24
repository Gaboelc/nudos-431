"""T14b: los cuadros del video del amarre cuadrado, con el motor (poc/motor).

La mano lleva la punta de la cuerda por el camino de la plantilla, a velocidad pareja. En cada
cuadro, la cuerda hasta donde llegó la mano se asienta con el motor y la tensión de atado de
T14a (60 N en el ballestrinque y las vueltas, 150 N en los ahorcados), con el chicote corto y la
punta que sostiene la mano fijos. Así la cuerda se va dando y, cuando llegan los ahorcados, las
vueltas se juntan. El último cuadro es el amarre terminado de la ficha (atar_amarre.py --atado).

Cada cuadro parte de la plantilla, que nunca se atraviesa, y el motor no deja que la cuerda se
atraviese al asentarla. Como los cuadros no dependen uno del otro, se calculan a la vez en
varios procesos.

Uso (en el entorno de la prueba, desde la raíz del repositorio):
    python poc/video/cuadros_amarre.py [--segundos 9] [--fps 30] [--procesos 8]
Deja build/poc-video/amarre-cuadros.npz.
"""
from __future__ import annotations

import argparse
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "motor"))

SALIDA = Path(__file__).resolve().parents[2] / "build" / "poc-video"
_X = _HITOS = _SOLIDOS = None


def _preparar():
    global _X, _HITOS, _SOLIDOS
    from atar_amarre import zonas_y_hitos
    from motor import cilindro
    from nudos.construir import construir
    from nudos.spec import cargar
    spec = cargar("amarre-cuadrado")
    modelo = construir(spec)
    _X = modelo.pasos[-1].puntos
    _, _HITOS, g, _ = zonas_y_hitos(spec, len(spec.pasos), _X)
    cruz = g.solido
    _SOLIDOS = [cilindro((0, 0, cruz.zb), "y", cruz.radio - 0.56, 40.0),
                cilindro((0, 0, cruz.zt), "x", cruz.radio - 0.56, 40.0)]


def cuadro(K: int) -> np.ndarray:
    """La cuerda de la plantilla hasta el nodo K, asentada."""
    from motor import Escena, Material, Motor
    if _X is None:
        _preparar()
    Y = _X[:K + 1].copy()
    i = np.arange(K)
    fin_v, fin_a = _HITOS["vuelta-3"], _HITOS["ahorcado-3"]
    atado = np.where((i >= fin_v) & (i < fin_a), 150.0, 60.0)
    fijos = np.r_[np.arange(3), np.arange(max(3, K - 2), K + 1)]
    e = Escena(Y, Material(), _SOLIDOS, mesa=0.0, fijos=fijos, proximal=0.5, tension_atado=atado)
    m = Motor(e)
    return m.resolver(pasos=60, kappa=0.3, quieto=5e-4, mostrar=False)


def main() -> int:
    a = argparse.ArgumentParser()
    a.add_argument("--segundos", type=float, default=9.0, help="lo que tarda la mano en dar toda la cuerda")
    a.add_argument("--fps", type=int, default=30)
    a.add_argument("--procesos", type=int, default=8)
    args = a.parse_args()
    SALIDA.mkdir(parents=True, exist_ok=True)
    _preparar()
    n = round(args.segundos * args.fps)
    K0, K1 = 40, len(_X) - 1
    Ks = np.unique(np.round(K0 + (K1 - K0) * np.linspace(0, 1, n) ** 1.0).astype(int))
    print(f"{len(Ks)} cuadros, de {K0} a {K1} nodos, con {args.procesos} procesos", flush=True)
    t0 = time.time()
    with ProcessPoolExecutor(args.procesos, initializer=_preparar) as ex:
        cuadros = list(ex.map(cuadro, Ks, chunksize=2))
    print(f"listo en {time.time() - t0:.0f} s", flush=True)
    np.savez_compressed(SALIDA / "amarre-cuadros.npz", **{f"c{k:04d}": c for k, c in enumerate(cuadros)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
