"""Prueba de concepto del motor de física de la cuerda (T14a, fase 5 del plan).

Una cuerda es una varilla elástica discreta: nodos en la línea central, cada tramo con su
largo de reposo. Su energía es la suma de
- estiramiento: EA / (2 l) · (|e| − l)² por tramo, casi inextensible;
- flexión: EI / (2 l³) · |x_{i−1} − 2 x_i + x_{i+1}|² por nodo interior, que para tramos de
  largo parejo es EI/2 · κ² · l (la curvatura discreta al cuadrado);
- peso: m g z por nodo;
- manos: puntos fijos (fuera de las incógnitas) y fuerzas constantes, −F·x;
- contacto: la barrera de IPC (ipctk) entre tramos de cuerda, con los anfitriones (mallas
  fijas) y con la mesa (un plano). Ningún tramo se acerca a otro a menos de `dmin`, así que
  la cuerda nunca se atraviesa; la búsqueda en línea se recorta con la CCD de ipctk;
- roce: el de Coulomb suavizado de IPC, con la fuerza normal y la base tangente del paso
  anterior (roce «retrasado»), sobre el desplazamiento del paso;
- un término proximal c/2 · |x − x_anterior|², que hace de amortiguación: el motor avanza por
  pasos cuasiestáticos hasta que la cuerda deja de moverse.

Unidades: longitudes en diámetros de cuerda (una cuerda de 8 mm), fuerzas en newtons y
energías en N·diámetro. Corre en el entorno aparte de la prueba (ver LEEME.md).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

import ipctk
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

D_M = 0.008            # el diámetro de la cuerda, en metros
G = 9.81 / D_M         # la gravedad, en diámetros/s²


@dataclass
class Material:
    """Una cuerda trenzada de 8 mm (valores de partida; se calibran en T15e)."""
    EA: float = 20000.0          # N: rigidez a la tracción (0,5 % con 100 N)
    EI: float = 31.0             # N·d²: rigidez a la flexión (2·10⁻³ N·m²)
    peso_por_d: float = 0.0035   # N por diámetro de largo (45 g/m)
    mu_cuerda: float = 0.35      # roce cuerda con cuerda
    mu_madera: float = 0.45      # roce cuerda con madera


@dataclass
class Solido:
    """Un anfitrión fijo como malla de triángulos (vértices, caras)."""
    V: np.ndarray
    F: np.ndarray


def cilindro(centro, eje: str, radio: float, largo: float, lados: int = 64, anillos: int = 24) -> Solido:
    """Un cilindro abierto, a lo largo de x o de y."""
    t = np.linspace(0, 2 * math.pi, lados, endpoint=False)
    s = np.linspace(-largo / 2, largo / 2, anillos)
    a, b = np.meshgrid(s, t, indexing="ij")
    if eje == "x":
        V = np.column_stack([a.ravel(), radio * np.cos(b.ravel()), radio * np.sin(b.ravel())])
    else:
        V = np.column_stack([radio * np.cos(b.ravel()), a.ravel(), radio * np.sin(b.ravel())])
    V = V + np.asarray(centro, float)
    F = []
    for i in range(anillos - 1):
        for j in range(lados):
            p, q = i * lados + j, i * lados + (j + 1) % lados
            F += [(p, q, q + lados), (p, q + lados, p + lados)]
    return Solido(V, np.array(F, dtype=np.int32))


def _aristas(F):
    E = np.sort(np.vstack([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    return np.unique(E, axis=0)


@dataclass
class Escena:
    X0: np.ndarray                      # (N, 3) la cuerda al empezar
    material: Material = field(default_factory=Material)
    solidos: list = field(default_factory=list)
    mesa: float | None = 0.0            # altura de la mesa (z), o None
    fijos: np.ndarray | None = None     # índices de nodos fijos
    fuerzas: dict = field(default_factory=dict)   # nodo -> fuerza (3,) en N
    dmin: float = 0.95                  # distancia mínima entre ejes: la cuerda se comprime un 5 %
    dhat: float = 0.1                   # la barrera actúa entre dmin y dmin + dhat
    vecinos: float = 1.5                # tramos a menos de esto a lo largo de la cuerda no chocan
    proximal: float = 2.0               # N/d por nodo: amortiguación de cada paso
    eps_roce: float = 1e-3              # diámetros: debajo de esto el roce es estático
    roce: bool = True
    # Tensión de atado, en N por tramo (N − 1): el largo de reposo de cada tramo se acorta
    # T/EA, así que el tramo queda tenso sin que una mano lo empuje, como una vuelta que se tiró
    # al darla y quedó así por el roce.
    tension_atado: np.ndarray | None = None


class Motor:
    def __init__(self, e: Escena):
        self.e = e
        X0 = np.asarray(e.X0, float)
        self.N = N = len(X0)
        self.l = np.linalg.norm(np.diff(X0, axis=0), axis=1)   # largos de reposo
        if e.tension_atado is not None:
            self.l = self.l * (1 - np.asarray(e.tension_atado, float) / e.material.EA)
        # La malla de colisión: la cuerda (sus tramos) y los sólidos (sus caras y aristas).
        V = [X0]
        E = [np.column_stack([np.arange(N - 1), np.arange(1, N)])]
        Fc = []
        base = N
        for s in e.solidos:
            V.append(s.V)
            E.append(_aristas(s.F) + base)
            Fc.append(s.F + base)
            base += len(s.V)
        self.V_fijos = np.vstack(V[1:]) if len(V) > 1 else np.zeros((0, 3))
        Vt = np.vstack(V)
        Et = np.vstack(E).astype(np.int32)
        Ft = np.vstack(Fc).astype(np.int32) if Fc else np.zeros((0, 3), np.int32)
        self.malla = ipctk.CollisionMesh(np.asfortranarray(Vt), np.asfortranarray(Et), np.asfortranarray(Ft))
        k = max(2, int(math.ceil(e.vecinos / float(np.mean(self.l)))))

        # Filtros nativos de ipctk (una función de Python traba el broad phase en paralelo):
        # los sólidos no chocan entre sí, y dos nodos a menos de k tramos a lo largo de la
        # cuerda tampoco.
        vecinos = {(i, j): False for i in range(N) for j in range(i + 1, min(N, i + k + 1))}
        self.malla.can_collide = ipctk.make_static_obstacle_filter(N) & ipctk.make_sparse_filter(vecinos, True)
        if e.mesa is not None:
            # El plano queda dmin por debajo de donde se apoya el eje de la cuerda (z = 0,5).
            # Hyperplane(normal, origen): así lo guarda ipctk (normal(), origin()).
            self.malla.planes = [ipctk.Hyperplane(np.array([0, 0, 1.0]), np.array([0, 0, e.mesa + 0.5 - e.dmin - 0.05]))]
        # Las incógnitas: los nodos de la cuerda que no están fijos.
        libre = np.ones(N, bool)
        if e.fijos is not None:
            libre[np.asarray(e.fijos)] = False
        self.libre = libre
        self.dof = np.flatnonzero(np.repeat(libre, 3))
        # Flexión: matriz constante.
        filas, cols, vals = [], [], []
        lm = float(np.mean(self.l))
        kb = e.material.EI / lm ** 3
        for i in range(1, N - 1):
            idx = (i - 1, i, i + 1)
            w = (1.0, -2.0, 1.0)
            for a, wa in zip(idx, w):
                for b, wb in zip(idx, w):
                    for c in range(3):
                        filas.append(3 * a + c); cols.append(3 * b + c); vals.append(kb * wa * wb)
        self.Kb = sp.csr_matrix((vals, (filas, cols)), shape=(3 * N, 3 * N))
        self.masa_g = e.material.peso_por_d * self.l.mean()   # peso de cada nodo, en N
        self.F_ext = np.zeros(3 * N)
        for i, f in e.fuerzas.items():
            self.F_ext[3 * i:3 * i + 3] += f
        self.registro = []
        # La CCD aditiva (la de IPC para varillas y telas delgadas) con LBVH: cien veces más
        # rápida que Tight Inclusion con dmin, y menos conservadora.
        self.bp, self.ccd = ipctk.LBVH(), ipctk.AdditiveCCD()

    # --- Energía de la cuerda (sin contacto) ---
    def _elastica(self, x, x_prev):
        N, e = self.N, self.e
        X = x.reshape(N, 3)
        d = np.diff(X, axis=0)
        L = np.linalg.norm(d, axis=1)
        u = d / L[:, None]
        ks = e.material.EA / self.l
        E = 0.5 * np.sum(ks * (L - self.l) ** 2)
        g = np.zeros((N, 3))
        f = (ks * (L - self.l))[:, None] * u
        g[:-1] -= f
        g[1:] += f
        # Hessiano del estiramiento, proyectado a semidefinido (sin el término negativo).
        A = ks[:, None, None] * (u[:, :, None] * u[:, None, :])
        extra = ks * np.maximum(L - self.l, 0) / L
        A += extra[:, None, None] * (np.eye(3)[None] - u[:, :, None] * u[:, None, :])
        i0 = np.arange(N - 1)
        filas, cols, vals = [], [], []
        for a, b, s in ((0, 0, 1), (1, 1, 1), (0, 1, -1), (1, 0, -1)):
            ia, ib = i0 + a, i0 + b
            for r in range(3):
                for c in range(3):
                    filas.append(3 * ia + r); cols.append(3 * ib + c); vals.append(s * A[:, r, c])
        Hs = sp.csr_matrix((np.concatenate(vals), (np.concatenate(filas), np.concatenate(cols))), shape=(3 * N, 3 * N))
        Eb = 0.5 * x @ (self.Kb @ x)
        gb = self.Kb @ x
        Eg = self.masa_g * np.sum(X[:, 2])
        gg = np.zeros((N, 3)); gg[:, 2] = self.masa_g
        Ef = -self.F_ext @ x
        c = e.proximal
        Ep = 0.5 * c * np.sum((x - x_prev) ** 2)
        gp = c * (x - x_prev)
        Etot = E + Eb + Eg + Ef + Ep
        gtot = g.ravel() + gb + gg.ravel() - self.F_ext + gp
        Htot = Hs + self.Kb + c * sp.eye(3 * N)
        return Etot, gtot, Htot

    # --- Contacto y roce (ipctk), sobre toda la malla de colisión ---
    def _V(self, x):
        return np.asfortranarray(np.vstack([x.reshape(self.N, 3), self.V_fijos]))

    def _contacto(self, x, colisiones, barrera, roce_col, roce_pot, V_prev):
        V = self._V(x)
        E = barrera(colisiones, self.malla, V)
        g = barrera.gradient(colisiones, self.malla, V)
        H = barrera.hessian(colisiones, self.malla, V, project_hessian_to_psd=ipctk.PSDProjectionMethod.CLAMP)
        if roce_col is not None:
            U = np.asfortranarray(V - V_prev)
            E += roce_pot(roce_col, self.malla, U)
            g = g + roce_pot.gradient(roce_col, self.malla, U)
            H = H + roce_pot.hessian(roce_col, self.malla, U, project_hessian_to_psd=ipctk.PSDProjectionMethod.CLAMP)
        n = 3 * self.N
        return E, np.asarray(g).ravel()[:n], H.tocsr()[:n, :n]

    def paso(self, x_prev, kappa, max_iter=50, tol=1e-6):
        """Un paso cuasiestático desde x_prev: minimiza la energía con el roce retrasado."""
        e = self.e
        V_prev = self._V(x_prev)
        barrera = ipctk.BarrierPotential(e.dhat, kappa)
        roce_col = roce_pot = None
        if e.roce:
            col_prev = ipctk.NormalCollisions()
            col_prev.build(self.malla, V_prev, e.dhat, e.dmin)
            roce_col = ipctk.TangentialCollisions()
            mus = np.where(np.arange(self.malla.num_vertices) < self.N, e.material.mu_cuerda, e.material.mu_madera)
            roce_col.build(self.malla, V_prev, col_prev, barrera, e.material.mu_cuerda)
            roce_pot = ipctk.FrictionPotential(e.eps_roce)
        x = x_prev.copy()
        for it in range(max_iter):
            col = ipctk.NormalCollisions()
            col.build(self.malla, self._V(x), e.dhat, e.dmin)
            Ee, ge, He = self._elastica(x, x_prev)
            Ec, gc, Hc = self._contacto(x, col, barrera, roce_col, roce_pot, V_prev)
            g = (ge + gc)[self.dof]
            if np.max(np.abs(g)) < tol * max(1.0, np.abs(self.F_ext).max()):
                break
            H = (He + Hc)[self.dof][:, self.dof].tocsc()
            p = np.zeros_like(x)
            p[self.dof] = spla.spsolve(H, -g)
            if not np.all(np.isfinite(p)):
                raise FloatingPointError("Newton dio un paso no finito")
            # La CCD recorta el paso para que nada se acerque a menos de dmin.
            V0 = self._V(x)
            V1 = self._V(x + p)
            alfa = min(1.0, ipctk.compute_collision_free_stepsize(
                self.malla, V0, V1, min_distance=e.dmin, broad_phase=self.bp, narrow_phase_ccd=self.ccd))
            E0 = Ee + Ec
            while alfa > 1e-10:
                xn = x + alfa * p
                coln = ipctk.NormalCollisions()
                coln.build(self.malla, self._V(xn), e.dhat, e.dmin)
                En = self._elastica(xn, x_prev)[0] + self._contacto(xn, coln, barrera, roce_col, roce_pot, V_prev)[0]
                if En <= E0 + 1e-4 * alfa * (g @ p[self.dof]):
                    break
                alfa *= 0.5
            x = x + alfa * p
            if alfa * np.max(np.abs(p)) < 1e-7:
                break
        return x, it + 1

    def resolver(self, x0=None, pasos=200, kappa=None, quieto=1e-4, mostrar=True):
        """Pasos cuasiestáticos hasta que la cuerda deja de moverse (o `pasos`)."""
        x = (np.asarray(self.e.X0, float) if x0 is None else x0).ravel().copy()
        if kappa is None:
            kappa = self.kappa_inicial(x)
        t0 = time.time()
        for k in range(pasos):
            xn, its = self.paso(x, kappa)
            mov = np.max(np.linalg.norm((xn - x).reshape(-1, 3), axis=1))
            x = xn
            col = ipctk.NormalCollisions()
            col.build(self.malla, self._V(x), self.e.dhat, self.e.dmin)
            dist = col.compute_minimum_distance(self.malla, self._V(x)) if len(col) else float("inf")
            self.registro.append((k, its, mov, dist, time.time() - t0))
            if mostrar and (k % 10 == 0 or mov < quieto):
                print(f"  paso {k:4d}: {its:2d} iteraciones, se movió {mov:.5f} d, distancia mínima {math.sqrt(dist) if dist < 1e9 else float('inf'):.3f}, {time.time() - t0:.0f} s", flush=True)
            if mov < quieto:
                break
        return x.reshape(-1, 3)

    def kappa_inicial(self, x):
        """La rigidez de la barrera. Medida con dos tramos cruzados (dmin 0,95, dhat 0,1): a
        media franja, la barrera de rigidez 1 empuja 1,8 N. Una cuerda con tensión T sobre un
        palo de radio R aprieta T·h/R por nodo; con esta rigidez, ese apoyo queda a media franja.
        Sin manos, el peso de unos cuantos nodos."""
        T = np.abs(self.F_ext).max()
        f = T * float(np.mean(self.l)) / 2.0 if T > 0 else self.masa_g * 20
        return max(f, 1e-3) / 1.8


def penetracion_minima(X, solidos_eje):
    """Para revisar: la menor distancia del eje de la cuerda a cada cilindro (centro, eje, radio)."""
    out = []
    for c, eje, r in solidos_eje:
        c = np.asarray(c, float)
        if eje == "x":
            d = np.hypot(X[:, 1] - c[1], X[:, 2] - c[2])
        else:
            d = np.hypot(X[:, 0] - c[0], X[:, 2] - c[2])
        out.append(float(d.min() - r))
    return out
