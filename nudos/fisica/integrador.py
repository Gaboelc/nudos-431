"""El integrador del motor (T15): Newton con búsqueda en línea.

T15b deja el Newton mínimo con el que se resuelven la catenaria y la elástica: minimiza una
energía con algunos grados de libertad fijos (las manos que sostienen). T15d le suma la barrera
y el roce de `contacto.py` y recorta cada paso con la CCD (`paso_maximo`).

Todo va en `float64` y en un orden fijo: resolver dos veces da lo mismo bit a bit.
"""
from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Callable

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla


_REDONDEO = 1e-13


@dataclass
class Resultado:
    x: np.ndarray            # la solución, con la forma de x0
    iteraciones: int
    fuerza: float            # la mayor componente del gradiente en los grados de libertad libres (N)
    convergio: bool


def newton(evaluar: Callable, x0, fijos=None, tol_fuerza: float = 1e-9, max_iter: int = 200,
           paso_maximo: Callable | None = None) -> Resultado:
    """Minimiza la energía de `evaluar` desde x0.

    `evaluar(x, orden, proyectar)` da la energía con `orden=0` y (energía, gradiente, Hessiano
    disperso) con `orden=2`, todo sobre x aplanado (3N,); con `proyectar`, el Hessiano viene
    semidefinido positivo. `fijos` son los nodos que no se mueven. `paso_maximo(x, p)`, si está,
    da la fracción de 0 a 1 del paso p que se puede dar (la CCD de T15d). Termina cuando ninguna
    componente del gradiente libre pasa `tol_fuerza`.

    Cada iteración prueba primero el Hessiano exacto, y el proyectado solo si el exacto no da
    una dirección en que la energía baje. Proyectar siempre la flexión, bloque por bloque, deja
    a Newton casi lineal: el voladizo de 25 diámetros no llegaba en 300 iteraciones, y con el
    exacto llega en 35 (T15b).
    """
    forma = np.shape(x0)
    x = np.asarray(x0, float).ravel().copy()
    libre = np.ones(len(x), bool)
    if fijos is not None:
        nodos = np.asarray(fijos, int)
        libre[(3 * nodos[:, None] + np.arange(3)).ravel()] = False
    dof = np.flatnonzero(libre)
    fuerza = math.inf
    for it in range(max_iter):
        E, g, H = evaluar(x, 2, False)
        gl = g[dof]
        fuerza = float(np.max(np.abs(gl))) if len(gl) else 0.0
        if fuerza < tol_fuerza:
            return Resultado(x.reshape(forma), it, fuerza, True)
        p = np.zeros_like(x)
        p[dof] = _resolver(H[dof][:, dof].tocsc(), -gl)
        pendiente = float(gl @ p[dof])
        if not pendiente < 0:          # el exacto no baja: el proyectado
            H = evaluar(x, 2, True)[2]
            p[dof] = _resolver(H[dof][:, dof].tocsc(), -gl)
            pendiente = float(gl @ p[dof])
        if not pendiente < 0:          # tampoco (un modo sin rigidez): el gradiente
            p[dof] = -gl
            pendiente = -float(gl @ gl)
        alfa = 1.0 if paso_maximo is None else min(1.0, paso_maximo(x, p))
        while alfa > 1e-12:
            En = evaluar(x + alfa * p, 0)
            # Cerca del mínimo, la energía baja menos que su error de redondeo: se acepta lo
            # que sube dentro de ese error, y el que decide es el gradiente.
            if math.isfinite(En) and En <= E + 1e-4 * alfa * pendiente + _REDONDEO * abs(E):
                break
            alfa *= 0.5
        else:
            return Resultado(x.reshape(forma), it, fuerza, False)
        x = x + alfa * p
    return Resultado(x.reshape(forma), max_iter, fuerza, False)


def _resolver(H: sp.csc_matrix, b: np.ndarray) -> np.ndarray:
    """H p = b con SuperLU. El Hessiano proyectado puede ser singular (un modo sin rigidez):
    entonces se le suma un poco de su diagonal."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", spla.MatrixRankWarning)
        p = spla.spsolve(H, b)
    if np.all(np.isfinite(p)):
        return p
    d = H.diagonal()
    reg = 1e-8 * max(float(np.max(np.abs(d))), 1.0)
    return spla.spsolve((H + reg * sp.identity(H.shape[0], format="csc")).tocsc(), b)
