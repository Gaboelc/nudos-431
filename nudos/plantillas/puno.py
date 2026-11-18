"""Plantilla del puño de mono, sin anfitrión: se ata en los dedos y no lleva bola en el centro.

El método es el del diseño de la tanda 4 en tasks/plan.md («El puño de mono»). Con el chicote
se dan `vueltas` vueltas alrededor de dos dedos parados (el primer juego, alrededor de z); el
chicote pasa entre los dedos y da otras tantas alrededor de las primeras, por la mitad (el
segundo, alrededor de x); después pasa por dentro de las primeras y da otras tantas alrededor de
las segundas (el tercero, alrededor de y). Se sacan los dedos, se hace un nudo simple en el
chicote, se mete en el centro y se aprieta.

Cada juego es una banda de vueltas paralelas sobre una superficie alrededor del centro del puño:
un elipsoide aplastado mientras está suelto, como lo dejan los dedos, y una esfera al apretarlo.
Cada juego queda encima de otro en dos caras opuestas y debajo del tercero en otras dos: el
segundo sobre el primero en ±y, el tercero sobre el segundo en ±z y el primero sobre el tercero
en ±x. Una vuelta va un diámetro (CAPA) más lejos del centro donde pasa por encima.

Los cruces se buscan en el puño desenrollado como un globo terráqueo: cada punto de las vueltas
se mira desde el centro del puño, su dirección da una longitud y una latitud alrededor de un polo
que pasa por dos esquinas opuestas por donde no pasa nada, y encima es lo más lejos del centro.
El nudo simple se busca desde arriba, como en la mesa. Entre zonas no se buscan.

Como en el refuerzo de cabo, la plantilla traza la cuerda de cada hito entera, porque meter el
nudo y apretar cambian la cuerda desde el chicote hacia atrás y el puño entero.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .trazo import MESA, TrazoDePaso

NUMEROS = {3: "tres", 4: "cuatro"}
_CAMPOS = {"tipo", "vueltas"}

# Zonas: las vueltas, en el mapa del puño; el nudo simple dentro del puño, desde arriba; y lo que
# va de una zona a otra (el chicote que entra al centro, lo que sale del puño y cae), sin mapa.
ESFERA, CENTRO, FUERA = 10, 11, 12

# Medidas en diámetros de cuerda; ver el diseño en tasks/plan.md.
PASO_VUELTA = 1.1      # entre dos vueltas vecinas de un juego
CAPA = 1.05            # cuánto más lejos del centro va una vuelta donde pasa por encima
HOLGURA = 0.9          # más allá de la vuelta de afuera del otro juego, la cara sigue entera
RADIO = {3: 5.5, 4: 6.5}           # apretado: la distancia del centro a la capa de adentro
# Suelto, en los dedos: cada juego es una vuelta redondeada alrededor de lo que rodea.
ESQUINA = 2.5          # radio de las esquinas de las vueltas del segundo y el tercer juego
HOLGURA_A = 3.0        # del tercer juego a los costados del primero, entre los dedos
DEDO_RADIO = 1.3       # el radio de un dedo, en diámetros de cuerda
DEDO_LUZ = 1.0         # del eje de la cuerda del tercer juego a un dedo
DEDO_SOBRE = 2.5       # cuánto sobresalen los dedos por encima del puño
CAMBIO = math.radians(30)          # cuánto se prolongan los dos juegos en un cambio de juego
CAMBIO_DEDOS = (math.radians(30), math.radians(50))   # en los dedos: el que termina y el que empieza
ARCO = 1.5                         # radio con que la cuerda deja una vuelta para salir o entrar
RECTA_MIN = 0.6                    # lo menos que va derecho el chicote antes del nudo del centro
SUELTO = (1.55, 1.33, 1.1)         # suelto: los semiejes, en veces el radio apretado
PASO = 0.1             # cada cuánto se traza la cuerda
PASO_CONTROL = 0.3     # cada cuánto se toma un punto de control
R_MAPA = 3.0           # escala del puño desenrollado
R_CARA = 6.0           # el radio con que se mide dónde está un cruce en su cara
LEJOS_CARA = 100.0     # cuánto se corren unas de otras las caras al guardar dónde está un cruce
SALE = 2.5             # cuánto se aleja del puño lo que sale de él antes de caer a la mesa
CAE = 3.0              # cuánto avanza hacia afuera mientras cae a la mesa
SOBRE_LA_MESA = 6.0    # cuánto sigue por la mesa
FIRME_MESA = 8.0       # el largo del firme sobre la mesa

# El nudo simple: un nudo de trébol (2, 3) sobre un toro, abierto donde está más afuera.
NUDO_R, NUDO_r = 1.6, 0.6
NUDO_ABRE = 0.7        # medio ángulo, en radianes, del tramo del trébol que se abre
NUDO_CURVA = 1.4       # radio con que las dos patas salen del nudo
NUDO_ENTRA = 2.0       # el largo de la pata que entra, derecha
NUDO_COLA = 1.0        # el largo de la punta, derecha

# Los juegos: su eje e, la dirección de las caras donde va encima (u) y donde va debajo (v).
_X, _Y, _Z = np.eye(3)
EJES = {"A": (_Z, _X, _Y), "B": (_X, _Y, _Z), "C": (_Y, _Z, _X)}
ENCIMA = {("B", "A"), ("C", "B"), ("A", "C")}   # (el de encima, el de abajo)
LETRA = {1: "A", 2: "B", 3: "C"}

# Las esquinas del puño, donde se juntan tres caras y no pasa ninguna banda. El firme entra al
# primer juego en K0, el primer juego pasa al segundo en K1, el segundo al tercero en K2 y el
# tercero termina en K3, de donde el chicote entra al centro. El polo del mapa va por las dos
# esquinas que no usa nada.
_s3 = 1 / math.sqrt(3)
K0, K1, K2, K3 = (np.array(v) * _s3 for v in ((1, -1, -1), (1, -1, 1), (-1, -1, 1), (-1, 1, 1)))
POLO = np.array([1.0, 1.0, 1.0]) * _s3
# Cada juego empieza en un borde de su banda (signo de β) y en un ángulo φ, y avanza en sentido σ.
# φ se mide desde u hacia v. Así cada juego empieza en la esquina donde terminó el anterior.
INICIO = {"A": (-1, -math.pi / 4, -1), "B": (+1, 3 * math.pi / 4, -1), "C": (-1, -math.pi / 4, -1)}

# Hacia dónde van por la mesa el firme y lo que sigue de cada juego.
FIRME_HACIA = np.array([0.7, -0.7])
SIGUE_HACIA = {"A": (0.0, -1.0), "B": None, "C": (-0.4, 1.0)}


@dataclass(frozen=True)
class PunoDeMono:
    vueltas: int    # las de cada juego

    tipo = "puno-de-mono"
    ANFITRION = None
    # El error común que sabe construir, con el primer hito desde el que se ve: el tercer juego
    # pasa por fuera del primero, en vez de por dentro.
    VARIANTES = {"tercero-por-fuera": "vuelta-3-1"}
    # La cuerda va del firme al chicote, así que no se da vuelta para la escena: nombres() dice
    # qué nombres lleva cada paso.
    CON_FIRME: tuple[str, ...] = ()
    # Los hitos en que el chicote está escondido en el centro: solo llevan «Firme».
    SOLO_FIRME = ("apretar",)

    @classmethod
    def leer(cls, datos: dict, falla) -> PunoDeMono:
        sobran = set(datos) - _CAMPOS
        if sobran:
            raise falla(f"campos desconocidos: {', '.join(sorted(sobran))}")
        v = datos.get("vueltas")
        if not isinstance(v, int) or isinstance(v, bool) or v not in NUMEROS:
            raise falla(f"«vueltas» es un número entero de {min(NUMEROS)} a {max(NUMEROS)}")
        return cls(vueltas=v)

    def hitos(self) -> dict[str, int]:
        """Los valores de `hasta`, en orden. `juego-<j>` es lo mismo que su última vuelta."""
        out, k = {}, 0
        for j in (1, 2, 3):
            for i in range(1, self.vueltas + 1):
                k += 1
                out[f"vuelta-{j}-{i}"] = k
            out[f"juego-{j}"] = k
        out["apretar"] = k + 1
        return out

    def medidas(self) -> dict[str, str]:
        return {"vueltas": NUMEROS[self.vueltas]}

    def nombres(self, hito: str) -> list[str]:
        """Los nombres de la imagen del hito: «Firme» siempre, y «Chicote» mientras se ve."""
        return ["firme"] if hito in self.SOLO_FIRME else ["firme", "chicote"]

    def voltear(self, r):
        """El puño terminado, visto por detrás (nudos/imprimir.py): ver voltear()."""
        return voltear(self, r)

    def dedos(self, hito: str) -> dict | None:
        """Los dedos del hito para render/escena.js, o None: van en las vueltas y no al apretar,
        porque antes se sacan."""
        return None if hito == "apretar" else _dedos(self.vueltas).datos()


# --------------------------------------------------------------------------
# Herramientas
# --------------------------------------------------------------------------
def _unit(v) -> np.ndarray:
    v = np.asarray(v, float)
    return v / max(float(np.linalg.norm(v)), 1e-12)


def _hermite(P0, T0, P1, T1, paso: float = PASO, fuerza: float = 1.0) -> np.ndarray:
    """Curva de Hermite de P0 a P1 con las tangentes unitarias T0 y T1, muestreada cada `paso`
    más o menos. No incluye P0."""
    P0, P1 = np.asarray(P0, float), np.asarray(P1, float)
    d = float(np.linalg.norm(P1 - P0)) * fuerza
    n = max(3, int(math.ceil(1.3 * float(np.linalg.norm(P1 - P0)) / paso)) + 1)
    t = np.linspace(0.0, 1.0, n)[1:, None]
    return ((2 * t ** 3 - 3 * t ** 2 + 1) * P0 + (t ** 3 - 2 * t ** 2 + t) * d * _unit(T0)
            + (-2 * t ** 3 + 3 * t ** 2) * P1 + (t ** 3 - t ** 2) * d * _unit(T1))


def _recta(a, b, paso: float = PASO) -> np.ndarray:
    """De a a b, sin incluir a."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = max(2, int(math.ceil(np.linalg.norm(b - a) / paso)) + 1)
    return (a + np.linspace(0, 1, n)[:, None] * (b - a))[1:]


def _suave(x) -> np.ndarray:
    """De 0 a 1 entre x = 0 y x = 1, con la primera y la segunda derivada nulas en los bordes."""
    x = np.clip(x, 0.0, 1.0)
    return x ** 3 * (x * (6 * x - 15) + 10)


def _largo(P) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])


# --------------------------------------------------------------------------
# La forma del puño
# --------------------------------------------------------------------------
class Forma:
    """La superficie del puño en un hito: los semiejes S (en x, y, z) de la capa de adentro."""

    def __init__(self, n: int, apretado: bool, variante: str | None = None):
        rho = RADIO[n]
        self.n, self.variante = n, variante
        self.S = np.full(3, rho) if apretado else rho * np.array(SUELTO)
        self.prolonga = (CAMBIO, CAMBIO)

    def radio(self, d) -> np.ndarray:
        """La distancia del centro a la capa de adentro en las direcciones unitarias d."""
        d = np.atleast_2d(d)
        return 1.0 / np.sqrt(((d / self.S) ** 2).sum(1))

    def _eje(self, w) -> float:
        return float(self.S[int(np.argmax(np.abs(w)))])

    def dbeta(self, j: str) -> float:
        """El ángulo entre dos vueltas vecinas del juego j."""
        e, u, v = EJES[j]
        return PASO_VUELTA / min(self._eje(u), self._eje(v))

    def capa(self, j: str, phi) -> np.ndarray:
        """Cuánto más lejos del centro va el juego j en el ángulo φ: CAPA en las caras donde va
        encima (±u), 0 donde va debajo (±v) y una rampa suave entre unas y otras."""
        phi = np.asarray(phi, float)
        if self.variante == "tercero-por-fuera":
            # El tercero va por fuera de todo, y el primero, debajo de todo.
            if j == "C":
                return np.full(phi.shape, CAPA)
            if j == "A":
                return np.zeros(phi.shape)
        e, u, v = EJES[j]
        ancho = (self.n / 2 - 1 / 8) * PASO_VUELTA + HOLGURA
        s_o, s_u = ancho / self._eje(u), ancho / self._eje(v)
        psi = np.abs(np.mod(phi + math.pi / 2, math.pi) - math.pi / 2)   # desde la cara ±u
        return CAPA * _suave((math.pi / 2 - s_u - psi) / (math.pi / 2 - s_u - s_o))

    def punto(self, j: str, phi, beta) -> np.ndarray:
        """Puntos del juego j (relativos al centro) en los ángulos φ (alrededor del eje, desde u
        hacia v) y β (hacia el eje)."""
        e, u, v = EJES[j]
        phi, beta = np.atleast_1d(phi), np.atleast_1d(beta)
        d = (np.cos(beta)[:, None] * (np.cos(phi)[:, None] * u + np.sin(phi)[:, None] * v)
             + np.sin(beta)[:, None] * e)
        return d * (self.radio(d) + self.capa(j, phi))[:, None]

    def en(self, j: str, t) -> np.ndarray:
        """Los puntos de la hélice del juego j después de recorrer los ángulos t: de un borde de
        su banda (t = 0) al otro (t = 2π·n), con n vueltas de Δβ cada una. Fuera de ese tramo
        sigue igual, para los cambios de juego."""
        signo, phi0, sigma = INICIO[j]
        t = np.atleast_1d(np.asarray(t, float))
        m = self.n / 2 * self.dbeta(j)
        return self.punto(j, phi0 + sigma * t, signo * m - signo * 2 * m * t / (2 * math.pi * self.n))

    def helice(self, j: str, hasta: float | None = None) -> tuple[np.ndarray, np.ndarray]:
        """Las vueltas del juego j hasta el ángulo recorrido `hasta` (por omisión, todas).
        Devuelve los puntos y la vuelta de cada uno (desde 1)."""
        hasta = 2 * math.pi * self.n if hasta is None else hasta
        n_pts = max(3, int(math.ceil(hasta * float(self.S.max() + CAPA) / PASO)) + 1)
        t = np.linspace(0.0, hasta, n_pts)
        vuelta = np.minimum(np.floor(t / (2 * math.pi)).astype(int) + 1, self.n)
        vuelta[-1] = max(1, int(math.ceil(hasta / (2 * math.pi) - 1e-9)))
        return self.en(j, t), vuelta

    def cambio(self, j0: str, j1: str) -> np.ndarray:
        """El cambio del juego j0 al j1, por la esquina: una mezcla suave de los dos juegos
        prolongados CAMBIO más allá de donde terminan y empiezan, que va del final del primero
        al principio del segundo. Sin las dos puntas."""
        total = 2 * math.pi * self.n
        largo = float(np.linalg.norm(self.en(j1, 0.0)[0] - self.en(j0, total)[0])) * 2
        s = np.linspace(0.0, 1.0, max(8, int(math.ceil(largo / PASO)) + 1))[1:-1]
        w = _suave(s)[:, None]
        a, b = self.prolonga
        return (1 - w) * self.en(j0, total + a * s) + w * self.en(j1, -b * (1 - s))

    def salida(self, j: str, t: float, adentro: bool = False) -> tuple[np.ndarray, np.ndarray]:
        """La cuerda que termina en el ángulo t del juego j, entre dos caras, se dobla hacia afuera
        del puño (o, `adentro`, hacia el centro) en un arco de radio ARCO, sin pasar sobre nada ni
        bajo nada. Devuelve el arco (sin su primer punto) y hacia dónde sigue derecha."""
        E, E2 = self.en(j, [t, t + 0.01])
        return _doblar(E, _unit(E2 - E), _unit(E) * (-1.0 if adentro else 1.0))


def _polar(phi, a: float, b: float, rc: float) -> np.ndarray:
    """La distancia del centro al borde de un rectángulo de medios lados a (a lo largo de u) y
    b (de v) con las esquinas redondeadas con radio rc, en la dirección φ (desde u hacia v)."""
    c, s = np.abs(np.cos(phi)), np.abs(np.sin(phi))
    pa, pb = a - rc, b - rc                 # el centro de la esquina
    t_lado = np.where(c > 1e-12, a / np.maximum(c, 1e-12), np.inf)
    t_arriba = np.where(s > 1e-12, b / np.maximum(s, 1e-12), np.inf)
    dp = c * pa + s * pb
    t_esq = dp + np.sqrt(np.maximum(dp ** 2 - pa ** 2 - pb ** 2 + rc ** 2, 0.0))
    return np.where(t_lado * s <= pb, t_lado, np.where(t_arriba * c <= pa, t_arriba, t_esq))


class FormaDedos(Forma):
    """El puño suelto, en los dedos, que van parados en x = ±dedo_x. Cada juego es una vuelta
    redondeada en su plano, alrededor de lo que rodea, y sus vueltas avanzan 1,1 a lo largo de
    su eje: el primero rodea los dos dedos (un óvalo de radio ra); el segundo abraza al primero
    por la mitad, entre los dedos, ESQUINA más afuera que sus vueltas; el tercero abraza al
    segundo por arriba y por abajo, entre los dedos y por dentro del primero. Los cruces son los
    mismos que en el puño apretado, cada juego encima en sus dos caras, porque cada vuelta va
    lejos de la que tapa."""

    def __init__(self, n: int, variante: str | None = None):
        self.n, self.variante = n, variante
        m = self.m = n / 2 * PASO_VUELTA     # lo más lejos que va una vuelta del medio de su banda
        ra = m + HOLGURA_A
        self.dedo_x = _dedo_x(n)
        ax = self.dedo_x + ra
        # (medio lado a lo largo de u, a lo largo de v, radio de las esquinas)
        self.formas = {"A": (ax, ra, ra), "B": (ra + ESQUINA, m + ESQUINA, ESQUINA),
                       "C": (m + 2 * ESQUINA, m + ESQUINA, ESQUINA)}
        if variante == "tercero-por-fuera":
            # El tercero, por fuera del primero: alrededor de sus puntas, en x = ±ax.
            self.formas["C"] = (m + 2 * ESQUINA, ax + ESQUINA, ESQUINA)
        self.S = np.array([ax, ra + ESQUINA, m + 2 * ESQUINA])
        self.prolonga = CAMBIO_DEDOS

    def en(self, j: str, t) -> np.ndarray:
        signo, phi0, sigma = INICIO[j]
        e, u, v = EJES[j]
        t = np.atleast_1d(np.asarray(t, float))
        phi = phi0 + sigma * t
        avance = signo * self.m - signo * 2 * self.m * t / (2 * math.pi * self.n)
        r = _polar(phi, *self.formas[j])
        return ((r * np.cos(phi))[:, None] * u + (r * np.sin(phi))[:, None] * v
                + avance[:, None] * e)

    def salida(self, j: str, t: float, adentro: bool = False) -> tuple[np.ndarray, np.ndarray]:
        """Como en el puño apretado, pero el tercer juego, que termina cada vuelta bajando junto a
        un dedo, sale hacia atrás, a lo largo de su eje, por donde todavía no hay vueltas."""
        E, E2 = self.en(j, [t, t + 0.01])
        hacia = np.array([0.0, 1.0, 0.0]) if j == "C" and not adentro else _unit(E)
        return _doblar(E, _unit(E2 - E), hacia * (-1.0 if adentro else 1.0))


def _dedo_x(n: int) -> float:
    """Dónde van los dedos, en x = ±_dedo_x: a DEDO_LUZ del tercer juego, que pasa entre ellos."""
    return n / 2 * PASO_VUELTA + ESQUINA + DEDO_LUZ + DEDO_RADIO


def _dedos(n: int) -> "Dedos":
    """Los dos dedos, parados sobre la mesa, más altos que el puño suelto."""
    m = n / 2 * PASO_VUELTA
    alto = 0.5 + 2 * (m + 2 * ESQUINA) + DEDO_SOBRE
    return Dedos(_dedo_x(n), DEDO_RADIO, alto)


@dataclass(frozen=True)
class Dedos:
    """Los dos dedos en que se ata el puño: dos cilindros parados sobre la mesa en x = ±x,
    y = 0, de la mesa hasta `alto`, con la punta redonda. La cuerda no puede entrar en ellos."""
    x: float
    radio: float
    alto: float

    def _distancia(self, X) -> tuple[np.ndarray, np.ndarray]:
        """La distancia de cada punto al eje de su dedo más cercano y hacia dónde salir."""
        lado = np.where(X[:, 0] >= 0, 1.0, -1.0)
        tope = self.alto - self.radio
        z = np.clip(X[:, 2], 0.0, tope)
        eje = np.column_stack([lado * self.x, np.zeros(len(X)), z])
        d = X - eje
        return np.linalg.norm(d, axis=1), d

    def empujar(self, X, libre) -> None:
        r = self.radio + 0.5
        dist, d = self._distancia(X)
        m = libre & (dist < r)
        if m.any():
            u = d[m] / np.maximum(dist[m], 1e-9)[:, None]
            X[m] = X[m] - d[m] + u * r

    def penetracion(self, X) -> float:
        dist, _ = self._distancia(X)
        return float(max(0.0, (self.radio + 0.5 - dist).max()))

    def datos(self) -> dict:
        """Lo que necesita render/escena.js para dibujarlos."""
        return {"x": [-self.x, self.x], "y": 0.0, "radio": self.radio, "alto": self.alto}


# --------------------------------------------------------------------------
# La cuerda de cada hito
# --------------------------------------------------------------------------
class _Rope:
    """Una cuerda que se va armando: puntos relativos o absolutos, con su zona y su pieza, y
    marcas con nombre."""

    def __init__(self):
        self.P, self.Z, self.pieza, self.marcas = [], [], [], {}

    def agregar(self, P, zona: int, pieza: str) -> None:
        P = np.atleast_2d(np.asarray(P, float))
        if self.P and len(P) and np.linalg.norm(P[0] - self.P[-1][-1]) < 1e-9:
            P = P[1:]
        if len(P):
            self.P.append(P)
            self.Z.append(np.full(len(P), zona))
            self.pieza.append(np.array([pieza] * len(P), dtype=object))

    @property
    def fin(self) -> np.ndarray:
        return self.P[-1][-1]

    def n(self) -> int:
        return sum(len(p) for p in self.P)

    def marcar(self, nombre: str) -> None:
        self.marcas[nombre] = self.n() - 1

    def listo(self):
        return (np.vstack(self.P), np.concatenate(self.Z), np.concatenate(self.pieza),
                dict(self.marcas))


def _nudo_simple():
    """El nudo simple en su marco, centrado en el origen y acostado: un trébol (2, 3) sobre un
    toro, abierto en un tramo de afuera, con las dos patas que salen de él en un arco de radio
    NUDO_CURVA y siguen derechas hacia afuera. Devuelve la pata que entra (desde su punta de
    afuera, sin el primer punto del trébol), el trébol, la punta y hacia dónde mira la pata que
    entra. La pata que entra es derecha hasta su índice NUDO_ENTRA_PUNTOS y después, el arco."""
    R, r, abre, rf = NUDO_R, NUDO_r, NUDO_ABRE, NUDO_CURVA
    th = np.linspace(abre, 4 * math.pi - abre, int(math.ceil(4 * math.pi * (R + r) / PASO)) + 1)
    rho = R + r * np.cos(1.5 * th)
    trebol = np.column_stack([rho * np.cos(th), rho * np.sin(th), r * np.sin(1.5 * th)])
    k = int(math.ceil(math.pi / 2 * rf / PASO)) + 1

    def afuera(P, T):
        rr = _unit(np.r_[P[:2], 0.0])
        return _unit(rr - (rr @ T) * T)

    # La pata que entra: derecha hacia el trébol, y un arco hasta su primer punto.
    P, T = trebol[0], _unit(trebol[1] - trebol[0])
    n = afuera(P, T)
    phi = np.linspace(math.pi / 2, 0.0, k)[:-1, None]
    arco = P + rf * n - rf * (n * np.cos(phi) + T * np.sin(phi))
    recta = _recta(arco[0] + NUDO_ENTRA * n, arco[0])[:-1]
    entrada = np.vstack([(arco[0] + NUDO_ENTRA * n)[None], recta, arco])
    assert len(entrada) - len(arco) == len(recta) + 1
    # La punta: un arco desde el último punto del trébol y derecha hacia afuera.
    P, T = trebol[-1], _unit(trebol[-1] - trebol[-2])
    nt = afuera(P, T)
    phi = np.linspace(0.0, math.pi / 2, k)[1:, None]
    arco = P + rf * nt - rf * (nt * np.cos(phi) - T * np.sin(phi))
    cola = np.vstack([arco, _recta(arco[-1], arco[-1] + NUDO_COLA * nt)])
    return entrada, trebol, cola, n


def _giro_z(ang: float) -> np.ndarray:
    c, s = math.cos(ang), math.sin(ang)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def _giro_del_nudo(g) -> np.ndarray:
    """El giro del nudo simple como matriz: un ángulo alrededor de z, o ya una matriz."""
    return _giro_z(g) if np.isscalar(g) else np.asarray(g, float)


def _giro_hacia(u, K) -> np.ndarray:
    """El giro que lleva la dirección u del marco del nudo simple a K, con la cara de arriba del
    nudo lo más hacia arriba que se puede."""
    x = _unit(K)
    z = _unit(np.array([0.0, 0.0, 1.0]) - x[2] * x)
    return np.column_stack([x, np.cross(z, x), z]) @ _giro_z(-math.atan2(u[1], u[0]))


class Cuerda:
    """Las cuerdas de un puño de mono, una por hito, con su secuencia de cruces.

    `secuencias` da la secuencia del método en cada hito y `alias` los hitos que equivalen a
    otro (`juego-<j>`). `trazo(hito, previo)` da los puntos de control del paso. Con `variante`,
    solo los hitos del tercer juego; con `solo`, solo esos hitos."""

    def __init__(self, p: PunoDeMono, variante: str | None = None, solo: tuple[str, ...] | None = None):
        if variante is not None and variante not in p.VARIANTES:
            raise ValueError(f"el puño de mono no tiene la variante {variante}")
        self.p, self.variante = p, variante
        n = p.vueltas
        self.alias = {f"juego-{j}": f"vuelta-{j}-{n}" for j in (1, 2, 3)}
        hitos = p.hitos()
        self.orden = [h for h in sorted(hitos, key=hitos.get) if h not in self.alias]
        if variante is not None:
            self.orden = [h for h in self.orden if h.startswith("vuelta-3-")]
        if solo is not None:
            self.orden = [h for h in self.orden if h in solo]
        self._etiquetas: dict[tuple, str] = {}
        self._pasos = {h: self._paso(h) for h in self.orden}
        self.secuencias = {h: self._pasos[h]["secuencia"] for h in self.orden}
        for a, h in self.alias.items():
            if h in self.secuencias:
                self.secuencias[a] = self.secuencias[h]

    # --- Las vueltas --------------------------------------------------------------------
    def _forma(self, hito: str) -> Forma:
        if hito == "apretar":
            return Forma(self.p.vueltas, True, self.variante)
        return FormaDedos(self.p.vueltas, self.variante)

    def _puno(self, hito: str, f: Forma) -> _Rope:
        """Las vueltas del hito, relativas al centro, desde la primera hasta la última del hito,
        con los cambios de juego. Sin el firme ni lo que sigue."""
        n = self.p.vueltas
        if hito.startswith("vuelta-"):
            j_fin, k_fin = (int(x) for x in hito.split("-")[1:])
        else:
            j_fin, k_fin = 3, n
        c = _Rope()
        for j in range(1, j_fin + 1):
            letra = LETRA[j]
            k = n if j < j_fin else k_fin
            H, vuelta = f.helice(letra, 2 * math.pi * k)
            if j > 1:
                # El cambio de juego, por la esquina: del final del juego anterior al principio de
                # este, sobre la superficie del puño.
                c.agregar(f.cambio(LETRA[j - 1], letra), ESFERA, f"cambio-{j}")
            c.marcar(f"inicio-{letra}")
            for i in range(1, k + 1):
                c.agregar(H[vuelta == i], ESFERA, f"{letra}{i}")
                c.marcar(f"{letra}{i}")
        return c

    # --- Un hito ------------------------------------------------------------------------
    def _paso(self, hito: str) -> dict:
        f = self._forma(hito)
        n = self.p.vueltas
        c = self._puno(hito, f)
        if hito.startswith("vuelta-"):
            j_fin, k_fin = (int(x) for x in hito.split("-")[1:])
        else:
            j_fin, k_fin = 3, n
        t_fin = 2 * math.pi * k_fin
        dentro = hito == "apretar"
        nudo = None
        if dentro:
            # Después del tercer juego, el chicote entra al centro donde termina la última vuelta,
            # entre dos caras, donde no tiene nada debajo. El nudo simple va en el centro, con la
            # pata que entra a lo largo de esa dirección: el nudo se corre de lado lo necesario.
            entrada, trebol, cola, u = _nudo_simple()
            arco, D = f.salida("C", t_fin, adentro=True)
            c.agregar(arco, FUERA, "chicote")
            # Dentro del puño, la pata que entra es solo su arco: la recta es el chicote.
            entrada = entrada[-int(math.ceil(math.pi / 2 * NUDO_CURVA / PASO)):]
            G = _giro_hacia(u, -D)
            S = G @ entrada[0]
            A = c.fin
            # El nudo, lo más cerca del centro, con al menos RECTA_MIN de chicote derecho.
            lam = max(float((S - A) @ D), RECTA_MIN)
            O = A + lam * D - S
            c.agregar(_recta(A, S + O), FUERA, "chicote")
            c.agregar(entrada[1:] @ G.T + O, FUERA, "chicote")
            c.marcar("nudo-inicio")
            c.agregar(trebol @ G.T + O, CENTRO, "nudo")
            c.marcar("nudo-fin")
            # Dentro del puño, la punta es solo medio arco: así no asoma entre las vueltas.
            cola = cola[:int(math.ceil(math.pi / 4 * NUDO_CURVA / PASO))]
            c.agregar(cola @ G.T + O, FUERA, "cola")
            nudo = (O, G)
        else:
            # Lo que sigue sale del puño donde termina la vuelta, entre dos caras.
            arco, D = f.salida(LETRA[j_fin], t_fin)
            c.agregar(arco, FUERA, "resto")
            A = c.fin
            lejos = float(f.radio(_unit(A))[0]) + CAPA + SALE
            c.agregar(_recta(A, A + max(lejos - float(A @ D), 1.0) * D), FUERA, "resto")
        rel, Zp, piezap, marcas = c.listo()
        # El puño se apoya en la mesa por lo que queda más abajo.
        centro = np.array([0.0, 0.0, 0.5 - float(rel[:, 2].min())])
        X = rel + centro
        # El firme: llega por la mesa por delante, a la derecha, y sube a la primera vuelta,
        # donde empieza, entre dos caras.
        firme = _firme(X[0], _unit(X[1] - X[0]), centro, f)
        partes = [(firme, _en_la_mesa(firme), _nombres("firme", len(firme))), (X, Zp, piezap)]
        marcas = {k: v + len(firme) for k, v in marcas.items()}
        marco = None if nudo is None else (centro + nudo[0], nudo[1])
        fin, T = X[-1], _unit(X[-1] - X[-2])
        if not dentro:
            # Ya fuera del puño, se aleja por encima de él y cae a la mesa.
            sigue = _alejar(fin, T, centro, f, hacia=SIGUE_HACIA[LETRA[j_fin]])
            partes.append((sigue, _en_la_mesa(sigue), _nombres("resto", len(sigue))))
        P = np.vstack([q[0] for q in partes])
        Z = np.concatenate([q[1] for q in partes])
        pieza = np.concatenate([q[2] for q in partes])
        cruces, _ = buscar(P, PASO, Z, centro, marco)
        secuencia, etiquetados = self._secuencia(P, pieza, cruces, centro)
        # Los dedos, en las vueltas; en el error no, porque el tercer juego pasaría por ellos.
        dedos = None if dentro or self.variante is not None else _dedos(n)
        return {"P": P, "Z": Z, "pieza": pieza, "marcas": marcas, "centro": centro,
                "nudo": marco, "cruces": etiquetados, "secuencia": secuencia, "dedos": dedos}

    # --- Los cruces -------------------------------------------------------------------
    def _secuencia(self, P, pieza, cruces, centro):
        """La secuencia del método: entre dos juegos, va encima el que dice ENCIMA (en la variante,
        el tercero sobre el primero); entre las demás piezas, lo que está más lejos del centro, o
        más alto en el nudo simple. Cada cruce lleva su etiqueta: la de sus dos piezas en la misma
        cara del puño, o, en el nudo simple, su número."""
        pasadas, etiquetados, en_nudo = [], [], []
        for c in cruces:
            ia = min(int(round(c.sa / PASO)), len(P) - 1)
            ib = min(int(round(c.sb / PASO)), len(P) - 1)
            a, b = str(pieza[ia]), str(pieza[ib])
            if a == "nudo" and b == "nudo":
                en_nudo.append(c)
                continue
            if _vuelta(a) and _vuelta(b) and a[0] != b[0]:
                arriba = (a[0], b[0]) in ENCIMA
                if self.variante == "tercero-por-fuera" and {a[0], b[0]} == {"A", "C"}:
                    arriba = a[0] == "C"
            else:
                arriba = float(np.linalg.norm(P[ia] - centro)) > float(np.linalg.norm(P[ib] - centro))
            d = _unit(P[ia] - centro)
            k = int(np.argmax(np.abs(d)))
            cara = ("+" if d[k] > 0 else "-") + "xyz"[k]
            clave = (a, b, cara) if a < b else (b, a, cara)
            etiqueta = self._etiquetas.setdefault(clave, str(len(self._etiquetas) + 1))
            etiquetados.append((etiqueta, clave, c))
            pasadas.append((c.sa, etiqueta + ("O" if arriba else "U")))
            pasadas.append((c.sb, etiqueta + ("U" if arriba else "O")))
        for k, c in enumerate(sorted(en_nudo, key=lambda c: c.sa)):
            ia, ib = int(round(c.sa / PASO)), int(round(c.sb / PASO))
            arriba = P[ia, 2] > P[ib, 2]
            clave = ("nudo", k)
            etiqueta = self._etiquetas.setdefault(clave, str(len(self._etiquetas) + 1))
            etiquetados.append((etiqueta, clave, c))
            pasadas.append((c.sa, etiqueta + ("O" if arriba else "U")))
            pasadas.append((c.sb, etiqueta + ("U" if arriba else "O")))
        return tuple(t for _, t in sorted(pasadas)), etiquetados

    # --- El paso ----------------------------------------------------------------------
    def trazo(self, hito: str, previo: str | None) -> TrazoDePaso:
        """Los puntos de control del paso y lo que se resalta: lo que agrega el paso."""
        hito = self.alias.get(hito, hito)
        previo = self.alias.get(previo, previo)
        if hito not in self._pasos:
            raise ValueError(f"la variante {self.variante} se ve solo en el tercer juego")
        d = self._pasos[hito]
        P, Z, marcas = d["P"], d["Z"], d["marcas"]
        k = max(1, int(round(PASO_CONTROL / PASO)))
        cambia = np.nonzero(np.diff(Z) != 0)[0]
        idx = np.array(sorted(set(range(0, len(P), k)) | set(marcas.values()) | {len(P) - 1}
                              | set(cambia.tolist()) | set((cambia + 1).tolist())))
        en = {m: int(np.searchsorted(idx, i)) for m, i in marcas.items()}
        a, b = self._resaltado(hito, previo, en)
        return TrazoDePaso(P[idx], Z[idx], b, a, marco={"centro": d["centro"], "nudo": d["nudo"],
                                                        "solido": d["dedos"]})

    def _resaltado(self, hito, previo, en) -> tuple[int | None, int]:
        """Los puntos de control donde empieza y termina el resaltado."""
        n = self.p.vueltas
        if hito == "apretar":
            return 0, 0
        j, k = (int(x) for x in hito.split("-")[1:])
        fin = en[f"{LETRA[j]}{k}"]
        if previo is None or not previo.startswith("vuelta-"):
            return en["inicio-A"], fin
        jp, kp = (int(x) for x in previo.split("-")[1:])
        return en[f"{LETRA[jp]}{kp}"], fin

    def paso(self, hito: str) -> dict:
        """La cuerda del hito antes de relajar, con sus piezas, marcas, centro y cruces."""
        return self._pasos[self.alias.get(hito, hito)]


def _vuelta(pieza: str) -> bool:
    return len(pieza) >= 2 and pieza[0] in "ABC" and pieza[1:].isdigit()


def _nombres(nombre: str, n: int) -> np.ndarray:
    return np.array([nombre] * n, dtype=object)


def _avance(z: float) -> float:
    """Cuánto avanza hacia afuera la cuerda que cae a la mesa desde la altura z: CAE, o más si
    cae de alto, para no doblarse."""
    return max(CAE, 1.3 * (z - 0.5))


def _doblar(E, T, hacia) -> tuple[np.ndarray, np.ndarray]:
    """Desde E, yendo en T, la cuerda se dobla hacia `hacia` en un arco de radio ARCO. Devuelve
    el arco (sin E) y hacia dónde sigue derecha."""
    nn = _unit(hacia - (hacia @ T) * T)
    phi = np.linspace(0.0, math.pi / 2, int(math.ceil(math.pi / 2 * ARCO / PASO)) + 1)[1:, None]
    return E + ARCO * nn - ARCO * (nn * np.cos(phi) - T * np.sin(phi)), nn


def _firme(P0, T, centro, forma: Forma) -> np.ndarray:
    """El firme hasta P0, donde empieza la primera vuelta yendo en T: visto desde P0 hacia atrás,
    se dobla hacia afuera del puño, sale derecho, cae a la mesa y sigue por ella hacia
    FIRME_HACIA. No incluye P0."""
    afuera = _unit(np.r_[(P0 - centro)[:2], 0.0])
    arco, D = _doblar(P0, -T, afuera)
    A = arco[-1]
    lejos = float(forma.radio(D)[0]) + CAPA + SALE
    recta = _recta(A, A + max(lejos - float((A - centro) @ D), 1.0) * D)
    resto = _alejar(recta[-1], D, centro, forma, hacia=FIRME_HACIA, largo=FIRME_MESA)
    return np.vstack([arco, recta, resto])[::-1]


def _en_la_mesa(P) -> np.ndarray:
    """La zona de lo que sale del puño: en la mesa, donde ya la toca; si no, sin mapa."""
    return np.where(P[:, 2] < 0.55, MESA, FUERA)


def _alejar(Q1, d, centro, forma: Forma, hacia=None, largo: float = SOBRE_LA_MESA) -> np.ndarray:
    """Desde Q1, ya fuera del puño y yendo en d, la cuerda se aleja por encima del puño hacia
    `hacia` (por omisión, hacia afuera), hasta pasar su costado; cae a la mesa y sigue por ella
    `largo`. No incluye Q1."""
    if hacia is None:
        hacia = d[:2] if np.linalg.norm(d[:2]) > 0.2 else np.array([0.0, -1.0])
    hacia = _unit(np.r_[np.asarray(hacia, float)[:2], 0.0])
    costado = float(forma.S[:2].max()) + CAPA + 0.5 + SALE
    piezas = []
    falta = costado - float((Q1 - centro) @ hacia)
    if falta > 0.5:
        Q1b = Q1 + falta * hacia
        piezas.append(_hermite(Q1, d, Q1b, hacia, fuerza=1.5))
        Q1, d = Q1b, hacia
    Q2 = np.r_[Q1[:2] + _avance(Q1[2]) * hacia[:2], 0.5]
    piezas.append(_hermite(Q1, d, Q2, hacia))
    piezas.append(_recta(Q2, Q2 + largo * hacia))
    return np.vstack(piezas)


# --------------------------------------------------------------------------
# Buscar los cruces
# --------------------------------------------------------------------------
def _marco_polo():
    e1 = _unit(np.cross(POLO, [0.0, 0.0, 1.0]))
    return e1, np.cross(POLO, e1)


def mapa_del_puno(X, centro) -> tuple[np.ndarray, np.ndarray]:
    """Cada punto en el puño desenrollado y su distancia al centro (encima es lo más lejos). El
    puño se mira desde su centro y cada dirección se proyecta desde la esquina opuesta al polo,
    por donde no pasa nada (proyección estereográfica): así el mapa no tiene costura y un cruce
    queda en el mismo lugar con el puño suelto y apretado. Escala R_MAPA."""
    D = X - centro
    r = np.linalg.norm(D, axis=1)
    d = D / np.maximum(r, 1e-9)[:, None]
    e1, e2 = _marco_polo()
    k = 2 * R_MAPA / np.maximum(1 + d @ POLO, 1e-6)
    return np.column_stack([k * (d @ e1), k * (d @ e2)]), r


def lugar_en_la_cara(d) -> tuple[float, float]:
    """Dónde está un cruce de las vueltas, para compararlo de un paso a otro: la cara del puño
    más cercana a su dirección d (desde el centro), corrida LEJOS_CARA por cada cara para que dos
    caras no se confundan, y su lugar en ella, en diámetros sobre una esfera de radio R_CARA. Así
    un cruce queda en el mismo lugar con el puño suelto y apretado."""
    d = np.asarray(d, float)
    k = int(np.argmax(np.abs(d)))
    cara = 2 * k + (0 if d[k] > 0 else 1)
    a, b = (i for i in range(3) if i != k)
    return (LEJOS_CARA * (cara + 1) + R_CARA * float(d[a]), R_CARA * float(d[b]))


def direccion_del_lugar(p) -> np.ndarray:
    """La dirección (desde el centro) del lugar de un cruce en su cara (lugar_en_la_cara)."""
    cara = int(round(p[0] / LEJOS_CARA)) - 1
    k, signo = cara // 2, (1.0 if cara % 2 == 0 else -1.0)
    a, b = (i for i in range(3) if i != k)
    d = np.zeros(3)
    d[a], d[b] = (p[0] - LEJOS_CARA * (cara + 1)) / R_CARA, p[1] / R_CARA
    d[k] = signo * math.sqrt(max(0.0, 1.0 - d[a] ** 2 - d[b] ** 2))
    return d


def _cruces_cerca(M, validos, h):
    """Como nudos.cruces.cruces_2d, pero solo compara los segmentos cercanos, con un árbol."""
    from scipy.spatial import cKDTree
    idx = np.nonzero(validos)[0]
    if len(idx) < 2:
        return []
    A, B = M[idx], M[idx + 1]
    largo = float(np.linalg.norm(B - A, axis=1).max())
    pares = cKDTree((A + B) / 2).query_pairs(largo * 1.01 + 1e-9, output_type="ndarray")
    if not len(pares):
        return []
    i, j = np.minimum(pares[:, 0], pares[:, 1]), np.maximum(pares[:, 0], pares[:, 1])
    ok = idx[j] - idx[i] >= 2
    i, j = i[ok], j[ok]
    rr, ss, qp = B[i] - A[i], B[j] - A[j], A[j] - A[i]
    rxs = rr[:, 0] * ss[:, 1] - rr[:, 1] * ss[:, 0]
    nz = np.abs(rxs) > 1e-12
    t = np.full(len(i), -1.0)
    v = np.full(len(i), -1.0)
    t[nz] = (qp[nz, 0] * ss[nz, 1] - qp[nz, 1] * ss[nz, 0]) / rxs[nz]
    v[nz] = (qp[nz, 0] * rr[nz, 1] - qp[nz, 1] * rr[nz, 0]) / rxs[nz]
    hit = nz & (t >= 0) & (t < 1) & (v >= 0) & (v < 1)
    out = []
    for k in np.nonzero(hit)[0]:
        sa, sb = (idx[i[k]] + t[k]) * h, (idx[j[k]] + v[k]) * h
        if any(abs(a - sa) < 0.3 and abs(b - sb) < 0.3 for a, b, _, _ in out):
            continue
        seno = abs(rxs[k]) / (np.linalg.norm(rr[k]) * np.linalg.norm(ss[k]))
        p = A[i[k]] + t[k] * rr[k]
        out.append((float(sa), float(sb), float(seno), (float(p[0]), float(p[1]))))
    return out


def buscar(X, h: float, zonas, centro, nudo=None):
    """Los cruces de la cuerda, en orden de su primera pasada, y la altura de sus dos pasadas: en
    las vueltas, en el puño desenrollado (encima, lo más lejos del centro); en el nudo simple
    dentro del puño y en la mesa, desde arriba (encima, lo más alto). Entre zonas no se buscan.
    Cada cruce guarda su lugar: en el mapa del puño, o, cerca del nudo simple, en el marco del
    nudo (`nudo`, su centro y su giro), para que sea el mismo en la mesa y dentro del puño."""
    from ..cruces import Cruce
    s = np.arange(len(X)) * h
    M, r = mapa_del_puno(X, centro)
    zonas_ = [(ESFERA, M, r), (MESA, X[:, :2], X[:, 2])]
    D = (X - centro) / np.maximum(r, 1e-9)[:, None]
    if nudo is not None:
        # El nudo simple, en su marco: se mira desde su cara de arriba.
        O, G = np.asarray(nudo[0], float), _giro_del_nudo(nudo[1])
        L = (X - O) @ G
        zonas_.insert(1, (CENTRO, L[:, :2], L[:, 2]))
    cruces, alturas = [], []
    for zona, mapa, alto in zonas_:
        validos = (zonas[:-1] == zona) & (zonas[1:] == zona)
        for sa, sb, seno, p in _cruces_cerca(mapa, validos, h):
            if zona == ESFERA:
                d = _unit([np.interp(sa / h, np.arange(len(X)), D[:, k]) for k in range(3)])
                p = lugar_en_la_cara(d)
            elif zona == MESA and nudo is not None:
                q = (np.r_[p, O[2]] - O) @ G
                if float(np.linalg.norm(q[:2])) < NUDO_R + NUDO_r + 1.0:
                    p = (q[0], q[1])
            cruces.append(Cruce(sa, sb, (float(p[0]), float(p[1])), seno))
            alturas.append((float(np.interp(sa, s, alto)), float(np.interp(sb, s, alto))))
    orden = sorted(range(len(cruces)), key=lambda k: cruces[k].sa)
    return [cruces[k] for k in orden], [alturas[k] for k in orden]


# --------------------------------------------------------------------------
# Por detrás
# --------------------------------------------------------------------------
def voltear(p: PunoDeMono, r):
    """El puño terminado, visto por detrás: volteado como la página de un libro, media vuelta
    alrededor de y, y apoyado en lo que queda más abajo. Es un giro rígido: los cruces se miden
    desde el centro del puño, así que la secuencia no cambia y no se relaja otra vez. El firme no
    gira con el puño: sale de él hacia afuera y vuelve a caer a la mesa."""
    from dataclasses import replace
    X = r.puntos
    ref = Cuerda(p, solo=("apretar",)).paso("apretar")
    llega = ref["P"][ref["marcas"]["inicio-A"]]
    i0 = int(np.argmin(np.linalg.norm(X[: len(X) // 2] - llega, axis=1)))
    c = ref["centro"]
    puno = X[i0:]
    Y = np.column_stack([2 * c[0] - puno[:, 0], puno[:, 1], 2 * c[2] - puno[:, 2]])
    bajar = float(Y[:, 2].min()) - 0.5
    Y[:, 2] -= bajar
    centro = np.array([c[0], c[1], c[2] - bajar])
    # El firme, desde la primera vuelta hacia atrás: se dobla hacia afuera, sale derecho del puño
    # y cae a la mesa.
    forma = Forma(p.vueltas, True)
    arco, D = _doblar(Y[0], -_unit(Y[3] - Y[0]), _unit(Y[0] - centro))
    lejos = float(forma.radio(D)[0]) + CAPA + SALE
    A = arco[-1]
    recta = _recta(A, A + max(lejos - float((A - centro) @ D), 1.0) * D)
    # Hacia atrás, como por delante, pero del otro lado: el puño se volteó sobre y.
    resto = _alejar(recta[-1], D, centro, forma, hacia=FIRME_HACIA * [-1, 1], largo=FIRME_MESA)
    firme = np.vstack([Y[:1], arco, recta, resto])[::-1]
    firme = _remuestrear(firme, r.h)[:-1]
    Y = np.vstack([firme, Y])
    return replace(r, puntos=Y, resaltado=None,
                   medidas={**r.medidas, "altura_max": float(Y[:, 2].max())})


def _remuestrear(P, paso: float) -> np.ndarray:
    s = _largo(P)
    n = max(1, int(math.ceil(s[-1] / paso)))
    g = np.linspace(0.0, s[-1], n + 1)
    return np.column_stack([np.interp(g, s, P[:, k]) for k in range(3)])
