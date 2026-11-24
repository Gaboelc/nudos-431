"""El integrador del motor (T15): Newton con búsqueda en línea, y el paso de la cuerda.

- `newton` minimiza una energía con algunos nodos fijos (las manos que sostienen); T15b
  resuelve con él la catenaria y la elástica.
- `Sistema.paso` da un paso de la cuerda con su contacto (T15c): Euler implícito, en la forma
  de potencial incremental de IPC, con la barrera, el roce retrasado y cada paso de Newton
  recortado por la CCD, así que la cuerda nunca se atraviesa, tampoco entre dos iteraciones.
  Sin `dt`, el paso es cuasiestático: la inercia se cambia por una amortiguación que tira hacia
  donde estaba la cuerda, como en T14a.

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

from nudos.fisica.contacto import EPS_ROCE, MallaContacto
from nudos.fisica.materiales import GRAVEDAD
from nudos.fisica.varilla import Varilla


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


# --- El paso de la cuerda con su contacto (T15c) ---

@dataclass
class Paso:
    x: np.ndarray            # (N, 3) la cuerda al final del paso
    v: np.ndarray            # (N, 3) su velocidad, en diámetros por segundo (cero si es cuasiestático)
    iteraciones: int
    fuerza: float
    convergio: bool


class Sistema:
    """Una o varias cuerdas (`varillas`, sus nodos seguidos en ese orden), su contacto
    (`malla`, con los mismos nodos) y sus manos: los nodos `fijos` y las `fuerzas` (N, 3) en
    newtons sobre cada nodo. `kappa` es la rigidez de la barrera (ver
    `contacto.rigidez_barrera`)."""

    def __init__(self, varillas, malla: MallaContacto | None = None, fijos=(), fuerzas=None,
                 kappa: float = 1.0, roce: bool = True, eps_roce: float = EPS_ROCE,
                 tol_fuerza: float = 1e-7, max_newton: int = 500):
        self.varillas = list(varillas)
        self.cortes = np.cumsum([0, *(v.N for v in self.varillas)])
        self.N = N = int(self.cortes[-1])
        if malla is not None and malla.N != N:
            raise ValueError("la malla de contacto no tiene los nodos de las varillas")
        self.malla = malla
        self.fijos = np.asarray(fijos, int)
        self.fuerzas = np.zeros((N, 3)) if fuerzas is None else np.asarray(fuerzas, float).reshape(N, 3)
        self.kappa, self.roce, self.eps_roce = kappa, roce, eps_roce
        self.tol_fuerza, self.max_newton = tol_fuerza, max_newton
        # La masa de cada nodo, en N·s²/d: su peso sobre la gravedad en diámetros por segundo².
        self.masa = np.concatenate([
            v.material.peso_por_d * (np.r_[v.l, 0.0] + np.r_[0.0, v.l]) / 2
            / (GRAVEDAD / v.material.diametro_m) for v in self.varillas])

    def elastica(self, x, orden: int = 2, proyectar: bool = False):
        """La energía de las varillas y de las fuerzas de las manos."""
        x = np.asarray(x, float).ravel()
        partes = [v.evaluar(x[3 * a:3 * b], orden, proyectar)
                  for v, a, b in zip(self.varillas, self.cortes[:-1], self.cortes[1:])]
        if orden == 0:
            return math.fsum(partes) - float(self.fuerzas.ravel() @ x)
        E = math.fsum(p[0] for p in partes) - float(self.fuerzas.ravel() @ x)
        g = np.concatenate([p[1] for p in partes]) - self.fuerzas.ravel()
        if orden == 1:
            return E, g, None
        return E, g, sp.block_diag([p[2] for p in partes], format="csr")

    def paso(self, x, v=None, dt: float | None = None, amortiguacion: float = 2.0) -> Paso:
        """Un paso desde la cuerda en x (N, 3) con velocidad v. Con `dt` (en segundos), Euler
        implícito; sin `dt`, cuasiestático, con `amortiguacion` (N/d por nodo). Los nodos fijos
        quedan donde están en x."""
        x0 = np.asarray(x, float).reshape(self.N, 3)
        v0 = np.zeros_like(x0) if v is None else np.asarray(v, float).reshape(self.N, 3)
        if dt is None:
            A = np.full(3 * self.N, amortiguacion)
            meta = x0.ravel()
        else:
            A = np.repeat(self.masa, 3) / dt ** 2
            meta = (x0 + dt * v0).ravel()
        m = self.malla
        roce = m.roce_retrasado(x0, self.kappa, self.eps_roce) if m is not None and self.roce else None
        if roce is not None and len(roce) == 0:
            roce = None

        def evaluar(y, orden, proyectar=False):
            d = y - meta
            inercia = 0.5 * float(np.sum(A * d * d))
            if orden == 0:
                E = self.elastica(y, 0) + inercia
                if m is not None:
                    E += m.barrera(y, self.kappa, 0)
                if roce is not None:
                    E += roce.evaluar(y, 0)
                return E
            E, g, H = self.elastica(y, 2, proyectar)
            E += inercia
            g = g + A * d
            H = H + sp.diags(A, format="csr")
            for parte in ((m.barrera(y, self.kappa),) if m is not None else ()) +                     ((roce.evaluar(y),) if roce is not None else ()):
                E += parte[0]
                g = g + parte[1]
                H = H + parte[2]
            return E, g, H

        paso_maximo = None
        if m is not None:
            def paso_maximo(y, p):
                return m.paso_libre(y, y + p)

        r = newton(evaluar, x0.ravel(), fijos=self.fijos, tol_fuerza=self.tol_fuerza,
                   max_iter=self.max_newton, paso_maximo=paso_maximo)
        x1 = r.x.reshape(self.N, 3)
        v1 = np.zeros_like(x1) if dt is None else (x1 - x0) / dt
        return Paso(x1, v1, r.iteraciones, r.fuerza, r.convergio)
