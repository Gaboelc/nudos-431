"""La malla de contacto del motor, sobre `ipctk` 1.6.1 (D11).

Lo que T14a aprendió de la biblioteca (rama `poc/motor`, `poc/motor/LEEME.md`) queda aquí, y
`tests/test_fisica_contacto.py` lo comprueba:

- La mesa es una malla de dos triángulos grandes, no un `ipctk.Hyperplane`. Un plano de ipctk
  solo ve los nodos a menos de (dmin + dhat)/2, no a menos de dmin + dhat (medido en T15a):
  con dmin 0,95, una cuerda apoyada a 1 diámetro del plano no tenía contacto, y en T14a la
  mesa la sostenía solo la CCD, que recorta el paso sin hacer fuerza. (Y `Hyperplane` recibe
  primero la normal y después el origen.)
- Las distancias de `ipctk` vienen al cuadrado. `distancia_minima` devuelve la distancia.
- Dos nodos cercanos a lo largo de la cuerda no chocan entre sí (sus tramos se tocan siempre).
  Ese filtro tiene que ser nativo (`make_static_obstacle_filter & make_sparse_filter`): una
  función de Python en `can_collide` traba la fase gruesa, que corre en hilos de C++.
- La CCD es la aditiva (`AdditiveCCD`) con `LBVH`: de 0,005 a 0,08 s por llamada, contra los
  7 a 11 s de la que viene por omisión (Tight Inclusion), y deja pasos 15 veces más largos.
- Un palo es una malla de 64 lados: la cara plana queda a menos de 0,003 diámetros de la
  superficie redonda, para radios de hasta 2,5.
- Calcular dos veces da lo mismo bit a bit, aunque `ipctk` arme los contactos en paralelo.

Las longitudes van en diámetros de cuerda: el eje de una cuerda apoyada en la mesa queda a 0,5.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import ipctk
import numpy as np

DMIN = 0.95    # la distancia mínima entre ejes: la cuerda se comprime hasta un 5 %
DHAT = 0.1     # la barrera actúa entre DMIN y DMIN + DHAT
VECINOS = 1.5  # dos nodos a menos de esto a lo largo de la cuerda no chocan
LADOS = 64     # los lados de la malla de un palo


@dataclass(frozen=True)
class Solido:
    """Un anfitrión fijo, como malla de triángulos: vértices (n, 3) y caras (m, 3)."""
    V: np.ndarray
    F: np.ndarray


def cilindro(centro, eje, radio: float, largo: float, lados: int = LADOS, anillos: int = 24) -> Solido:
    """Un cilindro abierto de `radio` y `largo` alrededor de `centro`, a lo largo de `eje`
    (un vector, no hace falta que sea unitario)."""
    w = np.asarray(eje, float)
    w = w / np.linalg.norm(w)
    a = np.cross(w, [0.0, 0.0, 1.0] if abs(w[2]) < 0.9 else [1.0, 0.0, 0.0])
    a /= np.linalg.norm(a)
    b = np.cross(w, a)
    t = np.linspace(0, 2 * math.pi, lados, endpoint=False)
    s = np.linspace(-largo / 2, largo / 2, anillos)
    S, T = np.meshgrid(s, t, indexing="ij")
    S, T = S.ravel()[:, None], T.ravel()[:, None]
    V = np.asarray(centro, float) + S * w + radio * (np.cos(T) * a + np.sin(T) * b)
    F = []
    for i in range(anillos - 1):
        for j in range(lados):
            p, q = i * lados + j, i * lados + (j + 1) % lados
            F += [(p, q, q + lados), (p, q + lados, p + lados)]
    return Solido(V, np.array(F, dtype=np.int32))


def mesa(altura: float = 0.0, dmin: float = DMIN, dhat: float = DHAT, medio: float = 500.0) -> Solido:
    """La mesa, como un cuadrado de 2·`medio` de lado en dos triángulos. Queda de modo que el
    eje de una cuerda apoyada (z = altura + 0,5) esté a media franja de la barrera, a
    dmin + dhat/2 de la malla."""
    z = altura + 0.5 - dmin - dhat / 2
    V = np.array([[-medio, -medio, z], [medio, -medio, z], [medio, medio, z], [-medio, medio, z]])
    return Solido(V, np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32))


def _aristas(F: np.ndarray) -> np.ndarray:
    E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    return np.unique(E, axis=0)


class MallaContacto:
    """La cuerda (N nodos en fila), los anfitriones fijos y, si hay, la mesa (`altura_mesa`).

    `X0` da la forma de partida, solo para saber cuántos nodos tiene la cuerda y a qué
    distancia van; las posiciones de cada momento se pasan a cada llamada (`x`, (N, 3)).
    """

    def __init__(self, X0, solidos=(), altura_mesa: float | None = None,
                 dmin: float = DMIN, dhat: float = DHAT, vecinos: float = VECINOS):
        X0 = np.asarray(X0, float)
        self.N = N = len(X0)
        self.dmin, self.dhat = dmin, dhat
        if altura_mesa is not None:
            solidos = [*solidos, mesa(altura_mesa, dmin, dhat)]
        V = [X0]
        E = [np.column_stack([np.arange(N - 1), np.arange(1, N)])]
        F = []
        base = N
        for s in solidos:
            V.append(s.V)
            E.append(_aristas(s.F) + base)
            F.append(s.F + base)
            base += len(s.V)
        self.V_fijos = np.vstack(V[1:]) if len(V) > 1 else np.zeros((0, 3))
        self.malla = ipctk.CollisionMesh(
            np.asfortranarray(np.vstack(V)),
            np.asfortranarray(np.vstack(E).astype(np.int32)),
            np.asfortranarray(np.vstack(F).astype(np.int32) if F else np.zeros((0, 3), np.int32)))
        # Los anfitriones no chocan entre sí, y los nodos a menos de k tramos a lo largo de la
        # cuerda tampoco. Los dos filtros son nativos de ipctk.
        h = float(np.mean(np.linalg.norm(np.diff(X0, axis=0), axis=1)))
        k = max(2, math.ceil(vecinos / h))
        pares = {(i, j): False for i in range(N) for j in range(i + 1, min(N, i + k + 1))}
        self.malla.can_collide = ipctk.make_static_obstacle_filter(N) & ipctk.make_sparse_filter(pares, True)
        self._bp, self._ccd = ipctk.LBVH(), ipctk.AdditiveCCD()

    def V(self, x) -> np.ndarray:
        """Los vértices de toda la malla con la cuerda en `x`, como los pide ipctk."""
        return np.asfortranarray(np.vstack([np.asarray(x, float).reshape(self.N, 3), self.V_fijos]))

    def colisiones(self, x) -> ipctk.NormalCollisions:
        """Los pares dentro de la franja de la barrera (a menos de dmin + dhat)."""
        col = ipctk.NormalCollisions()
        col.build(self.malla, self.V(x), self.dhat, self.dmin)
        return col

    def distancia_minima(self, x) -> float:
        """La menor distancia entre ejes (o a la malla de un palo o de la mesa) de los pares que
        pueden chocar, dentro de la franja; infinito si no hay ninguno. ipctk la da al cuadrado."""
        col = self.colisiones(x)
        if len(col) == 0:
            return math.inf
        return math.sqrt(col.compute_minimum_distance(self.malla, self.V(x)))

    def paso_libre(self, x0, x1) -> float:
        """La fracción de 0 a 1 del paso de x0 a x1 que se puede dar sin que ningún par se
        acerque a menos de dmin en el camino (la CCD)."""
        return min(1.0, ipctk.compute_collision_free_stepsize(
            self.malla, self.V(x0), self.V(x1), min_distance=self.dmin,
            broad_phase=self._bp, narrow_phase_ccd=self._ccd))
