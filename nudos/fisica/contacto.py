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
  superficie redonda, para radios de hasta 2,5. A lo largo, un prisma es exacto, así que basta
  con un anillo en cada punta: con 24, como en T14a, armar los contactos tardaba 25 veces más.
- Los contactos son los de IPC, los que vienen por omisión. Un nodo sobre una arista de la
  malla suma los contactos con las dos caras, con la arista y con sus vértices, y sobre la
  diagonal de la mesa empuja 4 veces más que sobre una cara (T15c). Eso solo reparte el apoyo:
  ese nodo queda unos 0,03 diámetros más alto y sostiene más, pero la fuerza total y el roce
  total son los de la física (el cabrestante y la tabla inclinada lo comprueban). Los de OGC
  (*Offset Geometric Contact*) empujan parejo, pero su energía salta cuando dos cuerdas se
  cruzan justo en un nodo de cada una (cuenta uno de los cuatro pares de tramos: un paso de
  10⁻⁶ la multiplica por 4), y Newton se traba en el salto.
- Calcular dos veces da lo mismo bit a bit solo con `ipctk` en un hilo (ver abajo): las
  distancias salían iguales en paralelo (T15a), pero las fuerzas de la barrera no (T15c).

Las longitudes van en diámetros de cuerda: el eje de una cuerda apoyada en la mesa queda a 0,5.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import ipctk
import numpy as np
import scipy.sparse as sp

from nudos.fisica.materiales import CUERDA_8MM

# ipctk arma los contactos y suma sus fuerzas en varios hilos, y con más de uno el orden de la
# suma cambia de una corrida a otra (medido en T15c: el choque de dos cuerdas daba otro
# resultado cada vez). Con un hilo da lo mismo bit a bit. `construir` ya reparte los pasos de un
# nudo en procesos (nudos/procesos.py), así que no se pierde velocidad.
ipctk.set_num_threads(1)

DMIN = 0.95    # la distancia mínima entre ejes: la cuerda se comprime hasta un 5 %
DHAT = 0.1     # la barrera actúa entre DMIN y DMIN + DHAT
VECINOS = 1.5  # dos nodos a menos de esto a lo largo de la cuerda no chocan
LADOS = 64     # los lados de la malla de un palo
EPS_ROCE = 1e-3  # diámetros por paso: debajo de esto, el roce es estático (suavizado)


@dataclass(frozen=True)
class Solido:
    """Un anfitrión fijo, como malla de triángulos: vértices (n, 3) y caras (m, 3), y el roce
    de la cuerda con él (sin `mu`, el de la madera)."""
    V: np.ndarray
    F: np.ndarray
    mu: float | None = None


def cilindro(centro, eje, radio: float, largo: float, lados: int = LADOS, anillos: int = 2,
             mu: float | None = None) -> Solido:
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
    return Solido(V, np.array(F, dtype=np.int32), mu)


def mesa(altura: float = 0.0, dmin: float = DMIN, dhat: float = DHAT, medio: float = 500.0) -> Solido:
    """La mesa, como un cuadrado de 2·`medio` de lado en dos triángulos. Queda de modo que el
    eje de una cuerda apoyada (z = altura + 0,5) esté a media franja de la barrera, a
    dmin + dhat/2 de la malla."""
    z = altura + 0.5 - dmin - dhat / 2
    V = np.array([[-medio, -medio, z], [medio, -medio, z], [medio, medio, z], [-medio, medio, z]])
    return Solido(V, np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int32))


# La fuerza con que empuja la barrera de rigidez 1 a un nodo de cuerda a media franja de una
# malla (a dmin + dhat/2), en N. No depende del largo de los tramos (medido en T15c).
FUERZA_MEDIA_FRANJA = 0.5101


def rigidez_barrera(fuerza_por_nodo: float) -> float:
    """La rigidez de la barrera para que un nodo que se apoya con `fuerza_por_nodo` (en N)
    quede a media franja. Una cuerda con tensión T que abraza un palo de radio R aprieta T·h/R
    por nodo, con h el largo de los tramos; una que descansa, su peso por nodo."""
    return fuerza_por_nodo / FUERZA_MEDIA_FRANJA


def _aristas(F: np.ndarray) -> np.ndarray:
    E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    return np.unique(E, axis=0)


class MallaContacto:
    """La cuerda (N nodos en fila), los anfitriones fijos y, si hay, la mesa (`altura_mesa`).

    `X0` da la forma de partida, solo para saber cuántos nodos tiene la cuerda y a qué
    distancia van; las posiciones de cada momento se pasan a cada llamada (`x`, (N, 3)).
    """

    def __init__(self, X0, solidos=(), altura_mesa: float | None = None,
                 dmin: float = DMIN, dhat: float = DHAT, vecinos: float = VECINOS,
                 nodos_por_cuerda=None, mu_cuerda: float = CUERDA_8MM.mu_cuerda,
                 mu_solidos: float = CUERDA_8MM.mu_madera):
        X0 = np.asarray(X0, float)
        self.N = N = len(X0)
        self.dmin, self.dhat = dmin, dhat
        cortes = np.cumsum([0, *(nodos_por_cuerda or [N])])
        if cortes[-1] != N or np.any(np.diff(cortes) < 2):
            raise ValueError("nodos_por_cuerda tiene que sumar los nodos de X0, al menos 2 por cuerda")
        self.cortes = cortes
        if altura_mesa is not None:
            solidos = [*solidos, mesa(altura_mesa, dmin, dhat)]
        V = [X0]
        E = [np.column_stack([np.arange(a, b - 1), np.arange(a + 1, b)]) for a, b in zip(cortes[:-1], cortes[1:])]
        F = []
        # El roce de cada par es el promedio de los de sus vértices (así lo mezcla ipctk), así
        # que un vértice de un anfitrión lleva 2·μ − μ_cuerda para que cuerda con anfitrión dé μ.
        mu = [np.full(N, mu_cuerda)]
        base = N
        for s in solidos:
            V.append(s.V)
            E.append(_aristas(s.F) + base)
            F.append(s.F + base)
            mu.append(np.full(len(s.V), 2 * (mu_solidos if s.mu is None else s.mu) - mu_cuerda))
            base += len(s.V)
        self.V_fijos = np.vstack(V[1:]) if len(V) > 1 else np.zeros((0, 3))
        self.mu = np.concatenate(mu)
        self.malla = ipctk.CollisionMesh(
            np.asfortranarray(np.vstack(V)),
            np.asfortranarray(np.vstack(E).astype(np.int32)),
            np.asfortranarray(np.vstack(F).astype(np.int32) if F else np.zeros((0, 3), np.int32)))
        # Los anfitriones no chocan entre sí, y los nodos a menos de k tramos a lo largo de una
        # misma cuerda tampoco. Los dos filtros son nativos de ipctk.
        pares = {}
        for a, b in zip(cortes[:-1], cortes[1:]):
            h = float(np.mean(np.linalg.norm(np.diff(X0[a:b], axis=0), axis=1)))
            k = max(2, math.ceil(vecinos / h))
            pares.update({(i, j): False for i in range(a, b) for j in range(i + 1, min(b, i + k + 1))})
        self.malla.can_collide = ipctk.make_static_obstacle_filter(N) & ipctk.make_sparse_filter(pares, True)
        self._bp, self._ccd = ipctk.LBVH(), ipctk.AdditiveCCD()

    def V(self, x) -> np.ndarray:
        """Los vértices de toda la malla con la cuerda en `x`, como los pide ipctk."""
        return np.asfortranarray(np.vstack([np.asarray(x, float).reshape(self.N, 3), self.V_fijos]))

    def colisiones(self, x) -> ipctk.NormalCollisions:
        """Los pares dentro de la franja de la barrera (a menos de dmin + dhat)."""
        col = ipctk.NormalCollisions()
        col.build(self.malla, self.V(x), self.dhat, self.dmin, self._bp)
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

    # --- La barrera y el roce (T15c) ---

    def barrera(self, x, kappa: float, orden: int = 2):
        """La barrera de IPC con rigidez `kappa`: su energía, su gradiente (3N,) y su Hessiano
        (3N × 3N, CSR, proyectado a semidefinido par por par), sobre los nodos de la cuerda."""
        V = self.V(x)
        col = self.colisiones(x)
        B = ipctk.BarrierPotential(self.dhat, kappa)
        E = float(B(col, self.malla, V))
        if orden == 0:
            return E
        n = 3 * self.N
        g = np.asarray(B.gradient(col, self.malla, V))[:n]
        if orden == 1:
            return E, g, None
        H = B.hessian(col, self.malla, V, project_hessian_to_psd=ipctk.PSDProjectionMethod.CLAMP)
        return E, g, _recortar(H, n)

    def roce_retrasado(self, x0, kappa: float, eps: float = EPS_ROCE) -> "Roce":
        """El roce de Coulomb suavizado de IPC para un paso que sale de x0, «retrasado»: la
        fuerza normal de cada contacto y su plano tangente son los de x0 (con la barrera de
        rigidez `kappa`). Hasta `eps` diámetros de corrimiento en el paso, el roce crece como un
        resorte hasta μ·N (el estático, suavizado); más allá, es μ·N.

        Un solo μ, el estático, para el estático y el dinámico: en ipctk 1.6.1, con μ_s > μ_k,
        la fuerza crece con el corrimiento hasta μ_k y nunca llega a μ_s (medido en T15c: a
        22°, con μ_s = 0,45 y μ_k = 0,35, la cuerda desliza por la tabla), así que un μ_k
        aparte solo debilita lo que sostiene un nudo."""
        V0 = self.V(x0)
        col = self.colisiones(x0)
        tc = ipctk.TangentialCollisions()
        tc.build(self.malla, V0, col, ipctk.BarrierPotential(self.dhat, kappa), self.mu, self.mu)
        return Roce(self, tc, ipctk.FrictionPotential(eps), V0)


@dataclass
class Roce:
    """El roce de un paso (ver `MallaContacto.roce_retrasado`)."""
    malla: MallaContacto
    colisiones: ipctk.TangentialCollisions
    potencial: ipctk.FrictionPotential
    V0: np.ndarray

    def __len__(self):
        return len(self.colisiones)

    def evaluar(self, x, orden: int = 2):
        """La energía del roce para la cuerda en x, su gradiente y su Hessiano proyectado, como
        `MallaContacto.barrera`. Los anfitriones no se mueven."""
        m = self.malla
        U = np.asfortranarray(m.V(x) - self.V0)
        E = float(self.potencial(self.colisiones, m.malla, U))
        if orden == 0:
            return E
        n = 3 * m.N
        g = np.asarray(self.potencial.gradient(self.colisiones, m.malla, U))[:n]
        if orden == 1:
            return E, g, None
        H = self.potencial.hessian(self.colisiones, m.malla, U,
                                   project_hessian_to_psd=ipctk.PSDProjectionMethod.CLAMP)
        return E, g, _recortar(H, n)


def _recortar(H, n: int) -> sp.csr_matrix:
    """La parte de la cuerda (las primeras n filas y columnas) de un Hessiano de ipctk."""
    H = sp.csr_matrix(H)[:n, :n]
    H.sort_indices()
    return H
