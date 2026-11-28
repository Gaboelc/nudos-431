"""Plantilla del amarre cuadrado, sobre dos palos cruzados en ángulo recto (anfitrión «cruz»).

El método es el del diseño de T7 en tasks/historial.md: un ballestrinque en el palo de abajo,
las vueltas alrededor de los dos palos, los ahorcados entre los palos y un ballestrinque
de cierre en el palo de arriba.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .trazo import PASO

# Cuántas vueltas y ahorcados acepta la plantilla. El manual de la Tropa pide «tres o
# cuatro» de cada uno; el margen deja probar, y un número se escribe en letras.
NUMEROS = {2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis"}
_CAMPOS = {"tipo", "vueltas", "ahorcados", "inicio", "cierre"}
_CAMPOS_EXTREMO = {"poste", "lado"}
# De qué lado del otro palo puede ir un ballestrinque. El palo de abajo va hacia el fondo
# de la mesa, así que el de arriba lo parte en delante (hacia quien ata) y detrás; el de
# arriba va de izquierda a derecha, y el de abajo lo parte en izquierda y derecha.
LADOS = {"abajo": ("delante", "detras"), "arriba": ("izquierda", "derecha")}


@dataclass(frozen=True)
class Extremo:
    """Dónde va un ballestrinque: en qué palo y de qué lado del otro palo."""
    poste: str   # «abajo» o «arriba»
    lado: str    # uno de LADOS[poste]


@dataclass(frozen=True)
class AmarreCuadrado:
    vueltas: int     # alrededor de los dos palos
    ahorcados: int   # entre los palos, alrededor de las vueltas
    inicio: Extremo  # ballestrinque de inicio
    cierre: Extremo  # ballestrinque de cierre

    tipo = "amarre-cuadrado"
    ANFITRION = "cruz"
    # El error común que sabe construir, con el primer hito desde el que se ve.
    # Los ahorcados por encima del palo de arriba, en lugar de entre los palos.
    VARIANTES = {"ahorcados-por-fuera": "ahorcado-1"}
    # Hasta el ballestrinque de inicio, la parte larga de la cuerda es su firme y el chicote
    # es el extremo corto, como en el ballestrinque. Desde la primera vuelta se mueve la parte
    # larga y su punta es el chicote.
    CON_FIRME = ("inicio-1", "inicio")

    @classmethod
    def leer(cls, datos: dict, falla) -> AmarreCuadrado:
        sobran = set(datos) - _CAMPOS
        if sobran:
            raise falla(f"campos desconocidos: {', '.join(sorted(sobran))}")
        numeros = {}
        for clave in ("vueltas", "ahorcados"):
            v = datos.get(clave)
            if not isinstance(v, int) or isinstance(v, bool) or v not in NUMEROS:
                raise falla(f"«{clave}» es un número entero de {min(NUMEROS)} a {max(NUMEROS)}")
            numeros[clave] = v
        inicio = _extremo(datos.get("inicio"), "inicio", falla)
        cierre = _extremo(datos.get("cierre"), "cierre", falla)
        # Es el método del manual de la Tropa. Empezar en el palo de arriba se agrega
        # cuando un nudo lo necesite.
        if inicio.poste != "abajo" or cierre.poste != "arriba":
            raise falla("por ahora el ballestrinque de inicio va en el palo de abajo y el "
                        "de cierre en el de arriba")
        return cls(inicio=inicio, cierre=cierre, **numeros)

    def hitos(self) -> dict[str, int]:
        """Los valores de `hasta`, con su posición en la cuerda. `vueltas` es lo mismo que
        la última vuelta y `ahorcados` que el último ahorcado: así un paso que dice
        «hasta: vueltas» sigue valiendo si cambia el número de vueltas."""
        out = {"inicio-1": 0, "inicio": 1}
        k = 1
        for nombre, total in (("vuelta", self.vueltas), ("ahorcado", self.ahorcados)):
            for i in range(1, total + 1):
                k += 1
                out[f"{nombre}-{i}"] = k
            out[f"{nombre}s"] = k
        out["cierre-1"] = k + 1
        out["cierre"] = k + 2
        return out

    def medidas(self) -> dict[str, str]:
        return {"vueltas": NUMEROS[self.vueltas], "ahorcados": NUMEROS[self.ahorcados]}


def _extremo(datos, clave: str, falla) -> Extremo:
    if not isinstance(datos, dict) or set(datos) != _CAMPOS_EXTREMO:
        raise falla(f"«{clave}» lleva «poste» (abajo o arriba) y «lado»")
    poste, lado = datos["poste"], datos["lado"]
    if poste not in LADOS:
        raise falla(f"en «{clave}», «poste» es abajo o arriba")
    if lado not in LADOS[poste]:
        raise falla(f"en «{clave}», sobre el palo de {poste} «lado» es {' o '.join(LADOS[poste])}")
    return Extremo(poste, lado)


# --------------------------------------------------------------------------
# La cuerda entera
# --------------------------------------------------------------------------
# Medidas en diámetros de cuerda; ver «Cómo se hizo» de T7 en tasks/historial.md y el amarre
# tallado de T15e en tasks/plan.md.
PASO_VUELTAS = 1.1      # entre dos vueltas vecinas sobre un palo
SEPARA_INICIO = 4.0     # delante, el hueco entre la cara del palo de arriba y el ballestrinque de inicio
SEPARA_CIERRE = 4.0     # el hueco entre la cara del palo de abajo y el ballestrinque de cierre
JUNTAS = 1.04           # a media altura, lo que se apartan dos esquinas vecinas: lo justo para no tocarse
RECTA = 0.5             # cuánto se acercan las esquinas a la recta de un palo al otro (1: curva de Hermite)
LIBRE = 1.08            # lo que deja un ahorcado entre él y cualquier otro tramo
CARRIL = 1.1            # entre los carriles de un ballestrinque: dos vueltas, el firme y el chicote
RADIO_ESQUINA = 1.3     # radio con que se redondean las esquinas entre dos rectas
SEPARA_ENCIMA = 1.6     # en el error, entre dos ahorcados que pasan por encima del palo de arriba
FUERA = 1.0             # en el error, cuánto por fuera del palo de arriba empieza a subirlo un ahorcado
ABRE_FUERA = 0.5        # en el error, cuánto más lejos que el anterior empieza a subirlo cada ahorcado
BAJA_ERROR = 0.8        # en el error, cuánto más bajos que antes van los ahorcados junto al palo de abajo
DZ_BANDA = 0.45         # en banda, cuánto más alto que el anterior va cada ahorcado entre los palos
BAJO_BANDA = 0.05       # en banda, cuánto por debajo del palo de arriba pasa el último
SUBE_DESDE, SUBE_HASTA = -75.0, -20.0   # en banda, dónde sube cada uno al siguiente (grados)
SOBRE_FIRME = 1.05      # cuánto más lejos del palo de abajo que los ahorcados va el firme sobre ellos
ANG_FIRME = 75.0        # dónde va el firme alrededor del palo de abajo, sobre los ahorcados (grados)
DESPEGA = 0.6           # cuánto más allá de la primera vuelta del ballestrinque va ya sobre el palo
R_CUERDA = 0.5          # radio de la cuerda
AIRE = -2               # zona sin mapa: el firme, donde pasa por encima del ballestrinque de inicio
# Hacia dónde sale el resto de la cuerda en cada hito, sobre la mesa (antes de reflejar).
SALIDAS = {"inicio-1": (-0.6, -0.8), "inicio": (0.6, -0.8), "vuelta": (1.0, 0.0),
           "ahorcado": (1.0, -0.2), "cierre-1": (0.3, -1.0)}
# Los cuadrantes entre los palos, con el signo de x y de y: 1 detrás a la derecha, 2 detrás a
# la izquierda, 3 delante a la izquierda y 4 delante a la derecha.
CUADRANTES = {1: (1, 1), 2: (-1, 1), 3: (-1, -1), 4: (1, -1)}


@dataclass
class Cuerda:
    """La cuerda entera de un amarre, calculada una sola vez.

    `puntos` y `zonas` la recorren desde el chicote corto del ballestrinque de inicio.
    `hitos` dice en qué punto termina cada hito; `restos` da, para cada hito, los puntos de
    control de lo que sigue de la cuerda en ese paso, que sale del amarre y cae a la mesa.
    `secuencias` da la secuencia de cruces del método hasta cada hito."""
    puntos: np.ndarray
    zonas: np.ndarray
    hitos: dict[str, int]
    restos: dict[str, np.ndarray]
    secuencias: dict[str, tuple[str, ...]]
    alias: dict[str, str]   # «vueltas» y «ahorcados»: el hito al que equivalen
    quietos: np.ndarray | None = None   # los puntos que no se relajan (amarre diagonal)


class _Palos:
    """Dónde toca la cuerda a cada palo. En el de arriba, en el plano x = X y con el ángulo a
    en (y, z); en el de abajo, en el plano y = Y y con el ángulo b en (x, z). Un sentido +1 es
    antihorario en esas coordenadas."""

    def __init__(self, cruz):
        self.rb, self.zb, self.zt = cruz.rb, cruz.zb, cruz.zt
        self.centro_ar, self.centro_ab = np.array([0.0, cruz.zt]), np.array([0.0, cruz.zb])

    def arriba(self, x, a) -> np.ndarray:
        return np.array([x, self.rb * math.cos(a), self.zt + self.rb * math.sin(a)])

    def abajo(self, y, b) -> np.ndarray:
        return np.array([self.rb * math.cos(b), y, self.zb + self.rb * math.sin(b)])

    @staticmethod
    def hacia_arriba(a, sentido) -> np.ndarray:
        """Hacia dónde va la cuerda que gira en `sentido` sobre el palo de arriba, en a."""
        return sentido * np.array([0.0, -math.sin(a), math.cos(a)])

    @staticmethod
    def hacia_abajo(b, sentido) -> np.ndarray:
        return sentido * np.array([-math.sin(b), 0.0, math.cos(b)])

    def arco_arriba(self, x, a0, a1, sentido) -> np.ndarray:
        return np.array([self.arriba(x, a) for a in _angulos(a0, a1, sentido, self.rb)])

    def arco_abajo(self, y, b0, b1, sentido) -> np.ndarray:
        return np.array([self.abajo(y, b) for b in _angulos(b0, b1, sentido, self.rb)])

    def ancho_arriba(self, z) -> float:
        """Hasta dónde llega, a la altura z, lo que no puede ocupar el eje de la cuerda junto
        al palo de arriba, medido desde su eje (en y)."""
        return math.sqrt(max(0.0, self.rb ** 2 - (z - self.zt) ** 2))

    def ancho_abajo(self, z) -> float:
        return math.sqrt(max(0.0, self.rb ** 2 - (z - self.zb) ** 2))

    def tensa(self, X, Y, s_ar, s_ab, de_arriba) -> tuple[float, float]:
        """Los ángulos donde la cuerda deja un palo y llega al otro en una esquina que va del
        palo de arriba (plano x = X) al de abajo (plano y = Y), o al revés: cada punto es la
        tangente desde el otro, como en una cuerda tensa."""
        b = 0.0 if X > 0 else math.pi
        for _ in range(30):
            L = self.abajo(Y, b)
            a = _tangente(self.centro_ar, self.rb, L[[1, 2]], s_ar, saliendo=de_arriba)
            U = self.arriba(X, a)
            b = _tangente(self.centro_ab, self.rb, U[[0, 2]], s_ab, saliendo=not de_arriba)
        return a, b


def _angulos(a0, a1, sentido, r) -> np.ndarray:
    giro = ((a1 - a0) * sentido) % (2 * math.pi)
    return a0 + sentido * np.linspace(0, giro, max(2, int(giro * r / PASO) + 1))


@dataclass
class _Esquina:
    """Una esquina de una vuelta: el tramo que va de un palo al otro por fuera del cruce.

    Deja un palo y llega al otro siguiendo el arco de cada uno (`t0` y `t1`), donde una cuerda
    tensa deja el uno para ir recta al otro (_Palos.tensa), y entre los dos va en una curva
    suave (de Hermite), casi recta. A media altura se aparta `abre` de la recta, a lo largo de
    la banda que forman las esquinas de ese lado, lo justo para que dos vecinas no queden a
    menos de un diámetro (_abrir)."""
    cuadrante: int    # dónde va, entre los palos (CUADRANTES)
    sube: int         # +1 si va del palo de abajo al de arriba
    P0: np.ndarray    # donde empieza la curva, en el sentido de la cuerda
    P1: np.ndarray
    t0: np.ndarray    # hacia dónde va la cuerda en P0 y en P1
    t1: np.ndarray
    a: float          # ángulo donde toca el palo de arriba
    b: float          # ángulo donde toca el palo de abajo
    abre: np.ndarray = field(default_factory=lambda: np.zeros(3))

    def puntos(self) -> np.ndarray:
        return _hermite(self.P0, self.P1, self.t0, self.t1, self.abre, RECTA)

    def medio(self) -> np.ndarray:
        return 0.5 * (self.P0 + self.P1)


@dataclass
class _Firme:
    """El firme, del ballestrinque de inicio a la primera vuelta: los ahorcados lo cruzan, como
    a una esquina, y para la secuencia de cruces va primero entre las esquinas (_secuencias).
    Pasa por encima de ellos, sobre el palo de abajo, y llega al de arriba en el ángulo `a`."""
    a: float


def _abrir(banda: list[_Esquina]) -> float:
    """Aparta a media altura las esquinas de una banda, a lo largo de ella, lo justo para que dos
    vecinas queden a JUNTAS una de otra. Con las vueltas a PASO_VUELTAS sobre los palos, las
    esquinas tensas se juntan a media altura, porque la banda se angosta al girar de un palo
    al otro. Devuelve cuánto se apartan dos vecinas."""
    if len(banda) < 2:
        return 0.0
    tau = banda[-1].medio() - banda[0].medio()
    tau[2] = 0.0
    tau = _unit(tau)
    for s in np.arange(0.0, 1.5, 0.02):
        for i, e in enumerate(banda):
            e.abre = (i - (len(banda) - 1) / 2) * s * tau
        P = [e.puntos() for e in banda]
        if min(_distancia(P[i], P[i + 1]) for i in range(len(P) - 1)) >= JUNTAS:
            return float(s)
    raise ValueError("las esquinas de un lado no caben una junto a otra")


def _distancia(P, Q) -> float:
    """La menor distancia entre dos tramos de cuerda, en puntos."""
    return float(np.sqrt(((P[:, None, :] - Q[None, :, :]) ** 2).sum(axis=-1)).min())


def _hermite(P0, P1, t0, t1, abre=None, recta=1.0) -> np.ndarray:
    """Una curva suave de P0 a P1 que sale en la dirección t0 y llega en la t1, en puntos.
    Con `abre`, a media altura se aparta eso de la curva, sin cambiar sus extremos. Con `recta`
    menor que 1, va más cerca de la recta de P0 a P1 y dobla más junto a ellos."""
    P0, P1 = np.asarray(P0, float), np.asarray(P1, float)
    largo = float(np.linalg.norm(P1 - P0))
    u = np.linspace(0, 1, max(8, int(1.3 * largo / PASO)))[:, None]
    h00, h10 = 2 * u ** 3 - 3 * u ** 2 + 1, u ** 3 - 2 * u ** 2 + u
    h01, h11 = 3 * u ** 2 - 2 * u ** 3, u ** 3 - u ** 2
    L = largo * recta
    C = h00 * P0 + h10 * L * np.asarray(t0) + h01 * P1 + h11 * L * np.asarray(t1)
    return C if abre is None else C + np.sin(math.pi * u) ** 2 * abre


def _vertical(P, z) -> np.ndarray:
    """Una recta vertical desde P hasta la altura z, en puntos."""
    k = max(2, int(abs(z - P[2]) / PASO) + 1)
    out = np.repeat(np.asarray(P, float)[None], k, axis=0)
    out[:, 2] = np.linspace(P[2], z, k)
    return out


def cuerda(p: AmarreCuadrado, cruz, variante: str | None = None) -> Cuerda:
    """Calcula la cuerda entera del amarre sobre la cruz (nudos/anfitrion.py). Con `variante`,
    la del error común que la plantilla sabe construir (AmarreCuadrado.VARIANTES).

    El amarre va tallado, como uno atado y apretado con cuerda real (T15e): las vueltas en
    bandas pegadas a los palos, de un palo al otro tensas y pegadas al cruce, los ahorcados
    juntos y pegados a las esquinas, y el ballestrinque de inicio separado del palo de arriba
    (SEPARA_INICIO). Si los ahorcados no caben entre él y el palo de arriba, el ballestrinque
    se aparta lo que haga falta. El error usa el mismo ballestrinque que el bien hecho, así
    que la cuerda de los dos es la misma hasta las vueltas.

    El error `ahorcados-por-fuera` es el mismo amarre con los ahorcados por encima del palo de
    arriba: donde el bien hecho pasa por debajo de él, el error sube por delante, pasa por
    encima, por fuera de las vueltas, y baja por detrás (o al revés, a la izquierda). Entre
    los palos y sobre el palo de abajo va como el bien hecho, así que cruza las mismas
    esquinas; sobre el palo de arriba van más separados y cada uno va más bajo que el anterior
    (ver alto() y por_el_palo_de_arriba())."""
    if variante is not None and variante not in AmarreCuadrado.VARIANTES:
        raise ValueError(f"el amarre cuadrado no tiene la variante {variante}")
    return cuerda_y_medidas(p, cruz, variante)[0]


def cuerda_y_medidas(p: AmarreCuadrado, cruz, variante: str | None = None):
    """La cuerda, con dónde va la primera vuelta del ballestrinque de inicio (a c1 del eje del
    palo de arriba) y por dónde pasa cada ahorcado por los palos (ahorcados_y_cierre). Los
    ahorcados del bien hecho y del error tienen que caber entre el ballestrinque y el palo de
    arriba; los dos van con el mismo ballestrinque."""
    # Por fuera de las vueltas, que bajo el palo de abajo llegan hasta B[1] (_cuerda).
    c1 = max(cruz.radio + R_CUERDA + SEPARA_INICIO,
             cruz.rb + 0.05 + (p.vueltas - 1) * PASO_VUELTAS + CARRIL)
    for _ in range(2):
        pasos = {v: _cuerda(p, cruz, v, c1)[1] for v in (None, "ahorcados-por-fuera")}
        # El firme va sobre el palo de abajo desde DESPEGA más allá de la primera vuelta del
        # ballestrinque, y el ahorcado más afuera pasa bajo él un diámetro más adentro.
        falta = max(c["del"] for ps in pasos.values() for c in ps) + DESPEGA + 1.0
        if falta <= c1 + 1e-9:
            break
        c1 = falta
    c, pasos = _cuerda(p, cruz, variante, c1)
    return c, c1, pasos


def _cuerda(p: AmarreCuadrado, cruz, variante: str | None, c1: float) -> tuple[Cuerda, list[dict]]:
    """La cuerda del amarre con la primera vuelta del ballestrinque de inicio a c1 del eje del
    palo de arriba, y por dónde pasa cada ahorcado por los palos."""
    from .trazo import ABAJO, ARRIBA, CINTURA, Trazo
    por_fuera = variante == "ahorcados-por-fuera"
    n, m = p.vueltas, p.ahorcados
    pal = _Palos(cruz)
    rb, zb, zt = cruz.rb, cruz.zb, cruz.zt
    a0 = rb + 0.05        # la vuelta más pegada al otro palo
    # Cada vuelta nueva va por fuera de la anterior sobre el palo de arriba y por dentro
    # sobre el de abajo, como en las referencias. Delante y detrás van igual de pegadas al
    # cruce: el ballestrinque de inicio queda por fuera de ellas.
    A = [None] + [a0 + (k - 1) * PASO_VUELTAS for k in range(1, n + 2)]   # sobre el de arriba
    B = [None] + [a0 + (n - k) * PASO_VUELTAS for k in range(1, n + 1)]   # bajo el de abajo
    if c1 - CARRIL < B[1]:
        raise ValueError("las vueltas no caben entre el palo de arriba y el ballestrinque de inicio")
    carriles = [-(c1 + k * CARRIL) for k in range(4)]   # vuelta 1, firme, chicote, vuelta 2
    sube_z = np.array([0.0, 0.0, 1.0])

    # --- Las esquinas de las vueltas: tensas de un palo al otro ---
    esq: dict[tuple[int, int], _Esquina] = {}
    for k in range(1, n + 1):
        # Detrás a la derecha: deja el de arriba por detrás y llega al de abajo por la derecha.
        a, b = pal.tensa(A[k], B[k], -1, -1, True)
        esq[k, 1] = _Esquina(1, -1, pal.arriba(A[k], a), pal.abajo(B[k], b),
                             pal.hacia_arriba(a, -1), pal.hacia_abajo(b, -1), a, b)
        # Detrás a la izquierda: sube del de abajo al de arriba.
        a, b = pal.tensa(-A[k], B[k], +1, -1, False)
        esq[k, 2] = _Esquina(2, +1, pal.abajo(B[k], b), pal.arriba(-A[k], a),
                             pal.hacia_abajo(b, -1), pal.hacia_arriba(a, +1), a, b)
        # Delante a la izquierda: deja el de arriba por delante y baja al de abajo por la izquierda.
        a, b = pal.tensa(-A[k], -B[k], +1, +1, True)
        esq[k, 3] = _Esquina(3, -1, pal.arriba(-A[k], a), pal.abajo(-B[k], b),
                             pal.hacia_arriba(a, +1), pal.hacia_abajo(b, +1), a, b)
        if k < n:
            # Delante a la derecha: sube del de abajo a la vuelta siguiente sobre el de arriba.
            a, b = pal.tensa(A[k + 1], -B[k], -1, +1, False)
            esq[k, 4] = _Esquina(4, +1, pal.abajo(-B[k], b), pal.arriba(A[k + 1], a),
                                 pal.hacia_abajo(b, +1), pal.hacia_arriba(a, -1), a, b)
    # A media altura, las esquinas de cada lado se apartan unas de otras lo justo.
    for q in (1, 2, 3, 4):
        _abrir([esq[k, q] for k in range(1, n + 1) if (k, q) in esq])

    # --- Alturas de los ahorcados: en el bien hecho, en una banda pegada a las esquinas; en
    # el error, junto al palo de abajo tan bajos como en el bien hecho, debajo del firme ---
    alto = alturas_de_ahorcados(m, por_fuera, cruz, banda=True, baja=BAJA_ERROR)

    t = Trazo()

    # --- Ballestrinque de inicio, desde el chicote: el orden de atado, al revés ---
    # Va de modo que el firme sale por el costado derecho del palo de abajo, hacia arriba; su
    # cruz queda abajo a la derecha. En el orden de atado el ángulo crece; al recorrerlo al
    # revés, alfa = -40 - psi (alfa en el corte del palo, desde +x hacia arriba).
    pts, hito1 = [], None
    for v, psi, alto_b, nombre in reversed(_ballestrinque(*carriles, psi0=0)):
        a, r = math.radians(-40 - psi), rb + alto_b
        pts.append([r * math.cos(a), v, zb + r * math.sin(a)])
        if nombre == "diagonal" and hito1 is None:
            hito1 = len(pts)   # inicio-1: hasta antes de la diagonal
    # El chicote corto asoma un poco del palo, tangente: así la cuerda tiene de dónde correr.
    pts = np.array(pts)
    atras = pts[0] - pts[1]
    atras[2] = max(atras[2], 0.0)                    # sin bajar de la mesa
    t.puntos(pts[0] + 1.2 * _unit(atras), ABAJO)
    t.ir(pts[0], ABAJO)
    t.puntos(pts[:hito1], ABAJO)
    t.marcar("inicio-1")
    t.puntos(pts[hito1 - 1:], ABAJO)

    # --- El firme, del ballestrinque a la primera vuelta ---
    # Sube recto por el costado del palo de abajo hasta SOBRE_FIRME de él, pasa por encima de la
    # vuelta del ballestrinque más cercana al cruce y va hacia el cruce sobre el palo de abajo,
    # a esa distancia: por encima de donde los ahorcados pasan sobre el palo. Junto al palo de
    # arriba sube por su cara de delante y, por encima, se corre hasta la primera vuelta. El
    # hito del inicio va donde termina de subir recto: así, en el video (T21d), el ballestrinque
    # del paso 1 y el del paso 2 se asientan casi igual, porque el firme tira de él del mismo modo.
    r_f = rb + SOBRE_FIRME
    th = math.radians(ANG_FIRME)
    t.puntos(_vertical(pal.abajo(carriles[1], 0.0), zb + math.sqrt(r_f ** 2 - rb ** 2)), ABAJO)
    t.marcar("inicio")
    W1 = np.array([r_f * math.cos(th), -c1 + DESPEGA, zb + r_f * math.sin(th)])
    t.puntos(_hermite(t.fin, W1, sube_z, np.array([0.0, 1.0, 0.0])), AIRE)
    ignorar = len(t.piezas)   # hasta aquí, nada estorba a los ahorcados: van entre esto y el cruce
    # Donde deja el palo de abajo, el firme queda a 0,4 de la cara del de arriba.
    y_trepa = -math.sqrt((rb + 0.4) ** 2 - (zt - W1[2]) ** 2)
    W2 = np.array([W1[0], y_trepa, W1[2]])
    t.ir(W2, ABAJO)
    a_f = math.pi / 2       # por encima del palo llega a la primera vuelta
    a_t = a_f + (_tangente(pal.centro_ar, rb, W2[[1, 2]], -1) - a_f) % (2 * math.pi)
    t.ir(pal.arriba(W1[0], a_t), ARRIBA)
    u = np.linspace(0.0, 1.0, max(8, int((a_t - a_f) * rb / PASO) + 1))
    s = u * u * (3 - 2 * u)
    helice = np.array([pal.arriba(W1[0] + (A[1] - W1[0]) * si, a_t + (a_f - a_t) * ui)
                       for ui, si in zip(u, s)])
    t.puntos(helice, ARRIBA)
    firme = _Firme(a_f)
    # Los ahorcados cruzan el firme sobre el palo de abajo, delante, por debajo de él.
    medio_firme = np.array([[W1[0], 0.5 * (W1[1] + y_trepa)]])

    # --- Vueltas ---
    esquinas = []   # en el orden de la cuerda, con sus puntos
    for k in range(1, n + 1):
        e1, e2, e3 = esq[k, 1], esq[k, 2], esq[k, 3]
        entra = firme if k == 1 else esq[k - 1, 4]
        t.puntos(pal.arco_arriba(A[k], entra.a, e1.a, -1), ARRIBA)    # por encima, de delante a atrás
        t.puntos(e1.puntos(), CINTURA)
        t.puntos(pal.arco_abajo(B[k], e1.b, e2.b, -1), ABAJO)         # por debajo, de derecha a izquierda
        t.puntos(e2.puntos(), CINTURA)
        t.puntos(pal.arco_arriba(-A[k], e2.a, e3.a, +1), ARRIBA)      # por encima, de atrás a delante
        t.puntos(e3.puntos(), CINTURA)
        sale_b = esq[k, 4].b if k < n else 0.0
        t.puntos(pal.arco_abajo(-B[k], e3.b, sale_b, +1), ABAJO)      # por debajo, de izquierda a derecha
        t.marcar(f"vuelta-{k}")
        esquinas += [(e1, e1.puntos()), (e2, e2.puntos()), (e3, e3.puntos())]
        if k < n:
            t.puntos(esq[k, 4].puntos(), CINTURA)
            esquinas.append((esq[k, 4], esq[k, 4].puntos()))

    # --- Ahorcados y ballestrinque de cierre ---
    # El último tramo de la última vuelta sube por el costado del palo de abajo, pegado al cruce,
    # y va a pasar bajo el palo de arriba, donde empieza el primer ahorcado.
    def salida(planos, pasa_ar, punto):
        zj = alto(1, 0.0)
        E0 = np.array([planos["der"], -pasa_ar(zj, 1), zj])
        llega_e0 = np.array([0.0, 1.0, 0.0])
        if por_fuera:
            # Llega a E0, más alto que el primer ahorcado, hacia donde sigue: la cara de delante
            # del palo de arriba.
            E0 = punto(planos["der"], -pasa_ar(zj, 1), 0)
            llega_e0 = _unit(pal.arriba(E0[0], _tangente(pal.centro_ar, rb, E0[[1, 2]], -1)) - E0)
        t.puntos(_hermite(t.fin, E0, sube_z, llega_e0), ABAJO)

    cierre_min = cruz.radio + R_CUERDA + SEPARA_CIERRE + CARRIL
    pasos = ahorcados_y_cierre(t, pal, m, por_fuera, alto, esquinas, {"der": A[n], "izq": A[n]},
                               salida, junto=True, ignorar=ignorar, piso_del=-y_trepa + 0.9,
                               cierre_min=cierre_min)
    X, Z, hitos = t.muestrear(RADIO_ESQUINA)
    # El trazo lleva el inicio delante y el cierre a la derecha; los otros lados son su reflejo.
    espejo = np.array([-1.0 if p.cierre.lado == "izquierda" else 1.0,
                       -1.0 if p.inicio.lado == "detras" else 1.0, 1.0])
    X = X * espejo
    restos = {}
    for nombre, i in hitos.items():
        if nombre != "cierre":
            sale = SALIDAS[nombre] if nombre in SALIDAS else SALIDAS[nombre.split("-")[0]]
            restos[nombre] = _resto(X[i], _unit(X[i] - X[max(i - 3, 0)]),
                                    _unit(np.array([*sale, 0.0]) * espejo))
    alias = {"vueltas": f"vuelta-{n}", "ahorcados": f"ahorcado-{m}"}
    # Dónde cruza cada esquina al primer ahorcado: da el orden en que los ahorcados las recorren.
    ang = lambda P: np.arctan2(P[..., 1], P[..., 0])
    donde = [((*medio_firme[0],), 0, True)]
    for e, P in esquinas:
        dz = np.abs(P[:, 2] - np.array([alto(1, x) for x in ang(P)]))
        donde.append(((*P[int(dz.argmin()), :2],), e.sube, False))
    return Cuerda(X, Z, hitos, restos, _secuencias(p, donde, bajan=por_fuera), alias), pasos


def alturas_de_ahorcados(m: int, por_fuera: bool, cruz, banda: bool = False, baja: float = 0.0):
    """La altura del ahorcado j en el ángulo ang alrededor del cruce, alto(j, ang).

    Cada ahorcado pasa bajo el palo de arriba cerca de su cara de abajo y sobre el de abajo
    cerca de su cara de arriba; entre los dos sube y baja suave. Cada uno va un poco más alto
    que el anterior, así que en el mapa de la cintura no se cruzan. En el error (`por_fuera`)
    van al revés, cada uno más bajo: así cada ahorcado pasa por debajo de donde los anteriores
    suben al palo de arriba, y no por fuera de ellos. Con j = 0, un poco más alto que el
    primero.

    Con `banda` (el amarre cuadrado bien hecho, tallado), los ahorcados van uno junto al otro,
    en una banda pegada a las esquinas: cada uno por fuera del anterior (ahorcados_y_cierre) y
    solo DZ_BANDA más alto, lo justo para que en el mapa de la cintura no se crucen. El último
    pasa pegado al palo de arriba. j puede tener decimales: en el último cuadrante, cada
    ahorcado sube a la altura del siguiente (ver ahorcados_y_cierre).

    Fuera de la banda, `baja` es cuánto más bajos van todos junto al palo de abajo: en el error
    del amarre cuadrado tallado, así pasan por debajo del firme, como en el bien hecho."""
    rb, zb, zt = cruz.rb, cruz.zb, cruz.zt

    def en_banda(j, ang):
        baja = DZ_BANDA * (m - j)
        bajo, alto_ = zt - rb - BAJO_BANDA - baja, zb + rb - 0.4 - baja
        return bajo + (alto_ - bajo) * math.sin(ang) ** 2

    if banda and not por_fuera:
        en_banda.banda = True
        return en_banda

    def alto(j, ang):
        u = (m - j if por_fuera else j - 1) / (m - 1)
        bajo, alto_ = zt - rb - 0.9 + 0.8 * u, zb + rb - 0.4 - baja + 0.8 * u
        return bajo + (alto_ - bajo) * math.sin(ang) ** 2
    alto.banda = False
    return alto


def ahorcados_y_cierre(t, pal: _Palos, m: int, por_fuera: bool, alto, esquinas, encima: dict,
                       salida, fuera: float = FUERA, junto: bool = False, ignorar: int = 0,
                       piso_del: float = 0.0, cierre_min: float = 0.0) -> list[dict]:
    """Los ahorcados y el ballestrinque de cierre de un amarre sobre la cruz, trazados en `t`
    después de las vueltas. Los usan el amarre cuadrado y el diagonal. Devuelve por dónde pasa
    cada ahorcado bajo el palo de arriba («der» e «izq», en x) y sobre el de abajo («det» y
    «del», en y).

    `alto(j, ang)` es la altura del ahorcado j en el ángulo ang alrededor del cruce;
    `esquinas`, lo que cada ahorcado rodea por fuera, en el orden de la cuerda: pares
    (esquina, puntos), donde la esquina dice su `cuadrante`. `encima` dice hasta dónde llegan
    las vueltas sobre el palo de arriba, a la derecha («der») y a la izquierda («izq»), a lo
    largo de x: en el error (`por_fuera`), los ahorcados pasan por encima de él más afuera. `salida(planos, pasa_ar, punto)` traza la
    salida de la última vuelta hasta donde el primer ahorcado pasa bajo el palo de arriba, a
    la derecha y por delante. El cierre queda a la derecha; los otros lados son su reflejo. En el
    error, `fuera` es cuánto por fuera del palo de arriba empieza a subirlo el primer ahorcado.

    Con `junto` (el amarre cuadrado tallado), los ahorcados pasan por los palos lo más cerca
    del cruce que dejan las esquinas y los anteriores (junto_a); en banda (alturas_de_ahorcados),
    cada uno pegado al anterior. Las primeras `ignorar` piezas de `t` no estorban a los ahorcados:
    el ballestrinque de inicio, más allá de donde pasan. `piso_del` es lo más cerca del cruce
    que pueden pasar sobre el palo de abajo por delante, y `cierre_min`, lo más cerca que va el
    firme del ballestrinque de cierre."""
    from .trazo import ABAJO, ARRIBA, CINTURA, MESA, Plano, _densa
    rb, zt = pal.rb, pal.zt
    ang = lambda P: np.arctan2(P[..., 1], P[..., 0])
    # En banda, cada ahorcado va junto al anterior (alturas_de_ahorcados) y, en el último
    # cuadrante, sube a la altura del siguiente. Ahí j es una función del ángulo.
    banda = getattr(alto, "banda", False) and not por_fuera
    nivel = lambda j, a: j(a) if callable(j) else j

    # --- Ahorcados: vueltas tensas entre los palos, por fuera de todo lo que ya está ---
    def cerca(j, cuadrante, extra=()):
        """Lo que tiene que dejar por fuera un ahorcado en un cuadrante: los puntos de la cuerda
        trazada (menos el tramo que acaba de hacer) que quedan a su altura, cada uno con el
        radio que tiene que dejarle."""
        P = np.vstack([_densa(x.puntos) if x.recta else x.puntos for x in t.piezas[ignorar:]])
        s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
        P = P[s <= s[-1] - 3.5]
        if len(extra):
            P = np.vstack([P, extra])
        sx, sy = CUADRANTES[cuadrante]
        P = P[(sx * P[:, 0] > 0) & (sy * P[:, 1] > 0)]
        dz = P[:, 2] - np.array([alto(nivel(j, x), x) for x in ang(P)])
        lejos = np.abs(dz) < LIBRE
        return P[lejos, :2], np.sqrt(LIBRE ** 2 - dz[lejos] ** 2)

    def extremos(j):
        """Por dónde pasan los ahorcados bajo el palo de arriba (a la derecha y a la izquierda)
        y sobre el de abajo (detrás y delante): justo por fuera de las esquinas."""
        out = {}
        for nombre, cuads, eje, signo in (("der", (1, 4), 0, 1), ("det", (1, 2), 1, 1),
                                         ("izq", (2, 3), 0, -1), ("del", (3, 4), 1, -1)):
            lejos = 0.0
            for e, P in esquinas:
                if e.cuadrante not in cuads:
                    continue
                dz = P[:, 2] - np.array([alto(j, x) for x in ang(P)])
                ok = np.abs(dz) < LIBRE
                if ok.any():
                    lejos = max(lejos, float((signo * P[ok, eje] + np.sqrt(LIBRE ** 2 - dz[ok] ** 2)).max()))
            out[nombre] = lejos + 0.05
        return out

    def pasa_ab(z, r=rb):
        """Lo que se aparta del eje del palo de abajo al pasar sobre él, como si el palo tuviera
        radio r."""
        return math.sqrt(max(0.0, r ** 2 - (z - pal.zb) ** 2)) + 0.5

    def sobre_ab(z, Y, signo, j, r):
        """El x donde el ahorcado j empieza o termina de pasar sobre el palo de abajo, en el
        plano y = Y, por el lado `signo`. En banda, con la altura que tiene ahí y no la de
        encima del palo: lejos del palo baja, y tiene que quedar por fuera del radio r."""
        x = pasa_ab(z, r)
        if banda:
            for _ in range(30):
                x = pasa_ab(alto(j, math.atan2(Y, signo * x)), r)
        return signo * x
    if por_fuera:
        # Suben al palo de arriba y bajan de él en diagonal, desde un poco por delante o por
        # detrás de su cara; cada ahorcado, un poco más lejos que el anterior, para no tener
        # que rodear ahí mismo el pie del anterior.
        pasa_ar = lambda z, j: rb + fuera + (j - 1) * ABRE_FUERA
    else:
        pasa_ar = lambda z, j: pal.ancho_arriba(z) + 0.5

    def punto(x, y, j):
        a = math.atan2(y, x)
        return np.array([x, y, alto(nivel(j, a), a)])

    def junto_a(j, nombre, desde=None):
        """Lo más cerca del cruce que el ahorcado j puede pasar bajo el palo de arriba («der» o
        «izq») o sobre el de abajo («det» o «del»): desde lo que dejan los palos, el primer
        valor en que sus dos puntas quedan a LIBRE de lo que ya está atado a su altura (cerca)
        y, si se da `desde`, donde empieza el tramo que llega a una de ellas, ese tramo puede
        ir tenso por fuera de todo (_cadena). Así va pegado a las esquinas y, en banda, al
        anterior, sin correrse más afuera."""
        signo = 1 if nombre in ("der", "det") else -1
        cuads = {"der": (1, 4), "det": (1, 2), "izq": (2, 3), "del": (4, 3)}[nombre]
        llega_a = {"der": 1, "det": 0, "izq": 0, "del": 1}[nombre]   # la punta donde acaba el tramo
        if nombre in ("der", "izq"):
            z = alto(j, 0.0 if signo > 0 else math.pi)
            piso = math.sqrt(max(0.0, (rb + 0.05) ** 2 - (z - pal.zb) ** 2))
            puntas = lambda c: (punto(signo * c, pasa_ar(z, j), j), punto(signo * c, -pasa_ar(z, j), j))
        else:
            z = alto(j, signo * math.pi / 2)
            piso = math.sqrt(max(0.0, (rb + 0.05) ** 2 - (zt - pal.zb - rb) ** 2))
            if nombre == "del":
                piso = max(piso, piso_del)
            puntas = lambda c: (punto(sobre_ab(z, signo * c, 1, j, rb), signo * c, j),
                                punto(sobre_ab(z, signo * c, -1, j, rb), signo * c, j))
        obst = [cerca(j, q) for q in cuads]
        # Por fuera de lo que, a su altura, llega más lejos en esa dirección en los dos
        # cuadrantes: así no corre a lo largo del palo antes de rodear las esquinas, y el
        # siguiente puede ir junto a él.
        eje = 0 if nombre in ("der", "izq") else 1
        for C, R in obst:
            if len(C):
                piso = max(piso, float((signo * C[:, eje] + R).max()) + 0.05)

        def tenso(Q):
            if desde is None:
                return True
            try:
                _cadena(desde[:2], Q[:2], *obst[llega_a])
            except ValueError:
                return False
            return True
        for c in np.arange(piso, piso + 20.0, 0.02):
            Qs = puntas(c)
            if all(not len(C) or (np.linalg.norm(C - Q[:2], axis=1) >= R).all()
                   for (C, R), Q in zip(obst, Qs)) and tenso(Qs[llega_a]):
                return float(c)
        raise ValueError(f"el ahorcado {j} no encuentra por dónde pasar ({nombre})")

    if banda:
        planos = {"der": junto_a(1, "der")}
    elif junto:
        planos = {nombre: junto_a(1, nombre) for nombre in ("der", "det", "izq", "del")}
    else:
        planos = extremos(1)
    if por_fuera:
        # Por encima del palo de arriba, los ahorcados pasan por fuera de las vueltas.
        for lado in ("der", "izq"):
            planos[lado] = max(planos[lado], encima[lado] + SEPARA_ENCIMA)
    x_cierre = None

    def tramo(S, E, j, cuadrante, extra=(), entera=()):
        """El ahorcado j en un cuadrante, de S a E, tenso por fuera de lo que ya está. Las
        rectas de `entera` («primera», «ultima») van enteras, sin seguir la altura del
        ahorcado, para que la esquina con lo que sigue se pueda redondear."""
        C, R = cerca(j, cuadrante, extra)
        for Q in (S, E):
            if len(C) and (np.linalg.norm(C - Q[:2], axis=1) < R - 1e-6).any():
                raise ValueError(f"el ahorcado {nivel(j, 0.0):.0f} no cabe junto a los palos en el "
                                 f"cuadrante {cuadrante}")
        # Cada recta se parte en pedazos cortos, para que siga la altura de su ahorcado.
        cadena = _cadena(S[:2], E[:2], C, R)
        ultima = len(cadena) - 2
        for k, (Q0, Q1) in enumerate(zip(cadena[:-1], cadena[1:])):
            if (k == 0 and "primera" in entera) or (k == ultima and "ultima" in entera):
                t.ir(punto(Q1[0], Q1[1], j), CINTURA)
                continue
            for u in np.linspace(0, 1, max(2, int(np.linalg.norm(Q1 - Q0) / PASO) + 1))[1:]:
                Q = Q0 + u * (Q1 - Q0)
                t.ir(punto(Q[0], Q[1], j), CINTURA)

    def por_el_palo_de_arriba(X, S, sentido):
        """Del final hasta S pasando por el palo de arriba, en el plano x = X: por debajo, en el
        amarre bien hecho, o por encima, en el error. `sentido` es el del bien hecho."""
        if not por_fuera:
            t.rodear(pal.centro_ar, Plano(0, X), S, sentido, ARRIBA, ARRIBA, rb)
            return
        # Por encima se gira al revés: sube en diagonal hasta una cara del palo, pasa por arriba
        # y baja en diagonal por la otra. Lo que sube y baja va en la cintura, como el resto del
        # ahorcado, y ahí cada esquina de las vueltas lo cruza una vez: las esquinas llegan al
        # palo más arriba de donde él empieza a subir.
        a0 = _tangente(pal.centro_ar, rb, t.fin[[1, 2]], -sentido)
        a1 = _tangente(pal.centro_ar, rb, S[[1, 2]], -sentido, saliendo=True)
        t.ir(pal.arriba(X, a0), CINTURA)
        t.puntos(pal.arco_arriba(X, a0, a1, -sentido), ARRIBA)
        t.ir(S, CINTURA)

    # En el error, las rectas de cada cuadrante que llegan al palo de arriba o salen de él van
    # enteras, para redondear la esquina donde la cuerda sube o baja por su cara.
    llega = ("ultima",) if por_fuera else ()
    sale = ("primera",) if por_fuera else ()

    salida(planos, pasa_ar, punto)
    # En el error, por encima del palo de arriba van más separados: así cada uno baja de él
    # lejos de donde baja el anterior, y no tiene que rodearlo ahí mismo.
    paso_ar = SEPARA_ENCIMA if por_fuera else PASO_VUELTAS

    def pasa(j, nombre):
        """Por dónde pasa el ahorcado j por un palo. Fuera de la banda, cada uno pasa un
        diámetro más afuera que el anterior (en el error, por encima del palo de arriba,
        SEPARA_ENCIMA); en banda, junto al anterior y a las esquinas, a su altura."""
        if banda:
            return junto_a(j, nombre, desde=t.fin)
        return planos[nombre] + (j - 1) * (paso_ar if nombre in ("der", "izq") else PASO_VUELTAS)

    pasos = []
    x_sig = planos["der"]
    for j in range(1, m + 1):
        r_ab = rb   # el radio con que pasa sobre el palo de abajo
        # Bajo el palo de arriba (en el error, por encima), de delante a atrás, y por fuera de las
        # esquinas de detrás a la derecha.
        Xr = x_sig if banda else pasa(j, "der")
        z = alto(j, 0.0)
        S = punto(Xr, pasa_ar(z, j), j)
        por_el_palo_de_arriba(Xr, S, +1)
        Yt = pasa(j, "det")
        z = alto(j, math.pi / 2)
        tramo(S, punto(sobre_ab(z, Yt, 1, j, r_ab), Yt, j), j, 1, entera=sale)
        # Sobre el palo de abajo, de derecha a izquierda, y detrás a la izquierda.
        S = punto(sobre_ab(z, Yt, -1, j, r_ab), Yt, j)
        t.rodear(pal.centro_ab, Plano(1, Yt), S, +1, ABAJO, ABAJO, r_ab)
        Xl = pasa(j, "izq")
        z = alto(j, math.pi)
        tramo(S, punto(-Xl, pasa_ar(z, j), j), j, 2, entera=llega)
        # Bajo el palo de arriba (en el error, por encima), de atrás a delante, y delante a la
        # izquierda.
        S = punto(-Xl, -pasa_ar(z, j), j)
        por_el_palo_de_arriba(-Xl, S, -1)
        Yd = pasa(j, "del")
        z = alto(j, -math.pi / 2)
        tramo(S, punto(sobre_ab(z, -Yd, -1, j, r_ab), -Yd, j), j, 3, entera=sale)
        # Sobre el palo de abajo, de izquierda a derecha, y delante a la derecha, hasta donde
        # pasa bajo el palo de arriba el ahorcado siguiente. El último lleva al firme del
        # ballestrinque de cierre, por fuera de su primera vuelta.
        S = punto(sobre_ab(z, -Yd, 1, j, r_ab), -Yd, j)
        t.rodear(pal.centro_ab, Plano(1, -Yd), S, -1, ABAJO, ABAJO, r_ab)
        pasos.append({"der": Xr, "det": Yt, "izq": Xl, "del": Yd})
        z = alto(j, 0.0)
        extra = ()
        if banda:
            # Sube suave a la altura del siguiente, que pasa bajo el palo de arriba junto a él.
            # El último sube igual, hacia el ballestrinque de cierre: si se quedara a su altura,
            # cruzaría ahí al anterior, que ya subió a ella.
            d0, d1 = math.radians(SUBE_DESDE), math.radians(SUBE_HASTA)

            def jj(a, j=j):
                u = min(1.0, max(0.0, (a - d0) / (d1 - d0)))
                return j + u * u * (3 - 2 * u)
            if j < m:
                x_sig = junto_a(j + 1, "der", desde=t.fin)
            else:
                x_sig = max(Xr + PASO_VUELTAS + CARRIL, encima["der"] + 2 * CARRIL, cierre_min)
                muro = np.linspace(-rb, 0.0, 12)
                extra = np.column_stack([np.full(12, x_sig - CARRIL), muro,
                                         [alto(jj(a), a) for a in np.arctan2(muro, x_sig)]])
            tramo(S, punto(x_sig, -pasa_ar(alto(j + 1, 0.0), j + 1), j + 1), jj, 4, extra)
            t.marcar(f"ahorcado-{j}")
            x_cierre = x_sig
            continue
        if j < m:
            x_sig = Xr + paso_ar
        else:
            x_sig = max(Xr + PASO_VUELTAS + CARRIL, cierre_min)
            muro = np.linspace(-rb, 0.0, 12)
            extra = np.column_stack([np.full(12, x_sig - CARRIL), muro,
                                     [alto(j, math.atan2(y, x_sig)) for y in muro]])
        tramo(S, punto(x_sig, -pasa_ar(z, j + 1), j), j, 4, extra, entera=llega)
        t.marcar(f"ahorcado-{j}")
        x_cierre = x_sig

    # --- Ballestrinque de cierre, en el palo de arriba, en orden de atado ---
    bal = _ballestrinque(x_cierre - CARRIL, x_cierre, x_cierre + CARRIL, x_cierre + 2 * CARRIL,
                         psi0=450)
    P = t.fin
    a_ent = math.degrees(_tangente(pal.centro_ar, rb, np.array([P[1], P[2]]), +1)) % 360
    pts = [[x_cierre, rb * math.cos(math.radians(s)), zt + rb * math.sin(math.radians(s))]
           for s in np.arange(a_ent, bal[0][1], 6.0)]
    hito1 = None
    for v, psi, alto_b, nombre in bal:
        a, r = math.radians(psi), rb + alto_b
        pts.append([v, r * math.cos(a), zt + r * math.sin(a)])
        if nombre == "vuelta2" and hito1 is None:
            hito1 = len(pts)
    t.puntos(np.array(pts[:hito1]), ARRIBA)
    t.marcar("cierre-1")
    t.puntos(np.array(pts[hito1 - 1:]), ARRIBA)
    a = math.radians(bal[-1][1])     # el chicote sale un poco del palo, tangente
    t.ir(t.fin + 1.5 * np.array([0.0, -math.sin(a), math.cos(a)]), MESA)
    t.marcar("cierre")
    return pasos


def _cadena(S, E, centros, radios, lados=40) -> np.ndarray:
    """El camino más corto de S a E, en sentido antihorario, que deja del lado de dentro los
    discos (centros, radios): el borde de su envolvente convexa, como una cuerda tensa."""
    from scipy.spatial import ConvexHull
    t = np.linspace(0, 2 * math.pi, lados, endpoint=False)
    anillo = np.column_stack([np.cos(t), np.sin(t)])
    P = np.vstack([S, E] + [c + r * anillo for c, r in zip(centros, radios)])
    v = [int(i) for i in ConvexHull(P).vertices]   # en sentido antihorario
    if 0 not in v or 1 not in v:
        raise ValueError("un ahorcado no puede pasar por fuera de las esquinas")
    i = v.index(0)
    v = v[i:] + v[:i]
    return P[v[:v.index(1) + 1]]


def _ballestrinque(c_v1, c_firme, c_chicote, c_v2, psi0, paso=6.0):
    """Un ballestrinque sobre un palo, en orden de atado (desde el firme): una lista de
    (posición a lo largo del palo, ángulo en grados, cuánto se aleja del palo, tramo), con el
    ángulo creciente.

    Va en cuatro carriles a lo largo del palo: la primera vuelta, el firme, el chicote y la
    segunda vuelta. El firme llega por su carril y se va a la primera vuelta; la diagonal
    cruza por encima del firme (en psi0 - 10) y del chicote (en psi0 + 20) hasta la segunda
    vuelta, y el chicote vuelve a su carril por debajo de la diagonal. Donde cruza, la
    diagonal va un diámetro más lejos del palo; sube y baja despacio, para no doblarse."""
    out = []

    def tramo(p0, p1, v0, v1, nombre, lineal=False):
        for t in np.linspace(0, 1, max(2, int(abs(p1 - p0) / paso) + 1)):
            psi = p0 + (p1 - p0) * t
            if out and abs(out[-1][1] - psi) < 1e-9:
                continue
            s = t if lineal else t * t * (3 - 2 * t)
            out.append((v0 + (v1 - v0) * s, psi, _levantar(psi - psi0), nombre))

    tramo(psi0 - 40, psi0, c_firme, c_firme, "firme")
    tramo(psi0, psi0 + 90, c_firme, c_v1, "deriva1")
    tramo(psi0 + 90, psi0 + 320, c_v1, c_v1, "vuelta1")
    tramo(psi0 + 320, psi0 + 410, c_v1, c_v2, "diagonal", lineal=True)
    tramo(psi0 + 410, psi0 + 680, c_v2, c_v2, "vuelta2")
    tramo(psi0 + 680, psi0 + 710, c_v2, c_chicote, "deriva2")
    tramo(psi0 + 710, psi0 + 760, c_chicote, c_chicote, "chicote")
    return out


def _levantar(d) -> float:
    """Cuánto se aleja del palo la diagonal de un ballestrinque, d grados después de psi0:
    un diámetro entre sus dos cruces (de 335 a 395), con rampas suaves de 55 grados."""
    sube = np.clip((d - 280) / 55, 0, 1)
    baja = np.clip((450 - d) / 55, 0, 1)
    x = min(sube, baja)
    return float(2 * R_CUERDA * x * x * (3 - 2 * x))


def _tangente(c, r, P, sentido, saliendo=False) -> float:
    """El ángulo del punto del círculo (c, r) donde una recta desde P llega tangente
    (o, con `saliendo`, donde la cuerda lo deja para ir recta a P), girando en `sentido`."""
    d = P - c
    a = math.atan2(d[1], d[0])
    b = math.acos(min(1.0, r / float(np.linalg.norm(d))))
    for ang in (a + b, a - b):
        T = c + r * np.array([math.cos(ang), math.sin(ang)])
        t = sentido * np.array([-math.sin(ang), math.cos(ang)])
        if np.dot((P - T) if saliendo else (T - P), t) > 0:
            return ang
    raise ValueError("no hay tangente")


def _unit(v) -> np.ndarray:
    return v / max(float(np.linalg.norm(v)), 1e-12)


def _resto(P, llega, afuera) -> np.ndarray:
    """Puntos de control de lo que sigue de la cuerda después de un hito: sigue un poco como
    venía, gira hacia fuera del amarre y baja en curva hasta la mesa."""
    q1 = P + 1.0 * llega
    q2 = q1 + 1.0 * _unit(llega + afuera)
    q3 = q2 + 1.5 * afuera
    out = [q1, q2, q3]
    for u in (0.2, 0.4, 0.6, 0.8, 1.0):
        q = q3 + 9.0 * u * afuera
        q[2] = 0.5 + (q3[2] - 0.5) * (1 - u * u * (3 - 2 * u))   # baja sin quiebres
        out.append(q)
    out.append(out[-1] + 6.0 * afuera)
    return np.array(out)


def _secuencias(p: AmarreCuadrado, esquinas, bajan: bool = False) -> dict[str, tuple[str, ...]]:
    """La secuencia de cruces del método hasta cada hito.

    El ballestrinque de inicio da los cruces 1 y 2; cada ahorcado pasa por encima de cada
    esquina de las vueltas; el ballestrinque de cierre da los dos últimos. Las vueltas no se
    cruzan entre sí, porque van una junto a otra. Sobre cada esquina, los ahorcados pasan de
    abajo arriba (el primero es el más bajo o, si `bajan`, el más alto); cada ahorcado
    recorre las esquinas en el sentido en que gira, desde que pasa por el palo de arriba.

    `esquinas` da, en el orden de la cuerda, dónde cruza cada una al primer ahorcado, si sube y
    si es el firme. El firme va del ballestrinque de inicio, separado del cruce, al palo de
    arriba por encima del palo de abajo, así que pasa por encima de los ahorcados, que pasan
    sobre el palo entre el ballestrinque y el cruce: el más afuera, el último, primero.

    El error `ahorcados-por-fuera` tiene esta misma secuencia, con `bajan`: lo que cambia es
    por qué lado del palo de arriba pasan los ahorcados, y ahí no cruzan nada. Sobre el palo
    de abajo van como en el bien hecho, así que el firme los cruza en el mismo orden."""
    m = p.ahorcados
    etiqueta = lambda c, j: str(3 + c * m + (j - 1))
    ultimo = 3 + len(esquinas) * m
    # Cada ahorcado entra a la cintura después de pasar bajo el palo de arriba, a la derecha
    # (giro 0), y recorre las esquinas en el sentido en que gira.
    giro0 = 0.0
    por_giro = sorted(range(len(esquinas)),
                      key=lambda c: (math.atan2(esquinas[c][0][1], esquinas[c][0][0]) - giro0) % (2 * math.pi))
    orden = list(p.hitos())
    out = {}
    for hito in orden:
        r = orden.index(hito)
        sec = []
        if r >= orden.index("inicio"):
            sec += ["1U", "1O", "2O", "2U"]
        hechos = [j for j in range(1, m + 1) if r >= orden.index(f"ahorcado-{j}")]
        for c, (_, sube, firme) in enumerate(esquinas):
            if firme:
                sec += [etiqueta(c, j) + "O" for j in hechos[::-1]]
                continue
            for j in (hechos if (sube > 0) != bajan else hechos[::-1]):
                sec.append(etiqueta(c, j) + "U")
        for j in hechos:
            sec += [etiqueta(c, j) + ("U" if esquinas[c][2] else "O") for c in por_giro]
        if r >= orden.index("cierre-1"):
            sec += [f"{ultimo}U", f"{ultimo}O"]
        if r >= orden.index("cierre"):
            sec += [f"{ultimo + 1}O", f"{ultimo + 1}U"]
        out[hito] = tuple(sec)
    for alias, k in (("vueltas", p.vueltas), ("ahorcados", m)):
        nombre = "vuelta" if alias == "vueltas" else "ahorcado"
        out[alias] = out[f"{nombre}-{k}"]
    return out

