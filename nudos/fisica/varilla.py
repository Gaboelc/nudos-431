"""La varilla elástica discreta del motor (T15b): la energía de la cuerda sin contacto.

La cuerda es una fila de N nodos en su línea central (*Discrete Elastic Rods*, Bergou y otros,
2008 y 2010). Cada tramo, entre dos nodos, tiene su largo de reposo. La energía es la suma de:

- **Estiramiento**, en cada tramo: EA/(2 l) · (|e| − l)², con e el tramo y l su largo de reposo.
  EA es alta: la cuerda casi no se estira.
- **Flexión**, en cada nodo interior: EI · |κb|² / (l₀ + l₁), con κb = 2 e₀ × e₁ /
  (|e₀||e₁| + e₀·e₁) la curvatura discreta (el binormal de curvatura de Bergou) y l₀, l₁ los
  largos de reposo de los dos tramos. |κb| = 2 tan(φ/2), con φ el ángulo entre los tramos, así
  que la energía crece sin límite si la cuerda se dobla sobre sí misma; para ángulos chicos es
  EI/2 · κ² por largo, la de la teoría de vigas. La cuerda es redonda (isótropa) y no tiene
  curvatura natural: la «memoria» de una cuerda que estuvo enrollada queda fuera hasta que una
  página de prueba diga que se nota.
- **Memoria**, opcional (T15d): la forma que le dio la mano. Con `curvatura` (κb₀, una por
  nodo interior), la flexión es EI · |κb − κb₀|² / (l₀ + l₁): la cuerda guarda las curvas con
  que se la dejó, como una cuerda trenzada de verdad, que se deja doblar a mano y se queda así
  (sus fibras rozan entre sí). Sin memoria, una cuerda elástica de 8 mm abre cada lazo suelto
  sobre la mesa: su peso no alcanza para que el roce la sostenga. κb₀ va en el marco del mundo,
  no en el material, así que la energía cambia si un tramo gira entero; vale para asentar, donde
  el firme y el chicote se sostienen y la cuerda se mueve poco (ver nudos/fisica/asentar.py).
- **Peso**, en cada nodo: el peso de la mitad de cada tramo vecino por su altura z.

**La torsión no entra en la energía (decidido en T15b).** En una varilla redonda sin curvatura
natural, la torsión solo cambia la forma de la línea central si algo impide que la cuerda gire
sobre su eje: con un extremo libre de girar, el ángulo del marco material de cada tramo se
acomoda hasta que la torsión es cero en todos los nodos, y la energía de torsión no hace ninguna
fuerza. En los modos de T15d (asentar y apretar) el chicote está suelto o tirado con una fuerza,
nunca sostenido sin girar, y la barrera de IPC empuja en la línea central, sin momento sobre el
eje de la cuerda. Así que el marco material de equilibrio es el marco paralelo (`marco_paralelo`),
sin torsión, y eso es lo que T15g necesita para girar la trenza en el render. Cuánto pesaría la
torsión con las dos manos sosteniendo los extremos sin girar está medido en «Cómo se hizo T15b»
(`tasks/plan.md`); si T17 lo necesita al atar, entra ahí.

Las unidades son diámetros y newtons (ver `materiales.py`); la gravedad va en −z.

El Hessiano es disperso, en `float64`, y se arma siempre en el mismo orden, así que calcular dos
veces da lo mismo bit a bit. `proyectar=True` lo deja semidefinido positivo bloque por bloque,
como lo pide Newton.
"""
from __future__ import annotations

import math

import numpy as np
import scipy.sparse as sp

from nudos.fisica.materiales import CUERDA_8MM, Material

_I3 = np.eye(3)


class Varilla:
    """La varilla de N nodos con los largos de reposo `largos` (N − 1)."""

    def __init__(self, largos, material: Material = CUERDA_8MM, gravedad: bool = True,
                 curvatura=None):
        self.l = np.asarray(largos, float).copy()
        if self.l.ndim != 1 or len(self.l) < 1 or np.any(self.l <= 0):
            raise ValueError("los largos de reposo tienen que ser positivos")
        self.N = N = len(self.l) + 1
        self.material = m = material
        self.k_estirar = m.EA / self.l                       # (N − 1,)
        self.k_doblar = m.EI / (self.l[:-1] + self.l[1:])    # (N − 2,)
        mitades = np.concatenate([self.l, [0.0]]) + np.concatenate([[0.0], self.l])
        self.peso_nodo = m.peso_por_d * mitades / 2 if gravedad else np.zeros(N)
        # La memoria: la curvatura de reposo de cada nodo interior, en el marco del mundo.
        self.curvatura = None
        if curvatura is not None:
            self.curvatura = np.asarray(curvatura, float).reshape(N - 2, 3).copy()
        # El patrón del Hessiano, fijo: los bloques 6×6 de cada tramo y 9×9 de cada nodo
        # interior ocupan grados de libertad seguidos (3i … 3i + 5 y 3(i − 1) … 3(i + 1) + 2).
        f6, c6 = np.divmod(np.arange(36), 6)
        f9, c9 = np.divmod(np.arange(81), 9)
        b6 = 3 * np.arange(N - 1)[:, None]
        b9 = 3 * np.arange(N - 2)[:, None]
        filas = np.concatenate([(b6 + f6).ravel(), (b9 + f9).ravel()])
        cols = np.concatenate([(b6 + c6).ravel(), (b9 + c9).ravel()])
        # Cada entrada de los bloques va a un lugar fijo del CSR, y las que caen en el mismo
        # lugar se suman en el orden de los bloques (np.add.at), no en el que deje el
        # ordenamiento de scipy: así H[i, j] y H[j, i] dan lo mismo bit a bit.
        n = 3 * N
        claves, self._lugar = np.unique(filas * n + cols, return_inverse=True)
        self._indices = (claves % n).astype(np.int32)
        self._indptr = np.searchsorted(claves // n, np.arange(n + 1)).astype(np.int32)

    @classmethod
    def desde_forma(cls, X, material: Material = CUERDA_8MM, tension=None, **kw) -> "Varilla":
        """La varilla con los largos de reposo de la forma X (N, 3). Con `tension` (en N, un
        número o uno por tramo), cada largo se acorta a l/(1 + T/EA): en la forma X, el tramo
        queda tirado con esa tensión justa sin que una mano lo empuje (la «tensión de atado» de
        T14a, que acortaba l·(1 − T/EA) y tiraba un 0,3 % de más con 60 N)."""
        l = np.linalg.norm(np.diff(np.asarray(X, float), axis=0), axis=1)
        if tension is not None:
            l = l / (1 + np.asarray(tension, float) / material.EA)
        return cls(l, material, **kw)

    @staticmethod
    def curvatura_de(X) -> np.ndarray:
        """La curvatura discreta κb = 2 e₀ × e₁ / (|e₀||e₁| + e₀·e₁) de cada nodo interior de
        X (N, 3): la memoria de una cuerda que quedó con esa forma."""
        X = np.asarray(X, float)
        e, f = X[1:-1] - X[:-2], X[2:] - X[1:-1]
        D = np.linalg.norm(e, axis=1) * np.linalg.norm(f, axis=1) + np.einsum("ij,ij->i", e, f)
        return 2 * np.cross(e, f) / D[:, None]

    # --- Las partes de la energía. Cada una da (E, g (N, 3), bloques del Hessiano). ---

    def estiramiento(self, x, orden: int = 2, proyectar: bool = False):
        X = _forma(x, self.N)
        d = np.diff(X, axis=0)
        L = np.linalg.norm(d, axis=1)
        k, l = self.k_estirar, self.l
        E = 0.5 * float(np.sum(k * (L - l) ** 2))
        if orden == 0:
            return E, None, None
        u = d / L[:, None]
        f = (k * (L - l))[:, None] * u
        g = np.zeros((self.N, 3))
        g[:-1] -= f
        g[1:] += f
        if orden == 1:
            return E, g, None
        # Respecto del tramo: k [u uᵀ + (1 − l/L)(I − u uᵀ)]. Lo segundo es negativo con el tramo
        # más corto que su reposo; proyectado, se corta en cero (es la proyección exacta).
        uu = u[:, :, None] * u[:, None, :]
        c = 1 - l / L
        if proyectar:
            c = np.maximum(c, 0.0)
        A = k[:, None, None] * (uu + c[:, None, None] * (_I3 - uu))
        B = np.empty((len(l), 6, 6))
        B[:, :3, :3] = A
        B[:, 3:, 3:] = A
        B[:, :3, 3:] = -A
        B[:, 3:, :3] = -A
        return E, g, B

    def flexion(self, x, orden: int = 2, proyectar: bool = False):
        X = _forma(x, self.N)
        if self.N < 3:
            return 0.0, np.zeros((self.N, 3)), np.zeros((0, 9, 9))
        e = X[1:-1] - X[:-2]
        f = X[2:] - X[1:-1]
        p = np.einsum("ij,ij->i", e, e)
        q = np.einsum("ij,ij->i", f, f)
        r = np.einsum("ij,ij->i", e, f)
        sq = np.sqrt(p * q)
        w = r / sq                       # el coseno del ángulo entre los tramos
        c = self.k_doblar
        uno = 1 + w
        if np.any(uno <= 0):
            return math.inf, None, None
        # c·|κb|² = 4c·tan²(φ/2) = 4c·(1 − w)/(1 + w), pero con el producto cruz: 1 − w pierde
        # casi todas sus cifras cuando los tramos van casi derechos, y Newton dejaría de bajar.
        cruz = np.cross(e, f)
        E = float(np.sum(4 * c * np.einsum("ij,ij->i", cruz, cruz) / (sq + r) ** 2))
        if orden == 0:
            return E, None, None
        # E = G(w(p, q, r)), con p = |e|², q = |f|², r = e·f.
        G1 = -8 * c / uno ** 2
        wu = np.stack([-w / (2 * p), -w / (2 * q), 1 / sq], axis=1)            # (n, 3)
        Eu = G1[:, None] * wu
        J = np.zeros((len(c), 3, 6))
        J[:, 0, :3] = 2 * e
        J[:, 1, 3:] = 2 * f
        J[:, 2, :3] = f
        J[:, 2, 3:] = e
        gef = np.einsum("nki,nk->ni", J, Eu)                                    # (n, 6)
        g = np.zeros((self.N, 3))
        g[:-2] -= gef[:, :3]
        g[1:-1] += gef[:, :3] - gef[:, 3:]
        g[2:] += gef[:, 3:]
        if orden == 1:
            return E, g, None
        G2 = 16 * c / uno ** 3
        wuu = np.zeros((len(c), 3, 3))
        wuu[:, 0, 0] = 3 * w / (4 * p * p)
        wuu[:, 1, 1] = 3 * w / (4 * q * q)
        wuu[:, 0, 1] = wuu[:, 1, 0] = w / (4 * p * q)
        wuu[:, 0, 2] = wuu[:, 2, 0] = -1 / (2 * p * sq)
        wuu[:, 1, 2] = wuu[:, 2, 1] = -1 / (2 * q * sq)
        Euu = G2[:, None, None] * wu[:, :, None] * wu[:, None, :] + G1[:, None, None] * wuu
        H = np.einsum("nki,nkl,nlj->nij", J, Euu, J)
        H[:, :3, :3] += 2 * Eu[:, 0, None, None] * _I3
        H[:, 3:, 3:] += 2 * Eu[:, 1, None, None] * _I3
        H[:, :3, 3:] += Eu[:, 2, None, None] * _I3
        H[:, 3:, :3] += Eu[:, 2, None, None] * _I3
        # De (e, f) a los nodos: e = x₁ − x₀, f = x₂ − x₁.
        M = np.zeros((6, 9))
        M[:3, :3], M[:3, 3:6] = -_I3, _I3
        M[3:, 3:6], M[3:, 6:] = -_I3, _I3
        B = np.einsum("ki,nkl,lj->nij", M, H, M)
        B = 0.5 * (B + np.swapaxes(B, 1, 2))     # simétrico bit a bit
        if proyectar:
            B = proyectar_psd(B)
        return E, g, B

    def memoria(self, x, orden: int = 2):
        """La parte de la flexión que viene de la memoria: EI·(|κb₀|² − 2 κb₀·κb)/(l₀ + l₁),
        que sumada a `flexion` da EI·|κb − κb₀|²/(l₀ + l₁). Sin memoria, cero."""
        if self.curvatura is None or self.N < 3:
            return (0.0, None if orden == 0 else np.zeros((self.N, 3)),
                    None if orden < 2 else np.zeros((max(self.N - 2, 0), 9, 9)))
        X = _forma(x, self.N)
        a, c = self.curvatura, self.k_doblar
        e = X[1:-1] - X[:-2]
        f = X[2:] - X[1:-1]
        p = np.einsum("ij,ij->i", e, e)
        q = np.einsum("ij,ij->i", f, f)
        r = np.einsum("ij,ij->i", e, f)
        sq = np.sqrt(p * q)
        D = sq + r
        if np.any(D <= 0):
            return math.inf, None, None
        n = np.einsum("ij,ij->i", a, np.cross(e, f))
        # φ = κb₀·κb = 2n/D, y la energía es c|κb₀|² − 2c·φ.
        E = float(np.sum(c * (np.einsum("ij,ij->i", a, a) - 4 * n / D)))
        if orden == 0:
            return E, None, None
        nd = np.concatenate([np.cross(f, a), np.cross(a, e)], axis=1)              # ∂n, (m, 6)
        rqp, rpq = np.sqrt(q / p), np.sqrt(p / q)
        dd = np.concatenate([rqp[:, None] * e + f, rpq[:, None] * f + e], axis=1)  # ∂D
        w = -2 * c                                                                 # E = w·φ + …
        gphi = 2 * (nd * D[:, None] - n[:, None] * dd) / (D ** 2)[:, None]
        gef = w[:, None] * gphi
        g = np.zeros((self.N, 3))
        g[:-2] -= gef[:, :3]
        g[1:-1] += gef[:, :3] - gef[:, 3:]
        g[2:] += gef[:, 3:]
        if orden == 1:
            return E, g, None
        m = len(c)
        # ∂²n: solo los bloques cruzados, ∓[a]×.
        ax = np.zeros((m, 3, 3))
        ax[:, 0, 1], ax[:, 0, 2], ax[:, 1, 2] = -a[:, 2], a[:, 1], -a[:, 0]
        ax[:, 1, 0], ax[:, 2, 0], ax[:, 2, 1] = a[:, 2], -a[:, 1], a[:, 0]
        nn = np.zeros((m, 6, 6))
        nn[:, :3, 3:] = -ax
        nn[:, 3:, :3] = ax
        # ∂²D.
        DD = np.zeros((m, 6, 6))
        DD[:, :3, :3] = rqp[:, None, None] * (_I3 - e[:, :, None] * e[:, None, :] / p[:, None, None])
        DD[:, 3:, 3:] = rpq[:, None, None] * (_I3 - f[:, :, None] * f[:, None, :] / q[:, None, None])
        DD[:, :3, 3:] = _I3 + e[:, :, None] * f[:, None, :] / sq[:, None, None]
        DD[:, 3:, :3] = _I3 + f[:, :, None] * e[:, None, :] / sq[:, None, None]
        cruzado = nd[:, :, None] * dd[:, None, :]
        H = 2 * (nn / D[:, None, None]
                 - (cruzado + np.swapaxes(cruzado, 1, 2)) / (D ** 2)[:, None, None]
                 - n[:, None, None] * DD / (D ** 2)[:, None, None]
                 + 2 * n[:, None, None] * dd[:, :, None] * dd[:, None, :] / (D ** 3)[:, None, None])
        H *= w[:, None, None]
        M = np.zeros((6, 9))
        M[:3, :3], M[:3, 3:6] = -_I3, _I3
        M[3:, 3:6], M[3:, 6:] = -_I3, _I3
        B = np.einsum("ki,nkl,lj->nij", M, H, M)
        return E, g, 0.5 * (B + np.swapaxes(B, 1, 2))

    def peso(self, x, orden: int = 2):
        X = _forma(x, self.N)
        E = float(self.peso_nodo @ X[:, 2])
        if orden == 0:
            return E, None, None
        g = np.zeros((self.N, 3))
        g[:, 2] = self.peso_nodo
        return E, g, None

    # --- Todo junto ---

    def evaluar(self, x, orden: int = 2, proyectar: bool = False):
        """La energía, su gradiente (3N,) y su Hessiano disperso (3N × 3N, CSR), según `orden`
        (0, 1 o 2). Con `proyectar`, el Hessiano queda semidefinido positivo."""
        Es, gs, Bs = self.estiramiento(x, orden, proyectar)
        con_memoria = self.curvatura is not None
        # Con memoria, la flexión y la memoria se proyectan juntas: son una sola energía.
        Eb, gb, Bb = self.flexion(x, orden, proyectar and not con_memoria)
        Ep, gp, _ = self.peso(x, orden)
        E = Es + Eb + Ep
        if con_memoria and math.isfinite(E):
            Em, gm, Bm = self.memoria(x, orden)
            E += Em
            if orden and math.isfinite(E):
                gb = gb + gm
                if orden == 2:
                    Bb = Bb + Bm
                    if proyectar:
                        Bb = proyectar_psd(Bb)
        if orden == 0 or not math.isfinite(E):
            return (E, None, None) if orden else E
        g = (gs + gb + gp).ravel()
        if orden == 1:
            return E, g, None
        return E, g, self.hessiano_de_bloques(Bs, Bb)

    def energia(self, x) -> float:
        return self.evaluar(x, orden=0)

    def hessiano_de_bloques(self, Bs, Bb) -> sp.csr_matrix:
        datos = np.zeros(len(self._indices))
        np.add.at(datos, self._lugar, np.concatenate([Bs.ravel(), Bb.ravel()]))
        n = 3 * self.N
        return sp.csr_matrix((datos, self._indices, self._indptr), shape=(n, n))


def proyectar_psd(B: np.ndarray) -> np.ndarray:
    """Cada bloque simétrico de B (n, k, k) con sus autovalores negativos llevados a cero."""
    B = 0.5 * (B + np.swapaxes(B, 1, 2))
    lam, V = np.linalg.eigh(B)
    if np.all(lam >= 0):
        return B
    lam = np.maximum(lam, 0.0)
    return np.einsum("nik,nk,njk->nij", V, lam, V)


def _forma(x, N: int) -> np.ndarray:
    return np.asarray(x, float).reshape(N, 3)


# --- El marco material (para el render, T15g) ---

def transportar(t0, t1, v):
    """v llevado del tramo con dirección unitaria t0 al de t1 por la rotación más corta (el
    transporte paralelo discreto). Si t1 = −t0, la rotación no es única y v queda igual."""
    b = np.cross(t0, t1)
    s = float(np.linalg.norm(b))
    c = float(np.dot(t0, t1))
    if s < 1e-15:
        return np.array(v, float)
    k = b / s
    return v * c + np.cross(k, v) * s + k * float(np.dot(k, v)) * (1 - c)


def marco_paralelo(X, d1_inicial=None):
    """El marco material sin torsión de cada tramo de X (N, 3): las direcciones t (N − 1, 3) y
    los vectores d1 y d2, perpendiculares a t, llevados de un tramo al siguiente por transporte
    paralelo. Es el marco de una cuerda redonda que puede girar sobre su eje (ver arriba). Sin
    `d1_inicial`, d1 empieza perpendicular al primer tramo, lo más cerca de +z que se pueda."""
    X = np.asarray(X, float)
    d = np.diff(X, axis=0)
    t = d / np.linalg.norm(d, axis=1)[:, None]
    ref = np.array([0.0, 0.0, 1.0]) if d1_inicial is None else np.asarray(d1_inicial, float)
    a = ref - t[0] * np.dot(ref, t[0])
    if np.linalg.norm(a) < 1e-9:
        a = np.array([1.0, 0.0, 0.0]) - t[0] * t[0, 0]
    d1 = np.empty_like(t)
    d1[0] = a / np.linalg.norm(a)
    for i in range(1, len(t)):
        v = transportar(t[i - 1], t[i], d1[i - 1])
        v -= t[i] * np.dot(v, t[i])
        d1[i] = v / np.linalg.norm(v)
    return t, d1, np.cross(t, d1)
