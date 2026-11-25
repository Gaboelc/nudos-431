"""Plantilla del adujado: una aduja de cuerda libre sobre la mesa, sin anfitrión.

El método es el del diseño de la tanda 4 en tasks/historial.md («El adujado»): se hacen senos que se
cierran sobre el extremo, uno por encima y el siguiente por debajo; la aduja se junta por la
mitad; con la cuerda que queda se dan vueltas alrededor de la mitad, hacia la derecha; un seno
de la cuerda pasa por el ojo de la derecha, se abre, se pasa por encima de la punta y queda
abrazando la aduja junto a las vueltas. Al tirar del chicote, el seno se cierra.

Todo va sobre la mesa y los cruces se buscan desde arriba, como en un nudo libre. La aduja
juntada es una banda plana: bajo las vueltas, sus tramos van uno junto a otro. Unidades: el
diámetro de la cuerda. x a la derecha, y hacia el fondo de la mesa, z hacia arriba.

La cuerda de cada hito se traza entera, pieza por pieza, en la planta (x, y). Cada pieza tiene
un nivel: donde pasa a menos de HOLGURA de una pieza de nivel más bajo, va sobre ella, con
subidas y bajadas suaves. Los costados de las vueltas y del seno que rodea la aduja, que bajan
de un lado de la banda al otro, toman su altura de lo que rodean y de lo que empalman. La
secuencia de cruces sale de esa cuerda, y la etiqueta de cada cruce es la de sus dos piezas y
su lado de la aduja, así que un cruce conserva su etiqueta de un paso a otro.

La cuerda no se relaja (Cuerda._quietos): la plantilla ya la traza sin que nada se toque ni se
doble de más.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.interpolate import splev, splprep
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

from .trazo import MESA, TrazoDePaso

NUMEROS = {3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete", 8: "ocho"}
SENOS = (3, 6)
VUELTAS = (3, 8)
_CAMPOS = {"tipo", "senos", "vueltas"}

# Medidas en diámetros; ver el diseño en tasks/historial.md.
LARGO = 15.0          # media longitud del primer seno (x de su punta izquierda: -LARGO)
ANCHO_ABIERTO = 6.5   # medio ancho del primer seno con la aduja abierta
G = 1.05              # entre dos tramos vecinos de la banda
PUNTAS = 2.8          # entre las puntas de dos senos vecinos, donde cruzan el extremo
OJO = 1.25            # entre dos senos vecinos en los ojos
ALTO_OJO_IZQ = 4.5    # medio alto del primer seno en el ojo izquierdo
ALTO_OJO_DER = 5.5    # y en el derecho, que es donde entra el seno
TRANSICION = 12.0     # cuánto tarda la banda en abrirse en cada ojo: con menos, los senos de
                      # afuera se doblan donde la banda se abre
PASO_VUELTA = 1.1     # entre dos vueltas
RADIO_LADO = 1.03     # radio de los costados de las vueltas, alrededor del tramo de afuera
GIRO = 1.2            # radio de las curvas de la cuerda sobre la mesa
SUELTO = 0.8          # cuánto más alto y más afuera va el seno antes de tirar del chicote
LAZO_CURVA = 1.6      # a cuánto del tramo de afuera va el seno que rodea la aduja, por los costados
FORMA_LAZO = 1.5      # cómo avanza a lo largo de la aduja el costado del seno que la rodea
FUERA = 0.3           # en la planta, cuánto pasan las vueltas más allá del tramo de afuera
HOLGURA = 1.03        # una cuerda que pasa sobre otra va a esta distancia de ella
VECINO = 3.0          # a lo largo de la cuerda, lo que está más cerca no se apila
RAMPA = 2.4           # largo de la subida o bajada de una pasada por encima
PUENTE = 3.0          # entre dos pasadas por encima más cercanas que esto, la cuerda no baja
SUAVE = 0.3           # cuánto se suavizan las subidas y bajadas, para que no se doblen
PASO_MAPA = 0.05      # cada cuánto se traza la cuerda
PASO_CONTROL = 0.3    # cada cuánto se toma un punto de control
CAMBIO = 0.08         # en vueltas del seno, cuánto tarda en pasar al seno siguiente
RESTO = 6.0           # lo que sigue de la cuerda después del hito, por la mesa


@dataclass(frozen=True)
class Adujado:
    senos: int
    vueltas: int

    tipo = "adujado"
    ANFITRION = None   # libre sobre la mesa
    # El error común que sabe construir, con el primer hito desde el que se ve: todos los senos
    # pasan por encima del extremo, en vez de alternar.
    VARIANTES = {"sin-alternar": "seno-2"}
    CON_FIRME: tuple[str, ...] = ()
    # Con el motor (T15f): la aduja va suelta sobre la mesa, sin tensión de atado, y no se
    # aprieta (nudos/plantillas/pasos.py).
    TENSION = "suelta"
    APRETAR = False

    @classmethod
    def leer(cls, datos: dict, falla) -> Adujado:
        sobran = set(datos) - _CAMPOS
        if sobran:
            raise falla(f"campos desconocidos: {', '.join(sorted(sobran))}")
        out = {}
        for campo, (lo, hi) in (("senos", SENOS), ("vueltas", VUELTAS)):
            v = datos.get(campo)
            if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
                raise falla(f"«{campo}» es un número entero de {lo} a {hi}")
            out[campo] = v
        return cls(**out)

    def hitos(self) -> dict[str, int]:
        """Los valores de `hasta`, en orden. `senos` es lo mismo que el último seno y `vueltas`
        que la última vuelta."""
        out, k = {}, 0
        for i in range(1, self.senos + 1):
            k += 1
            out[f"seno-{i}"] = k
        out["senos"] = k
        k += 1
        out["juntar"] = k
        for i in range(1, self.vueltas + 1):
            k += 1
            out[f"vuelta-{i}"] = k
        out["vueltas"] = k
        for nombre in ("por-el-ojo", "por-encima", "tirar"):
            k += 1
            out[nombre] = k
        return out

    def medidas(self) -> dict[str, str]:
        return {"senos": NUMEROS[self.senos], "vueltas": NUMEROS[self.vueltas]}


# --------------------------------------------------------------------------
# Herramientas de trazado en la planta
# --------------------------------------------------------------------------
def _suave(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def _recta(a, b, paso: float = PASO_MAPA) -> np.ndarray:
    a, b = np.asarray(a, float), np.asarray(b, float)
    n = max(2, int(math.ceil(np.linalg.norm(b - a) / paso)) + 1)
    return a + np.linspace(0, 1, n)[:, None] * (b - a)


def _arco(centro, radio, a0, a1, paso: float = PASO_MAPA) -> np.ndarray:
    n = max(2, int(math.ceil(abs(a1 - a0) * radio / paso)) + 1)
    a = np.linspace(a0, a1, n)
    return np.column_stack([centro[0] + radio * np.cos(a), centro[1] + radio * np.sin(a)])


def _largo(M) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(M, axis=0), axis=1))])


def _remuestrear(M, paso: float) -> np.ndarray:
    s = _largo(M)
    n = max(1, int(math.ceil(s[-1] / paso)))
    g = np.linspace(0.0, s[-1], n + 1)
    return np.column_stack([np.interp(g, s, M[:, k]) for k in range(M.shape[1])])


def _hermite(P0, T0, P1, T1, paso: float = PASO_MAPA, tension: float = 1.0) -> np.ndarray:
    P0, P1 = np.asarray(P0, float), np.asarray(P1, float)
    T0 = np.asarray(T0, float) / np.linalg.norm(T0)
    T1 = np.asarray(T1, float) / np.linalg.norm(T1)
    d = float(np.linalg.norm(P1 - P0)) * tension
    n = max(8, int(math.ceil(1.5 * d / paso)))
    t = np.linspace(0.0, 1.0, n)[:, None]
    return ((2 * t ** 3 - 3 * t ** 2 + 1) * P0 + (t ** 3 - 2 * t ** 2 + t) * d * T0
            + (-2 * t ** 3 + 3 * t ** 2) * P1 + (t ** 3 - t ** 2) * d * T1)


def _puentes(crudo, pieza, paso: float) -> np.ndarray:
    """Entre dos pasadas por encima de una misma pieza (`pieza` dice la de cada punto) que están
    a menos de PUENTE a lo largo de ella, la cuerda no baja: sigue a la altura de la más baja de
    las dos. Así pasa una punta de seno sobre las dos ramas del seno por el ojo."""
    from scipy.ndimage import maximum_filter1d
    out = crudo.copy()
    w = int(round(PUENTE / paso))
    for k in np.unique(pieza):
        en = np.nonzero(pieza == k)[0]
        c = crudo[en]
        if not (c > 0).any():
            continue
        izq = maximum_filter1d(c, size=w + 1, origin=w // 2, mode="constant", cval=0.0)
        der = maximum_filter1d(c, size=w + 1, origin=-(w // 2), mode="constant", cval=0.0)
        out[en] = np.maximum(c, np.minimum(izq, der))
    return out


def _rampas(crudo, paso: float) -> np.ndarray:
    """La altura de cada punto con subidas y bajadas suaves: el máximo, sobre los demás puntos,
    de su altura cruda por una rampa coseno que va de 1 en el punto a 0 a RAMPA·√altura de él."""
    h = crudo.copy()
    if not (crudo > 0).any():
        return h
    w = RAMPA * np.sqrt(np.maximum(crudo, 1.0)) / paso
    for d in range(1, int(math.ceil(w.max())) + 1):
        f = np.where(d < w, 0.5 + 0.5 * np.cos(np.pi * d / w), 0.0) * crudo
        h[d:] = np.maximum(h[d:], f[:-d])
        h[:-d] = np.maximum(h[:-d], f[d:])
    return h


@dataclass
class _Pieza:
    nombre: str              # «seno-2», «vuelta-1-arriba», «extremo»…: identifica los cruces
    M: np.ndarray            # (N, 2) en la planta, o (N, 3) si es un costado trazado en 3D
    nivel: np.ndarray | float | None = 0.0   # None: no se apila (un costado o la subida en 3D)
    lado: object = None      # en un costado, su _Lado
    extra: float = 0.0       # cuánto más alto va, sobre lo que tiene debajo


# --------------------------------------------------------------------------
# La aduja
# --------------------------------------------------------------------------
class _Aduja:
    """La forma de los senos: el primero es una curva cerrada que empieza en su punta izquierda
    (y = 0) y va en sentido contrario al reloj, visto desde arriba; los demás, por fuera de él,
    a `paso(t)` uno de otro. `abierta` es la aduja recién hecha; si no, juntada, con la banda
    entre `xb0` y `xb1`. `largo` es la media longitud del primer seno y `transicion`, cuánto
    tarda la banda en abrirse en cada ojo (Cuerda)."""

    def __init__(self, n: int, abierta: bool, xb0: float = 0.0, xb1: float = 0.0,
                 largo: float = LARGO, transicion: float = TRANSICION):
        self.n, self.abierta, self.xb0, self.xb1 = n, abierta, xb0, xb1
        self.largo, self.transicion = largo, transicion
        xs = np.linspace(-self.largo, self.largo, 1201)
        y = self._medio_alto(xs)
        delante = np.column_stack([xs, -y])
        detras = np.column_stack([xs[::-1], y[::-1]])
        C = np.vstack([delante, detras[1:-1]])
        # Una curva cerrada suave, por largo de arco.
        tck, _ = splprep([C[:, 0], C[:, 1]], s=0.02 * len(C) * 1e-3, per=1)
        uu = np.linspace(0, 1, 6001)
        P = np.column_stack(splev(uu, tck))
        s = _largo(P)
        self.perimetro = float(s[-1])
        self._t = s / s[-1]
        self._P = P
        d = np.column_stack(splev(uu, tck, der=1))
        d /= np.linalg.norm(d, axis=1)[:, None]
        self._N = np.column_stack([d[:, 1], -d[:, 0]])   # hacia afuera (sentido antihorario)

    def _medio_alto(self, x):
        x = np.asarray(x, float)
        tapa = np.sqrt(np.clip(1 - (np.abs(x) / self.largo) ** 8, 0.0, 1.0))
        if self.abierta:
            return ANCHO_ABIERTO * np.sqrt(np.clip(1 - (x / self.largo) ** 2, 0.0, 1.0))
        fuera = np.where(x < self.xb0, self.xb0 - x, np.where(x > self.xb1, x - self.xb1, 0.0))
        alto = np.where(x < self.xb0, ALTO_OJO_IZQ, ALTO_OJO_DER)
        return (G / 2 + (alto - G / 2) * _suave(fuera / self.transicion)) * tapa

    def paso(self, x):
        """Cuánto hay de un seno al siguiente donde el primero está en x."""
        x = np.asarray(x, float)
        puntas = (PUNTAS - 1.25) * (np.abs(x) / self.largo) ** 6
        if self.abierta:
            return 1.25 + puntas
        fuera = np.where(x < self.xb0, self.xb0 - x, np.where(x > self.xb1, x - self.xb1, 0.0))
        return G + (OJO - G) * _suave(fuera / self.transicion) + puntas

    def punto(self, t, o) -> np.ndarray:
        """El punto del seno `o` (0 es el primero; puede ser fraccionario) en t ∈ [0, 1)."""
        t = np.mod(np.asarray(t, float), 1.0)
        P = np.column_stack([np.interp(t, self._t, self._P[:, k]) for k in range(2)])
        N = np.column_stack([np.interp(t, self._t, self._N[:, k]) for k in range(2)])
        N /= np.linalg.norm(N, axis=1)[:, None]
        return P + (np.asarray(o, float) * self.paso(P[:, 0]))[:, None] * N

    def t_en(self, x: float, delante: bool = True) -> float:
        """El t donde el primer seno pasa por x, por delante (y < 0) o por detrás."""
        m = self._P[:, 1] < 0 if delante else self._P[:, 1] > 0
        i = np.nonzero(m)[0]
        k = i[np.argmin(np.abs(self._P[i, 0] - x))]
        return float(self._t[k])

    def y_seno(self, x: float, k: int, delante: bool = True) -> float:
        """y del seno k (1 es el primero) en x, por delante o por detrás."""
        t = self.t_en(x, delante)
        ts = np.linspace(t - 0.05, t + 0.05, 401)
        P = self.punto(ts, np.full(len(ts), k - 1.0))
        j = int(np.argmin(np.abs(P[:, 0] - x)))
        return float(P[j, 1])


def _desfase(u, n: int) -> np.ndarray:
    """En qué seno va la espiral (0 es el primero) en la vuelta u: el seno k se cierra sobre el
    extremo en u = k y enseguida pasa, en CAMBIO de vuelta, al siguiente."""
    u = np.asarray(u, float)
    return sum(_suave((u - k - 0.02) / CAMBIO) for k in range(1, n + 1))


# --------------------------------------------------------------------------
# La cuerda de cada hito
# --------------------------------------------------------------------------
@dataclass
class _Lado:
    """Un costado de una vuelta o del seno que rodea la aduja: media vuelta alrededor del tramo
    de afuera de la banda, de abajo arriba (`sube`) o de arriba abajo, mientras avanza de x0 a
    x1. `lado` es -1 por delante y +1 por detrás. Su altura sale de la del tramo que rodea.
    Con `forma` > 1, rodea el tramo casi entero cerca de abajo y avanza después, por encima de
    él: así hace el seno que rodea la aduja, que abajo pasa más a la derecha que arriba."""
    x0: float
    x1: float
    lado: int
    sube: bool
    forma: float = 1.0
    afuera: float = 0.0      # con `forma`, a cuánto del tramo de afuera va

    def x(self, th) -> np.ndarray:
        f = np.asarray(th, float) / math.pi
        # Arriba y abajo no avanza, para empalmar derecho con lo que cruza la banda.
        f = _suave(f ** self.forma if self.sube else 1.0 - (1.0 - f) ** self.forma)
        return self.x0 + (self.x1 - self.x0) * f


class Cuerda:
    """Las cuerdas de un adujado, una por hito, con su secuencia de cruces.

    `secuencias` da la secuencia del método en cada hito y `alias` los hitos que equivalen a
    otro (`senos` y `vueltas`). `trazo(hito, previo)` da los puntos de control del paso."""

    def __init__(self, p: Adujado, variante: str | None = None):
        if variante is not None and variante not in p.VARIANTES:
            raise ValueError(f"el adujado no tiene la variante {variante}")
        self.p, self.variante = p, variante
        n, m = p.senos, p.vueltas
        self.Y = (n - 0.5) * G                       # el tramo de afuera de la banda
        self.x1 = -m * PASO_VUELTA / 2 - 3.0          # arriba, la primera vuelta
        self.xa = self.x1 + m * PASO_VUELTA           # arriba, donde sale la cuerda de las vueltas
        self.xb0 = self.x1 - 1.5                      # la banda
        self.xb1 = self.xa + GIRO + 0.3
        self.xd = self.xb1 + 5.6                      # donde la cuerda llega a la mesa en el ojo
        # Con más senos, la banda se abre más despacio, para que los de afuera no se doblen
        # donde se abre (su curva por dentro es la del primero menos lo que están afuera). Con
        # más vueltas o una transición más larga, la aduja se alarga para que quepan los ojos.
        alto = max(ALTO_OJO_IZQ, ALTO_OJO_DER) - G / 2
        self.transicion = max(TRANSICION, math.sqrt(6 * alto * ((n - 1) * OJO + 1.0)))
        # Por donde el chicote sale del ojo: donde el ojo ya está casi abierto del todo.
        self.xB = max(self.xd + 3 * GIRO + 0.5, self.xb1 + 0.8 * self.transicion)
        self.largo = max(LARGO, self.xB + 4.6, -self.xb0 + 8.3,
                         self.xb1 + self.transicion + 2.3)
        self.abierta = _Aduja(n, True, largo=self.largo)
        self.junta = _Aduja(n, False, self.xb0, self.xb1, self.largo, self.transicion)
        self._afuera: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        hitos = p.hitos()
        self.alias = {"senos": f"seno-{n}", "vueltas": f"vuelta-{m}"}
        self.orden = [h for h in sorted(hitos, key=hitos.get) if h not in self.alias]
        self._etiquetas: dict[tuple, str] = {}
        from ..libre import TrazadoError
        self._pasos, self._errores = {}, {}
        for h in self.orden:
            try:
                self._pasos[h] = self._paso(h)
            except TrazadoError as e:
                self._errores[h] = e
        self.secuencias = {h: self._pasos[h]["secuencia"] if h in self._pasos else ()
                           for h in self.orden}
        for a, h in self.alias.items():
            self.secuencias[a] = self.secuencias[h]

    # --- Los senos ------------------------------------------------------------------
    def _x_punta(self, k: int) -> float:
        """x donde el seno k se cierra sobre el extremo, en la punta izquierda."""
        return -self.largo - PUNTAS * (k - 1)

    def _extremo(self, aduja: _Aduja) -> tuple[_Pieza, float]:
        """El extremo: entra por la izquierda a lo largo de y = 0, pasa bajo las puntas de los
        senos (o sobre ellas) y dentro del primero baja hasta empezarlo, por delante. Devuelve
        la pieza y el t donde empieza el primer seno."""
        n = self.p.senos
        x_cola = self._x_punta(n) - 5.0
        recto = _recta((x_cola, 0.0), (-self.largo + 2.5, 0.0))
        t0 = aduja.t_en(-self.largo + 6.5, delante=True)
        P1 = aduja.punto(np.array([t0]), np.zeros(1))[0]
        P2 = aduja.punto(np.array([t0 + 1e-3]), np.zeros(1))[0]
        curva = _hermite(recto[-1], (1.0, 0.0), P1, P2 - P1, tension=1.2)
        M = np.vstack([recto, curva[1:-1]])
        # El nivel de cada punto: junto a la punta del seno k, bajo él si k es impar y sobre él si
        # es par; en el error, bajo todos.
        nivel = np.zeros(len(M))
        for k in range(1, n + 1):
            cerca = np.abs(M[:, 0] - self._x_punta(k)) < PUNTAS / 2
            encima = k % 2 == 0 and self.variante != "sin-alternar"
            nivel[cerca & (np.abs(M[:, 1]) < 0.5)] = 2.0 if encima else 0.0
        return _Pieza("extremo", M, nivel), t0

    def _espiral(self, aduja: _Aduja, u0: float, u1: float) -> list[_Pieza]:
        """Los senos desde u0 hasta u1, en una pieza por seno: el seno k va desde poco después de
        su lado delantero (u = k - 0.9) hasta poco después de cerrarse sobre el extremo (u = k +
        0.1). Lo que sigue al último es la «entrada» a las vueltas."""
        n = self.p.senos
        du = PASO_MAPA / aduja.perimetro
        u = np.append(np.arange(u0, u1, du), u1)
        P = aduja.punto(u, _desfase(u, n))
        k = np.clip(np.floor(u + 0.9).astype(int), 1, n + 1)
        piezas = []
        for kk in range(1, n + 2):
            en = np.nonzero(k == kk)[0]
            if not len(en):
                continue
            a, b = en[0], en[-1] + 1
            if piezas:
                a -= 1   # comparten el punto donde se unen
            nombre = f"seno-{kk}" if kk <= n else "entrada"
            piezas.append(_Pieza(nombre, P[a:b], 1.0))
        return piezas

    def _resto(self, P0, T0, girar_a=None) -> _Pieza:
        """Lo que sigue de la cuerda: sigue por la mesa en la dirección T0 o, con `girar_a`, gira
        hacia allá con radio 1,5 y sigue."""
        T0 = np.asarray(T0, float) / np.linalg.norm(T0)
        if girar_a is None:
            return _Pieza("resto", _recta(P0, P0 + RESTO * T0), 1.0)
        D = np.asarray(girar_a, float)
        D = D / np.linalg.norm(D)
        curva = _hermite(P0, T0, P0 + 1.5 * (T0 + D), D)
        return _Pieza("resto", np.vstack([curva, _recta(curva[-1], curva[-1] + RESTO * D)[1:]]), 1.0)

    # --- Los costados -----------------------------------------------------------------
    def _y_afuera(self, x, lado: int) -> np.ndarray:
        """y del tramo de afuera de la aduja juntada en x, por delante (-1) o por detrás (+1)."""
        x = np.atleast_1d(np.asarray(x, float))
        if lado not in self._afuera:
            xs = np.linspace(self.xb0 - 2.0, self.largo - 1.0, 300)
            ys = np.array([self.junta.y_seno(float(xx), self.p.senos, lado < 0) for xx in xs])
            self._afuera[lado] = (xs, ys)
        xs, ys = self._afuera[lado]
        return np.interp(x, xs, ys)

    def _borde(self, x: float, lado: int) -> float:
        """Hasta dónde llega en la planta una vuelta que cruza la aduja en x, por delante (-1) o
        por detrás (+1): FUERA más allá del tramo de afuera. Ahí empieza su costado."""
        return float(self._y_afuera(x, lado)[0]) + lado * FUERA

    def _costado(self, nombre: str, lado: _Lado) -> _Pieza:
        """La planta de un costado: θ de 0 a π, con y = y_afuera(x) ± (FUERA + R·sen θ). Es media
        vuelta de radio R alrededor de un eje FUERA más afuera que el tramo: en la planta no toca la
        línea del tramo, y las vueltas lo cruzan antes de llegar al costado. Su altura se pone
        después de apilar lo demás (Cuerda._alturas)."""
        if lado.forma != 1.0:
            # El seno que rodea la aduja avanza mucho a lo largo de ella: va por fuera del tramo
            # en una curva suave, desde abajo, donde sale hacia afuera, hasta arriba, donde vuelve.
            # Sale hacia afuera, sigue el tramo de afuera a LAZO_CURVA de él y vuelve.
            xb, xa = (lado.x0, lado.x1) if lado.sube else (lado.x1, lado.x0)
            g, sx = GIRO, np.sign(xa - xb)
            y_fuera = lambda x: float(self._y_afuera(x, lado.lado)[0]) + lado.lado * lado.afuera
            abajo = np.array([xb, self._borde(xb, lado.lado)])
            arriba = np.array([xa, self._borde(xa, lado.lado)])
            # Las dos esquinas son cuartos de vuelta de radio GIRO; entre ellas, el tramo de
            # afuera a LAZO_CURVA, con empalmes suaves.
            c1 = abajo + np.array([sx * g, 0.0])
            a0 = math.atan2(abajo[1] - c1[1], abajo[0] - c1[0])
            q1 = _arco(c1, g, a0, a0 - sx * lado.lado * math.pi / 2)
            c2 = arriba - np.array([sx * g, 0.0])
            b0 = math.atan2(arriba[1] - c2[1], arriba[0] - c2[0])
            q2 = _arco(c2, g, b0 + sx * lado.lado * math.pi / 2, b0)
            x_1, x_2 = q1[-1, 0] + sx * 2.0, q2[0, 0] - sx * 2.0
            if (x_2 - x_1) * sx > 1.0:
                xs = np.linspace(x_1, x_2, 200)
                medio = np.column_stack([xs, [y_fuera(x) for x in xs]])
                M = np.vstack([q1[:-1], _hermite(q1[-1], q1[-1] - q1[-2], medio[0], medio[1] - medio[0])[:-1],
                               medio[:-1], _hermite(medio[-1], medio[-1] - medio[-2], q2[0], q2[1] - q2[0])[:-1],
                               q2])
            else:   # cerca: de una esquina a la otra
                M = np.vstack([q1[:-1], _hermite(q1[-1], q1[-1] - q1[-2], q2[0], q2[1] - q2[0])[:-1], q2])
            M = _remuestrear(M if lado.sube else M[::-1], PASO_MAPA)
            pz = _Pieza(nombre, M, None)
            pz.lado = lado
            return pz
        th = np.linspace(0.0, math.pi, 60)
        x = lado.x(th)
        y = self._y_afuera(x, lado.lado) + lado.lado * (FUERA + RADIO_LADO * np.sin(th))
        pz = _Pieza(nombre, np.column_stack([x, y]), None)
        pz.lado = lado
        return pz

    # --- Las vueltas ----------------------------------------------------------------
    def _x_vuelta(self, j: int) -> float:
        return self.x1 + (j - 1) * PASO_VUELTA

    def _subida(self, P0, T0) -> _Pieza:
        """De la entrada, por la mesa delante de la banda, al costado delantero de la primera
        vuelta, donde lo alcanza a un tercio de su altura, y de ahí arriba. En 3D: la banda está ahí
        a 1,5 de la mesa."""
        R, x = RADIO_LADO, self.x1
        y_af = float(self._y_afuera(x, -1)[0])
        lado = _Lado(x - PASO_VUELTA / 2, x, -1, True)
        th = np.linspace(math.pi / 2, math.pi, 40)
        costado = np.column_stack([lado.x(th), y_af - FUERA - R * np.sin(th), 1.5 - R * np.cos(th)])
        # Sube de la mesa a la mitad del costado en un arco vertical que llega con su dirección.
        T1 = costado[1] - costado[0]
        fe = math.atan2(T1[2], T1[0])
        Ra = 1.0 / (1.0 - math.cos(fe))
        xc = costado[0, 0] - Ra * math.sin(fe)
        f = np.linspace(0.0, fe, 40)
        arco = np.column_stack([xc + Ra * np.sin(f), np.full(len(f), costado[0, 1]), 0.5 + Ra * (1 - np.cos(f))])
        a = _hermite(np.array([P0[0], P0[1], 0.5]), (T0[0], T0[1], 0.0), arco[0], (1.0, 0.0, 0.0))
        return _Pieza("vuelta-1-sube", np.vstack([a[:-1], arco, costado[1:]]), None)

    def _vueltas(self, hasta: int) -> list[_Pieza]:
        """Las vueltas 1 a `hasta`, desde arriba de la primera hasta abajo de la última, por
        delante. Por arriba van derechas en x; por abajo, PASO_VUELTA/2 más a la derecha."""
        h = PASO_VUELTA / 2
        piezas = []
        for j in range(1, hasta + 1):
            x = self._x_vuelta(j)
            if j > 1:
                piezas.append(self._costado(f"vuelta-{j}-sube", _Lado(x - h, x, -1, True)))
            piezas.append(_Pieza(f"vuelta-{j}-arriba", _recta((x, self._borde(x, -1)), (x, self._borde(x, 1))), 3.0))
            piezas.append(self._costado(f"vuelta-{j}-baja", _Lado(x, x + h, 1, False)))
            piezas.append(_Pieza(f"vuelta-{j}-abajo", _recta((x + h, self._borde(x + h, 1)),
                                                             (x + h, self._borde(x + h, -1))), 0.0))
        return piezas

    # --- Lo que sale de las vueltas ---------------------------------------------------
    def _pierna(self) -> list[_Pieza]:
        """Sale de la última vuelta: sube por delante, pasa por arriba sobre los tramos de
        delante, gira hacia la derecha y sigue por el medio de la banda, entre los dos tramos
        del medio, hasta el ojo, donde llega a la mesa en x = xd."""
        x = self.xa
        sube = self._costado("pierna-sube", _Lado(x - PASO_VUELTA / 2, x, -1, True))
        recto = _recta((x, self._borde(x, -1)), (x, -GIRO))
        giro = _arco((x + GIRO, -GIRO), GIRO, math.pi, math.pi / 2)
        largo = _recta((x + GIRO, 0.0), (self.xd, 0.0))
        return [sube, _Pieza("pierna", np.vstack([recto, giro[1:], largo[1:]]), 2.0)]

    def _chicote(self, y0: float) -> _Pieza:
        """El chicote: sale del ojo hacia el fondo en x = xB, sobre los tramos de detrás."""
        y1 = float(self._y_afuera(self.xB, 1)[0]) + 4.0
        return _Pieza("chicote", _recta((self.xB, y0), (self.xB, y1)), 2.0)

    def _por_el_ojo(self) -> list[_Pieza]:
        """El seno por el ojo: desde xd sigue por la mesa en y = 0, pasa bajo las puntas de los
        senos, da la vuelta más allá y vuelve en y = 2·GIRO bajo ellas; en el ojo gira hacia el
        fondo y sale sobre los tramos de detrás: es el chicote."""
        x_vuelta = -self._x_punta(self.p.senos) + 2.0
        ida = _recta((self.xd, 0.0), (x_vuelta, 0.0))
        vuelta = _arco((x_vuelta, GIRO), GIRO, -math.pi / 2, math.pi / 2)
        regreso = _recta((x_vuelta, 2 * GIRO), (self.xB + GIRO, 2 * GIRO))
        giro = _arco((self.xB + GIRO, 3 * GIRO), GIRO, -math.pi / 2, -math.pi)
        seno = _Pieza("seno-del-ojo", np.vstack([ida, vuelta[1:], regreso[1:], giro[1:]]), 0.0)
        return [seno, self._chicote(3 * GIRO)]

    def _lazo(self, suelto: bool) -> list[_Pieza]:
        """El seno abierto, que rodea la aduja: desde xd gira hacia delante y pasa bajo la banda
        en x = xd + GIRO, sube por delante, pasa por arriba junto a las vueltas, baja por detrás y
        vuelve bajo la banda hasta el medio, donde gira hacia la derecha y sale del ojo por detrás.
        Antes de tirar del chicote (`suelto`) va más alto y más afuera."""
        x_arriba = self.xa + 2 * GIRO
        afuera = LAZO_CURVA + (SUELTO if suelto else 0.0)
        xd, xb = self.xd, self.xd + GIRO
        giro = _arco((xd, -GIRO), GIRO, math.pi / 2, 0.0)
        y_del, y_det = self._borde(xb, -1), self._borde(xb, 1)
        abajo_del = _recta((xb, -GIRO), (xb, y_del))
        ya, yb = self._borde(x_arriba, -1), self._borde(x_arriba, 1)
        abajo_det = _recta((xb, y_det), (xb, GIRO))
        giro2 = _arco((xb + GIRO, GIRO), GIRO, math.pi, 1.5 * math.pi)
        hacia = _recta((xb + GIRO, 0.0), (self.xB - GIRO, 0.0))
        giro3 = _arco((self.xB - GIRO, GIRO), GIRO, -math.pi / 2, 0.0)
        return [_Pieza("lazo-delante", np.vstack([giro, abajo_del[1:]]), 0.0),
                self._costado("lazo-sube", _Lado(xb, x_arriba, -1, True, FORMA_LAZO, afuera)),
                _Pieza("lazo-arriba", _recta((x_arriba, ya), (x_arriba, yb)), 4.0,
                       extra=SUELTO if suelto else 0.0),
                self._costado("lazo-baja", _Lado(x_arriba, xb, 1, False, FORMA_LAZO, afuera)),
                _Pieza("lazo-detras", np.vstack([abajo_det, giro2[1:]]), 0.0),
                _Pieza("lazo-sale", np.vstack([hacia, giro3[1:]]), 0.0),
                self._chicote(GIRO)]

    # --- Un hito ----------------------------------------------------------------------
    def _piezas(self, hito: str) -> list[_Pieza]:
        n = self.p.senos
        if hito.startswith("seno-"):
            k = int(hito.split("-")[1])
            extremo, t0 = self._extremo(self.abierta)
            senos = self._espiral(self.abierta, t0, k + 0.03)
            P = senos[-1].M
            return [extremo] + senos + [self._resto(P[-1], P[-1] - P[-2])]
        extremo, t0 = self._extremo(self.junta)
        u_fin = n + self.junta.t_en(self.x1 - 6.0, delante=True)
        senos = self._espiral(self.junta, t0, u_fin)
        P = senos[-1].M
        if hito == "juntar":
            return [extremo] + senos + [self._resto(P[-1], P[-1] - P[-2], girar_a=(0.0, -1.0))]
        piezas = [extremo] + senos + [self._subida(P[-1], P[-1] - P[-2])]
        if hito.startswith("vuelta-"):
            j = int(hito.split("-")[1])
            x = self._x_vuelta(j) + PASO_VUELTA / 2
            return piezas + self._vueltas(j) + [
                _Pieza("resto", _recta((x, self._borde(x, -1)), (x, self._borde(x, -1) - RESTO)), 0.0)]
        piezas += self._vueltas(self.p.vueltas) + self._pierna()
        if hito == "por-el-ojo":
            return piezas + self._por_el_ojo()
        return piezas + self._lazo(suelto=hito == "por-encima")

    def _paso(self, hito: str) -> dict:
        piezas = self._piezas(hito)
        # Cada pieza, muestreada pareja a lo largo (los costados ya van parejos en θ).
        for pz in piezas:
            if pz.lado is not None or len(pz.M) < 2:
                continue
            s0 = _largo(pz.M)
            M = _remuestrear(pz.M, PASO_MAPA)
            if pz.nivel is not None and not np.isscalar(pz.nivel):
                s1 = np.linspace(0.0, s0[-1], len(M))
                i = np.clip(np.searchsorted(s0, s1), 0, len(s0) - 1)
                pz.nivel = np.asarray(pz.nivel)[i]
            pz.M = M
        partes, cual = [], []
        for k, pz in enumerate(piezas):
            M = pz.M if pz.M.shape[1] == 3 else np.column_stack([pz.M, np.full(len(pz.M), np.nan)])
            if partes and np.linalg.norm(M[0, :2] - partes[-1][-1, :2]) < 1e-6:
                M = M[1:]
            partes.append(M)
            cual.append(np.full(len(M), k))
        X, pieza = np.vstack(partes), np.concatenate(cual)
        X[:, 2] = self._alturas(X, pieza, piezas)
        s = _largo(X)
        cruces = self._cruces(X, s, pieza, piezas)
        return {"X": X, "s": s, "pieza": pieza, "piezas": piezas, "cruces": cruces,
                "secuencia": self._secuencia(cruces)}

    def _alturas(self, X, pieza, piezas) -> np.ndarray:
        """La altura de cada punto. Lo que tiene nivel se apila: un punto que en la planta queda
        a menos de HOLGURA de un punto de nivel más bajo (que no sea su vecino a lo largo de la
        cuerda) va sobre él, tanto como pide el contacto: √(HOLGURA² − d²) más arriba, a una
        distancia d en la planta. Sube y baja con subidas y bajadas suaves dentro de cada tramo
        seguido de piezas con nivel. Después, los costados rodean el tramo de afuera a la altura
        que quedó, y la subida a la primera vuelta va como está trazada."""
        N = len(X)
        nivel = np.full(N, np.nan)
        for k, pz in enumerate(piezas):
            en = pieza == k
            if pz.nivel is not None:
                nivel[en] = pz.nivel if np.isscalar(pz.nivel) else np.asarray(pz.nivel)[-en.sum():]
        con = ~np.isnan(nivel)
        # El largo a lo largo de la cuerda, con los costados a su altura aproximada.
        Z = np.where(np.isnan(X[:, 2]), 0.5, X[:, 2])
        s = _largo(np.column_stack([X[:, :2], Z]))
        idx = np.nonzero(con)[0]
        arbol = cKDTree(X[idx, :2])
        debajo = {}
        for a, vecinos in zip(idx, arbol.query_ball_point(X[idx, :2], HOLGURA)):
            j = idx[vecinos]
            j = j[(nivel[j] < nivel[a]) & (np.abs(s[j] - s[a]) > VECINO)]
            if len(j):
                d = np.linalg.norm(X[j, :2] - X[a, :2], axis=1)
                debajo[a] = (j, np.sqrt(np.clip(HOLGURA ** 2 - d ** 2, 0.0, None)))
        # Los tramos seguidos de piezas con nivel: las rampas no pasan de uno a otro.
        cortes = np.nonzero(np.diff(con.astype(int)) != 0)[0] + 1
        tramos = [t for t in np.split(np.arange(N), cortes) if con[t[0]]]
        paso = float(np.median(np.diff(s)))
        es_extremo = np.array([pz.nombre == "extremo" for pz in piezas])[pieza]
        h = np.zeros(N)
        for _ in range(16):
            crudo = np.zeros(N)
            for a, (j, sobre) in debajo.items():
                crudo[a] = float((h[j] + sobre).max())
            # Entre dos pasadas por encima cercanas de una misma pieza, la cuerda no baja. El
            # extremo sí: pasa alternando sobre y bajo las puntas de los senos.
            crudo = np.where(es_extremo, crudo, _puentes(crudo, pieza, paso))
            nuevo = np.zeros(N)
            for t in tramos:
                nuevo[t] = gaussian_filter1d(_rampas(crudo[t], paso), SUAVE / paso, mode="nearest")
            if np.allclose(nuevo, h, atol=1e-6):
                break
            h = nuevo
        z = np.where(con, 0.5 + h, X[:, 2])
        for k, pz in enumerate(piezas):
            if pz.extra:
                z[pieza == k] += pz.extra
        # Los costados, alrededor del tramo de afuera del seno más grande.
        afuera = np.nonzero(np.array([pz.nombre == f"seno-{self.p.senos}" for pz in piezas])[pieza])[0]
        arbol_af = cKDTree(X[afuera, :2])
        for k, pz in enumerate(piezas):
            if pz.lado is None:
                continue
            en = np.nonzero(pieza == k)[0]
            lado = pz.lado
            if lado.forma != 1.0:
                # Sube (o baja) suave entre lo de antes y lo de después.
                z0 = z[en[0] - 1] if con[en[0] - 1] else 0.5
                z1 = z[en[-1] + 1] if en[-1] + 1 < N and con[en[-1] + 1] else 0.5
                z[en] = z0 + (z1 - z0) * _suave(np.linspace(0.0, 1.0, len(en)))
                continue
            th = np.linspace(0.0, math.pi, len(pz.M))[-len(en):]
            x = lado.x(th)
            _, j = arbol_af.query(np.column_stack([x, self._y_afuera(x, lado.lado)]))
            zc = z[afuera[j]]
            z[en] = zc - RADIO_LADO * np.cos(th) if lado.sube else zc + RADIO_LADO * np.cos(th)
        # Lo que no se apila (los costados y la subida) empalma con lo de antes y lo de después:
        # se corrige su altura, repartiendo la diferencia a lo largo de la pieza.
        for k, pz in enumerate(piezas):
            if pz.nivel is not None:
                continue
            en = np.nonzero(pieza == k)[0]
            f = _suave(np.linspace(0.0, 1.0, len(en)))
            d0 = z[en[0] - 1] - z[en[0]] if en[0] > 0 and con[en[0] - 1] else 0.0
            d1 = z[en[-1] + 1] - z[en[-1]] if en[-1] + 1 < N and con[en[-1] + 1] else 0.0
            z[en] += (1 - f) * d0 + f * d1
        return z

    def _cruces(self, X, s, pieza, piezas) -> list[dict]:
        """Los cruces de la cuerda vistos desde arriba, con la pieza de encima y su etiqueta. La
        etiqueta es la de las dos piezas y el lado de la aduja donde se cruzan (delante, el
        medio o detrás): así un cruce la conserva de un paso a otro."""
        out = []
        for sa, sb, seno, p in cruces_planta(X, s):
            ia, ib = _indice(s, sa), _indice(s, sb)
            a, b = piezas[pieza[ia]], piezas[pieza[ib]]
            za, zb = _en(s, X[:, 2], sa), _en(s, X[:, 2], sb)
            lado = 0 if abs(p[1]) < 0.3 else int(np.sign(p[1]))
            clave = (a.nombre, b.nombre, lado)
            etiqueta = self._etiquetas.setdefault(clave, str(len(self._etiquetas) + 1))
            out.append({"sa": sa, "sb": sb, "seno": seno, "encima": za > zb, "lugar": p,
                        "etiqueta": etiqueta, "piezas": (a.nombre, b.nombre),
                        "alturas": (za, zb)})
        etiquetas = [c["etiqueta"] for c in out]
        if len(set(etiquetas)) != len(etiquetas):
            from ..libre import TrazadoError
            repetidas = sorted({e for e in etiquetas if etiquetas.count(e) > 1})
            raise TrazadoError(f"dos cruces con la misma etiqueta: {', '.join(repetidas)}")
        return out

    def _secuencia(self, cruces) -> tuple[str, ...]:
        pasadas = []
        for c in cruces:
            pasadas.append((c["sa"], c["etiqueta"] + ("O" if c["encima"] else "U")))
            pasadas.append((c["sb"], c["etiqueta"] + ("U" if c["encima"] else "O")))
        return tuple(t for _, t in sorted(pasadas))

    # --- El paso ----------------------------------------------------------------------
    def trazo(self, hito: str, previo: str | None) -> TrazoDePaso:
        """Los puntos de control del paso, todos sobre la mesa. Se resalta lo que agrega."""
        hito = self.alias.get(hito, hito)
        previo = self.alias.get(previo, previo)
        if self.variante is not None and self.orden.index(hito) > self.orden.index(f"seno-{self.p.senos}"):
            raise ValueError("la variante sin-alternar se ve solo en los senos")
        if hito in self._errores:
            raise self._errores[hito]
        d = self._pasos[hito]
        paso = max(1, int(round(PASO_CONTROL / PASO_MAPA)))
        idx = np.unique(np.r_[np.arange(0, len(d["X"]), paso), len(d["X"]) - 1])
        P, sc = d["X"][idx], d["s"][idx]
        a, b = self._resaltado(hito, previo, d)
        inicio = None if a is None else int(np.searchsorted(sc, a - 1e-9))
        fin = len(P) - 1 if b is None else min(int(np.searchsorted(sc, b - 1e-9)), len(P) - 1)
        return TrazoDePaso(P, np.full(len(P), MESA), fin, inicio, quietos=self._quietos(d)[idx])

    def _quietos(self, d) -> np.ndarray:
        """Lo que no se relaja: toda la cuerda. Al relajar, las vueltas tiraban de la cuerda y la
        comprimían hasta los senos y el seno por el ojo, que se doblaban. La plantilla ya la traza
        sin que nada se toque ni se doble de más (Cuerda._alturas), como la vuelta de braza del
        amarre diagonal."""
        return np.ones(len(d["X"]), bool)

    def _resaltado(self, hito, previo, d) -> tuple[float | None, float | None]:
        """Desde y hasta dónde se resalta, a lo largo de la cuerda: None al principio es desde
        la punta del extremo; None al final, hasta el final."""
        s, pieza, piezas = d["s"], d["pieza"], d["piezas"]

        def inicio_de(nombre):
            k = [i for i, pz in enumerate(piezas) if pz.nombre == nombre]
            return float(s[pieza == k[0]].min()) if k else None

        def fin_de(nombre):
            k = [i for i, pz in enumerate(piezas) if pz.nombre == nombre]
            return float(s[pieza == k[0]].max()) if k else None

        if hito.startswith("seno-"):
            k = int(hito.split("-")[1])
            k0 = int(previo.split("-")[1]) if previo and previo.startswith("seno-") else 0
            return inicio_de(f"seno-{k0 + 1}"), fin_de(f"seno-{k}")
        if hito == "juntar":
            return None, fin_de("entrada")
        if hito.startswith("vuelta-"):
            j = int(hito.split("-")[1])
            j0 = int(previo.split("-")[1]) if previo and previo.startswith("vuelta-") else 0
            a = inicio_de(f"vuelta-{j0 + 1}-sube") if j0 else inicio_de("entrada")
            return a, fin_de(f"vuelta-{j}-abajo")
        if hito == "por-el-ojo":
            return inicio_de("pierna-sube"), None
        if hito == "por-encima":
            return inicio_de("lazo-delante"), fin_de("lazo-sale")
        return inicio_de("chicote"), None


def _indice(s, x) -> int:
    return int(min(max(np.searchsorted(s, x) - 1, 0), len(s) - 1))


def _en(s, v, x) -> float:
    return float(np.interp(x, s, v))


def cruces_planta(X, s) -> list[tuple[float, float, float, tuple[float, float]]]:
    """Los cruces de una cuerda vista desde arriba: para cada uno, la posición a lo largo de la
    cuerda (`s`) de sus dos pasadas, el |sen| del ángulo entre ellas y dónde se cruzan. Como
    nudos.cruces.cruces_2d, pero solo compara los segmentos que están cerca, con un árbol."""
    P = X[:, :2]
    A, B = P[:-1], P[1:]
    largo = np.linalg.norm(B - A, axis=1)
    pares = cKDTree((A + B) / 2).query_pairs(float(largo.max()) * 1.01 + 1e-9, output_type="ndarray")
    if not len(pares):
        return []
    i, j = np.minimum(pares[:, 0], pares[:, 1]), np.maximum(pares[:, 0], pares[:, 1])
    ok = j - i >= 2
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
        a, b = i[k], j[k]
        sa = float(s[a] + t[k] * (s[a + 1] - s[a]))
        sb = float(s[b] + v[k] * (s[b + 1] - s[b]))
        if any(abs(x - sa) < 0.3 and abs(y - sb) < 0.3 for x, y, _, _ in out):
            continue
        seno = float(abs(rxs[k]) / (np.linalg.norm(rr[k]) * np.linalg.norm(ss[k])))
        p = A[a] + t[k] * rr[k]
        out.append((sa, sb, seno, (float(p[0]), float(p[1]))))
    return sorted(out)


def buscar_en_la_mesa(X, h: float, zonas=None):
    """Los cruces de la cuerda de un paso, vistos desde arriba, y la altura de sus dos
    pasadas, como en un nudo libre."""
    from ..cruces import Cruce
    s = np.arange(len(X)) * h
    cruces, alturas = [], []
    for sa, sb, seno, p in cruces_planta(X, s):
        cruces.append(Cruce(sa, sb, p, seno))
        alturas.append((_en(s, X[:, 2], sa), _en(s, X[:, 2], sb)))
    return cruces, alturas
