"""Plantilla del amarre diagonal, sobre la cruz del amarre cuadrado (anfitrión «cruz»).

El método es el del diseño en tasks/plan.md («El amarre diagonal (tanda 4)»): una vuelta de
braza alrededor de los dos palos, vueltas en una diagonal, vueltas en la otra, ahorcados entre
los palos y un ballestrinque de cierre en el palo de arriba. Los ahorcados y el cierre son los
del amarre cuadrado (amarre.ahorcados_y_cierre).

Cada vuelta de una diagonal va en un plano vertical a 45° de los dos palos. Sobre cada palo
sigue el corte del plano con el palo; entre los palos baja por la tangente común de los dos
cortes, como una cuerda tensa, suavizada como las esquinas del cuadrado. Cada vuelta nueva pasa
a su plano en la esquina con que baja entre los palos, como en el cuadrado. La segunda diagonal
pasa por fuera de la primera: en su plano, cada cruce con una vuelta de la primera es un
obstáculo que su envolvente convexa deja por dentro, así que se aparta del palo solo donde
cruza.

Se calcula primero en el «marco del diseño», el de las fotos de la fuente: la primera diagonal
va de delante a la derecha hacia atrás a la izquierda, con la vuelta de braza en la cara de
delante del palo de arriba, a la derecha del de abajo. Ese marco se refleja de izquierda a
derecha antes de los ahorcados, que salen de la segunda diagonal por delante a la derecha y
terminan con el cierre a la derecha, como en el cuadrado. Con el cierre a la izquierda todo se
refleja otra vez y queda como en las fotos.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .amarre import (CUADRANTES, NUMEROS, RADIO_ESQUINA, Cuerda, Extremo, _Palos, _extremo,
                     _hermite, _resto, _tangente, _unit, ahorcados_y_cierre, alturas_de_ahorcados)
from .trazo import ABAJO, ARRIBA, CINTURA, Trazo

_CAMPOS = {"tipo", "vueltas", "ahorcados", "cierre"}
VUELTAS = (2, 3, 4)   # en cada diagonal; la fuente pide «tres o cuatro»


@dataclass(frozen=True)
class AmarreDiagonal:
    vueltas: int     # en cada diagonal
    ahorcados: int   # entre los palos, alrededor de las vueltas
    cierre: Extremo  # ballestrinque de cierre

    tipo = "amarre-diagonal"
    ANFITRION = "cruz"
    # El error común que sabe construir, con el primer hito desde el que se ve: los ahorcados
    # por encima del palo de arriba, como en el amarre cuadrado.
    VARIANTES = {"ahorcados-por-fuera": "ahorcado-1"}
    # En el paso de la vuelta de braza la parte larga de la cuerda es el firme; desde la
    # primera vuelta se mueve la parte larga y su punta es el chicote.
    CON_FIRME = ("inicio",)
    # Bajo el palo de abajo se cruzan las dos diagonales: dos capas de cuerda.
    CAPAS_DEBAJO = 2

    @classmethod
    def leer(cls, datos: dict, falla) -> AmarreDiagonal:
        sobran = set(datos) - _CAMPOS
        if sobran:
            raise falla(f"campos desconocidos: {', '.join(sorted(sobran))}")
        v = datos.get("vueltas")
        if not isinstance(v, int) or isinstance(v, bool) or v not in VUELTAS:
            raise falla(f"«vueltas» es el número de vueltas en cada diagonal, de {min(VUELTAS)} "
                        f"a {max(VUELTAS)}")
        a = datos.get("ahorcados")
        if not isinstance(a, int) or isinstance(a, bool) or a not in NUMEROS:
            raise falla(f"«ahorcados» es un número entero de {min(NUMEROS)} a {max(NUMEROS)}")
        cierre = _extremo(datos.get("cierre"), "cierre", falla)
        if cierre.poste != "arriba":
            raise falla("por ahora el ballestrinque de cierre va en el palo de arriba")
        return cls(vueltas=v, ahorcados=a, cierre=cierre)

    def hitos(self) -> dict[str, int]:
        """Los valores de `hasta`, con su posición en la cuerda. `vueltas`, `segundas` y
        `ahorcados` son lo mismo que el último de cada uno."""
        out = {"inicio": 1}
        k = 1
        for nombre, plural, total in (("vuelta", "vueltas", self.vueltas),
                                      ("segunda", "segundas", self.vueltas),
                                      ("ahorcado", "ahorcados", self.ahorcados)):
            for i in range(1, total + 1):
                k += 1
                out[f"{nombre}-{i}"] = k
            out[plural] = k
        out["cierre-1"] = k + 1
        out["cierre"] = k + 2
        return out

    def medidas(self) -> dict[str, str]:
        return {"vueltas": NUMEROS[self.vueltas], "ahorcados": NUMEROS[self.ahorcados]}


# --------------------------------------------------------------------------
# Medidas, en diámetros de cuerda
# --------------------------------------------------------------------------
PASO_DIAGONAL = 1.1     # entre dos vueltas vecinas de una diagonal, de eje a eje
APARTE_BRAZA = 2.0      # entre la vuelta de braza y la primera vuelta, por el chicote que la rodea
SOBRE = 1.1             # en su plano, lo que deja la segunda diagonal alrededor de cada cruce
TRAMO_BRAZA = 3.4       # en la cara de delante, del firme al tramo con las vueltas del chicote
PASO_HELICE = 1.6       # lo que avanza el chicote en cada vuelta alrededor de su tramo
RADIO_HELICE = 1.2      # del eje de un tramo al del chicote que lo rodea: algo flojo, para que
                        # el chicote no se doble con radio menor que 1,1 al relajar
GIRO_BRAZA = 1.5       # radio con que el chicote dobla hacia abajo después de rodear el firme
VUELTAS_CHICOTE = 2.5   # vueltas del chicote alrededor de su tramo: 5 cruces
RAMPA = 42.0            # grados en que un tramo se aparta un diámetro del palo de arriba
RAMPA_FIRME = 42.0      # lo mismo en el firme, donde el chicote pasa por debajo: más suave
MARGEN = 6.0            # grados entre el último cruce de un tramo y lo que sigue en él
FUERA_ERROR = 0.7       # en el error, como amarre.FUERA (ver cuerda())
CABE = 0.4              # lo que deja, del radio de los palos, la vuelta más lejos del cruce
PASO_ANG = 1.5          # grados entre dos puntos de un corte
# Hacia dónde sale el resto de la cuerda en cada hito, sobre la mesa (en el marco del cuadrado,
# antes del reflejo del cierre).
SALIDAS = {"inicio": (0.0, -1.0), "vuelta": (-0.5, -0.85), "segunda": (0.6, -0.8),
           "ahorcado": (1.0, -0.2), "cierre-1": (0.3, -1.0)}
ESPEJO = np.array([-1.0, 1.0, 1.0])   # del marco del diseño al del cuadrado
QUIETA = 10   # se suma a la zona de una pieza que no se relaja, hasta muestrear la cuerda


@dataclass
class _Corte:
    """Un corte muestreado de un palo con un plano: el ángulo de cada punto alrededor del palo
    (nan en los de un obstáculo), sus coordenadas en el plano y en el espacio."""
    ang: np.ndarray
    plano: np.ndarray
    xyz: np.ndarray


class _Geo:
    """Puntos y cortes de las diagonales sobre la cruz, en el marco del diseño.

    Un plano es (sig, c): x + sig·y = c. La primera diagonal tiene sig = +1, la segunda −1.
    En el plano, s = (x − sig·y)/√2 va a lo largo y z es la altura. Sobre el palo de arriba un
    punto está en el ángulo a (grados) alrededor de su eje, desde +y hacia arriba: 90 es su
    cara de arriba, 180 la de delante. Sobre el de abajo, en el ángulo b desde +x hacia
    arriba: 0 es su cara de la derecha y 270 la de abajo. Lo que se aparta del palo de arriba
    se aparta de su eje sin moverse a lo largo del palo: su lugar en el mapa no cambia."""

    def __init__(self, cruz):
        self.rb, self.zb, self.zt = cruz.rb, cruz.zb, cruz.zt

    def arriba(self, sig, c, a, h=0.0):
        a = np.radians(np.asarray(a, float))
        return self.en_mapa(c - sig * self.rb * np.cos(a), np.degrees(a), h)

    def en_mapa(self, u, a, h=0.0):
        """Sobre el palo de arriba, en x = u y el ángulo a, apartado h del palo."""
        a = np.radians(np.asarray(a, float))
        r = self.rb + np.asarray(h, float)
        x, y, z = np.broadcast_arrays(np.asarray(u, float), r * np.cos(a), self.zt + r * np.sin(a))
        return np.stack([x, y, z], axis=-1)

    def abajo(self, sig, c, b):
        b = np.radians(np.asarray(b, float))
        return np.stack([self.rb * np.cos(b), sig * (c - self.rb * np.cos(b)),
                         self.zb + self.rb * np.sin(b)], axis=-1)

    def al_mapa(self, P) -> np.ndarray:
        """De un punto a sus coordenadas en el mapa del palo de arriba: (x, ángulo, apartado)."""
        P = np.atleast_2d(P)
        return np.column_stack([P[:, 0], np.degrees(np.arctan2(P[:, 2] - self.zt, P[:, 1])) % 360.0,
                                np.hypot(P[:, 1], P[:, 2] - self.zt) - self.rb])

    def hermite_mapa(self, P0, P1, t0, t1) -> np.ndarray:
        """Una curva suave sobre el palo de arriba de P0 a P1, que sale en la dirección t0 y
        llega en la t1: la curva de Hermite en el mapa del palo (x, arco, apartado), así que se
        dobla con el palo y no lo atraviesa."""
        m0, m1 = self.al_mapa(P0)[0], self.al_mapa(P1)[0]
        m1[1] = m0[1] + ((m1[1] - m0[1] + 180.0) % 360.0 - 180.0)
        r = self.rb + 0.5 * (m0[2] + m1[2])
        def tangente(m, tv):
            a = math.radians(m[1])
            return np.array([tv[0], -math.sin(a) * tv[1] + math.cos(a) * tv[2],
                             math.cos(a) * tv[1] + math.sin(a) * tv[2]])
        Q0 = np.array([m0[0], math.radians(m0[1]) * r, m0[2]])
        Q1 = np.array([m1[0], math.radians(m1[1]) * r, m1[2]])
        C = _hermite(Q0, Q1, _unit(tangente(m0, t0)), _unit(tangente(m1, t1)))
        return self.en_mapa(C[:, 0], np.degrees(C[:, 1] / r), C[:, 2])

    @staticmethod
    def al_plano(sig, P):
        P = np.atleast_2d(P)
        return np.column_stack([(P[:, 0] - sig * P[:, 1]) / math.sqrt(2), P[:, 2]])

    @staticmethod
    def del_plano(sig, c, Q):
        Q = np.atleast_2d(Q)
        return np.column_stack([(c + math.sqrt(2) * Q[:, 0]) / 2,
                                sig * (c - math.sqrt(2) * Q[:, 0]) / 2, Q[:, 1]])

    def corte(self, palo, sig, c, levantar=None, obstaculos=()) -> _Corte:
        """El corte de un palo («arriba» o «abajo») con el plano, muestreado, por fuera de los
        obstáculos (puntos del plano, alrededor de los que deja SOBRE). `levantar(a)` aparta
        cada punto del palo de arriba."""
        ang = np.arange(0.0, 360.0, PASO_ANG)
        if palo == "arriba":
            h = 0.0 if levantar is None else np.array([levantar(x) for x in ang])
            P = self.arriba(sig, c, ang, h)
        else:
            P = self.abajo(sig, c, ang)
        k = _Corte(ang, self.al_plano(sig, P), P)
        if len(obstaculos):
            t = np.radians(np.arange(0.0, 360.0, 10.0))
            anillo = SOBRE * np.column_stack([np.cos(t), np.sin(t)])
            Q = np.vstack([q + anillo for q in obstaculos])
            k = _Corte(np.concatenate([ang, np.full(len(Q), np.nan)]), np.vstack([k.plano, Q]),
                       np.vstack([P, self.del_plano(sig, c, Q)]))
        return k


def _envolvente(P) -> list[int]:
    """Los vértices de la envolvente convexa de los puntos P (2D), en sentido antihorario."""
    from scipy.spatial import ConvexHull
    return [int(i) for i in ConvexHull(P).vertices]


def _puente(arriba: _Corte, abajo: _Corte, lado: int) -> tuple[int, int]:
    """La tangente común de dos cortes del lado `lado` del plano (+1: s > 0): el índice del
    punto donde deja el corte de arriba y el del punto donde llega al de abajo."""
    P = np.vstack([arriba.plano, abajo.plano])
    v = _envolvente(P)
    n = len(arriba.plano)
    mejor = None
    for k in range(len(v)):
        i, j = v[k], v[(k + 1) % len(v)]
        if (i < n) != (j < n):
            s = lado * (P[i, 0] + P[j, 0])
            if mejor is None or s > mejor[0]:
                mejor = (s, i, j)
    if mejor is None:
        raise ValueError("los dos cortes no tienen tangente común")
    _, i, j = mejor
    return (i, j - n) if i < n else (j, i - n)


def _borde(k: _Corte, desde: int, hasta: int, sentido: int) -> np.ndarray:
    """Los puntos del borde de un corte (su envolvente convexa) de `desde` a `hasta`, en sentido
    antihorario (+1) u horario (−1) en el plano."""
    v = _envolvente(k.plano)
    if desde not in v or hasta not in v:
        raise ValueError("el punto no está en el borde del corte")
    if sentido < 0:
        v = v[::-1]
    i, j = v.index(desde), v.index(hasta)
    return k.xyz[[v[(i + q) % len(v)] for q in range((j - i) % len(v) + 1)]]


def _rampa(a, a0, a1) -> float:
    """Suave, de 0 en a0 a 1 en a1."""
    u = float(np.clip((a - a0) / (a1 - a0), 0.0, 1.0))
    return u * u * (3 - 2 * u)


def _dir(P, al_final=True) -> np.ndarray:
    return _unit(P[-1] - P[-3]) if al_final else _unit(P[2] - P[0])


def _angulos(a0, a1) -> np.ndarray:
    return np.linspace(a0, a1, max(2, int(abs(a1 - a0) / PASO_ANG) + 1))


def _cruce_arriba(c, d, rb) -> float:
    """El ángulo (grados) sobre el palo de arriba donde la vuelta de la primera diagonal en el
    plano c cruza la de la segunda en el plano d."""
    return math.degrees(math.acos(float(np.clip((c - d) / (2 * rb), -1, 1))))


def _entre(a, desde) -> float:
    """El ángulo a, más o menos 360, en la vuelta que empieza en `desde`."""
    return desde + (a - desde) % 360.0


def _cuadrante(P) -> int:
    x, y = float(np.mean(P[:, 0])), float(np.mean(P[:, 1]))
    return next(q for q, (sx, sy) in CUADRANTES.items() if sx * x > 0 and sy * y > 0)


@dataclass
class _Esquina:
    """Una esquina de una vuelta entre los palos, para los ahorcados: su nombre, en qué
    cuadrante va (CUADRANTES, en el marco del cuadrado), si sube y sus puntos. Los ahorcados
    la rodean por fuera, y cada uno la cruza una vez."""
    nombre: str
    cuadrante: int
    sube: int
    P: np.ndarray


class _Cuerda:
    """La cuerda del amarre en piezas, en el orden de la cuerda, con sus hitos y las pasadas
    por cada cruce, para la secuencia del método."""

    def __init__(self):
        self.piezas: list[tuple[np.ndarray, int]] = []
        self.marcas: dict[str, int] = {}
        self.eventos: list[tuple] = []
        self.esquinas: list[tuple[str, int, list[int]]] = []   # (nombre, sube, piezas)
        self.quietas: set[int] = set()                    # las piezas que no se relajan

    @property
    def fin(self) -> np.ndarray:
        return self.piezas[-1][0][-1]

    def poner(self, P, zona, quieta=False) -> None:
        P = np.atleast_2d(np.asarray(P, float))
        if self.piezas and np.linalg.norm(P[0] - self.fin) < 1e-9:
            P = P[1:]
        if len(P):
            self.piezas.append((P, zona))
            if quieta:
                self.quietas.add(len(self.piezas) - 1)

    def marcar(self, nombre) -> None:
        self.marcas[nombre] = len(self.piezas) - 1
        self.eventos.append(("hito", nombre))

    def pasa(self, cruce, encima: bool) -> None:
        self.eventos.append(("pasa", cruce, encima))

    def esquina(self, nombre, sube, P0, P1, t0, t1, antes=None) -> None:
        """Una esquina entre los palos, de P0 a P1. `antes`, si lo hay, es lo que la empieza
        y no se relaja: el final del tramo de la vuelta de braza, que baja entre los palos."""
        piezas = []
        if antes is not None:
            self.poner(antes, CINTURA, quieta=True)
            piezas.append(len(self.piezas) - 1)
        self.poner(_hermite(P0, P1, t0, t1), CINTURA)
        piezas.append(len(self.piezas) - 1)
        self.esquinas.append((nombre, sube, piezas))
        self.eventos.append(("esquina", nombre, sube))


def cuerda(p: AmarreDiagonal, cruz, variante: str | None = None) -> Cuerda:
    """Calcula la cuerda entera del amarre diagonal sobre la cruz (nudos/anfitrion.py). Con
    `variante`, la del error común (AmarreDiagonal.VARIANTES), que solo cambia los ahorcados."""
    if variante is not None and variante not in AmarreDiagonal.VARIANTES:
        raise ValueError(f"el amarre diagonal no tiene la variante {variante}")
    por_fuera = variante == "ahorcados-por-fuera"
    n, m = p.vueltas, p.ahorcados
    g = _Geo(cruz)
    rb = cruz.rb
    dc = PASO_DIAGONAL * math.sqrt(2)
    # La primera diagonal: la vuelta de braza (0) y las n vueltas, en planos x + y = c, de mayor
    # a menor y centrados en el cruce. La vuelta de braza va algo más lejos de la primera
    # vuelta, por el chicote que rodea el firme.
    c = [0.0] + [APARTE_BRAZA * math.sqrt(2) + i * dc for i in range(n)]
    medio = (c[0] + c[-1]) / 2
    c = [medio - x for x in c]
    # La segunda diagonal, en planos x − y = d, de mayor a menor.
    d = [((n - 1) / 2 - l) * dc for l in range(n)]
    # Cada vuelta tiene que bajar entre los palos, no por encima de uno: su plano pasa a menos de
    # un radio del cruce.
    if max(abs(x) for x in c + d) > rb - CABE:
        raise ValueError(f"las {n} vueltas de cada diagonal no caben entre palos de radio "
                         f"{cruz.radio:g}: hace falta un palo más grueso o menos vueltas")
    k = _Cuerda()

    # --- La vuelta de braza y la primera diagonal ---
    braza = _VueltaDeBraza(g, c[0], c[0] + TRAMO_BRAZA, max(_cruce_arriba(c[0], x, rb) for x in d))
    braza.chicote(k)
    T = [g.corte("arriba", 1, x) for x in c]
    B = [g.corte("abajo", 1, x) for x in c]
    E = g.corte("arriba", 1, braza.c_e, levantar=braza.h_tramo)
    # La primera diagonal termina en la cara de delante del palo de arriba, un poco después del
    # último cruce de la última vuelta, y de ahí baja a la segunda.
    a_cambio = max(_cruce_arriba(c[n], x, rb) for x in d) + 2 * MARGEN
    previo = None   # la vuelta anterior sobre el palo de arriba, hasta donde baja
    for i in range(n + 1):
        # Baja entre los palos delante a la derecha (s > 0), desde el plano anterior: la
        # vuelta de braza, desde su tramo con las vueltas del chicote.
        if i == 0:
            it, ib = _puente(E, B[0], +1)
            previo, final_tramo = braza.tramo(k, _entre(E.ang[it], 90.0))
        else:
            _, ib = _puente(T[i - 1], B[i], +1)
        # Sube entre los palos atrás a la izquierda (s < 0), en su plano.
        it2, ib2 = _puente(T[i], B[i], -1)
        # De la cara de la derecha (b cerca de 0) a la de la izquierda, pasando por abajo (−90).
        bajo = g.abajo(1, c[i], _angulos(_entre(B[i].ang[ib], -90.0),
                                         _entre(B[i].ang[ib2], -90.0) - 360.0))
        k.esquina(f"d1-{i}-baja", -1, previo[-1], bajo[0], _dir(previo), _dir(bajo, False),
                  antes=final_tramo if i == 0 else None)
        # Por debajo del palo de abajo, de derecha a izquierda; ahí la cruza cada vuelta de la
        # segunda diagonal, de la primera a la última.
        k.poner(bajo, ABAJO)
        for l in range(n):
            k.pasa(("B", i, l), False)
        # Por encima del palo de arriba, de atrás hacia delante, hasta donde baja la vuelta
        # siguiente (o, la última, hasta donde empieza la segunda diagonal). Ahí la cruzan las
        # vueltas de la segunda diagonal, de la última a la primera.
        a_llega = _entre(T[i].ang[it2], -90.0)   # atrás, cerca de 0
        a_hasta = a_cambio if i == n else _entre(T[i].ang[_puente(T[i], B[i + 1], +1)[0]], 90.0)
        A = _angulos(a_llega, a_hasta)
        sobre = g.arriba(1, c[i], A, [braza.h_firme(x) for x in A] if i == 0 else 0.0)
        k.esquina(f"d1-{i}-sube", +1, bajo[-1], sobre[0], _dir(bajo), _dir(sobre, False))
        if i == 0:
            # El firme sale de la vuelta de braza por la cara de delante, donde el chicote lo
            # rodea, y el paso de la vuelta de braza termina un poco más abajo.
            # Donde el chicote lo rodea, el firme no se relaja, como la vuelta de braza.
            j0, j1, j = (int(np.searchsorted(A, x)) for x in (*braza.firme_quieto, braza.a_fin_inicio))
            k.poner(sobre[:j0 + 1], ARRIBA)
            for l in range(n - 1, -1, -1):
                k.pasa(("T", 0, l), False)
            k.poner(sobre[j0:j1 + 1], ARRIBA, quieta=True)
            braza.firme(k)
            k.poner(sobre[j1:j + 1], ARRIBA)
            k.marcar("inicio")
            k.poner(sobre[j:], ARRIBA)
        else:
            k.poner(sobre, ARRIBA)
            for l in range(n - 1, -1, -1):
                k.pasa(("T", i, l), False)
            k.marcar(f"vuelta-{i}")
        previo = sobre
    return _segunda_y_resto(p, g, cruz, c, d, k, a_cambio, por_fuera)


class _VueltaDeBraza:
    """La vuelta de braza alrededor de los dos palos, en el marco del diseño. Todo va en la
    cara de delante del palo de arriba, a la derecha del de abajo, después de los cruces del
    firme con la segunda diagonal: el firme, en el plano c0, y el tramo de la vuelta de braza
    donde se enrolla el chicote, en el plano c_e, más a la derecha.

    En el orden de la cuerda, desde la punta del chicote: el chicote se enrolla en su tramo
    subiendo (cruces 1 a 5: debajo, encima, debajo, encima, debajo); da una vuelta al firme,
    subiendo, por encima (6) y por debajo (7); vuelve hacia abajo como el tramo, por dentro de
    sus vueltas; da la vuelta a los dos palos y sube por la cara de delante como el firme, que
    pasa por encima del chicote en 7 y por debajo en 6. Donde el chicote pasa bajo el firme, el
    firme se aparta un diámetro del palo; donde el chicote se enrolla en el tramo, el tramo."""

    def __init__(self, g: _Geo, c0, c_e, a_ultimo_cruce):
        self.g, self.c0, self.c_e = g, c0, c_e
        self.a_p2 = a_ultimo_cruce + MARGEN + RAMPA_FIRME   # el chicote pasa bajo el firme (7)
        self.a_p1 = self.a_p2 + 22.0                   # y antes, más abajo, por encima (6)
        # La vuelta al firme: empieza justo antes de pasar por encima (fi = π/2) y termina justo
        # después de pasar por debajo (3π/2), hacia el tramo; π/2 cae en a_p1 y 3π/2 en a_p2.
        por_rad = (self.a_p1 - self.a_p2) / math.pi
        self.fi_f = (math.pi / 2 - 0.6, 3 * math.pi / 2 + 0.6)
        self.a_f = tuple(self.a_p1 - (f - math.pi / 2) * por_rad for f in self.fi_f)
        # De ahí va hacia el tramo y dobla hacia abajo, en un cuarto de círculo de radio
        # GIRO_BRAZA; el tramo empieza donde termina el giro.
        self.r_giro = (g.rb + 0.5) * math.pi / 180      # diámetros por grado, sobre el palo
        self.a_F = self.a_f[1] + math.degrees(GIRO_BRAZA / (g.rb + 0.5))
        self.h_F = RADIO_HELICE                        # cuánto se aparta del palo ahí
        # Las vueltas del chicote, del tramo hacia abajo, después de donde el chicote va al
        # firme. Terminan justo después de pasar bajo el tramo (5), hacia el firme.
        self.a_h0 = max(self.a_F + 12.0, self.a_f[0] + 6.0)
        self.fi_h = (-math.pi - 0.4, 7 * math.pi / 2 + 0.25)
        vueltas = (self.fi_h[1] - self.fi_h[0]) / (2 * math.pi)
        self.a_h1 = self.a_h0 + math.degrees(vueltas * PASO_HELICE / (g.rb + RADIO_HELICE))
        self.a_fin_inicio = self.a_p1 + 16.0           # donde termina el paso de la vuelta de braza
        # El tramo del firme que no se relaja: donde el chicote lo rodea.
        self.firme_quieto = (self.a_p2 - RAMPA_FIRME - 4.0, self.a_p1 + 5.0)

    def u_firme(self, a):
        return self.c0 - self.g.rb * math.cos(math.radians(a))

    def u_tramo(self, a):
        return self.c_e - self.g.rb * math.cos(math.radians(a))

    def h_tramo(self, a):
        """Cuánto se aparta del palo el tramo: un diámetro donde lo rodea el chicote."""
        a = _entre(a, -90.0)
        if a >= 280.0 or a < self.a_F - 1e-9:
            return 0.0
        return self.h_F + (RADIO_HELICE - self.h_F) * _rampa(a, self.a_F, self.a_h0)

    def h_firme(self, a):
        """Cuánto se aparta del palo el firme: un diámetro donde el chicote pasa por debajo."""
        a = _entre(a, -90.0)
        return RADIO_HELICE * _rampa(a, self.a_p2 - RAMPA_FIRME, self.a_p2) * (1.0 - _rampa(a, self.a_p2, self.a_p2 + RAMPA_FIRME))

    def _eje_tramo(self, a):
        return self.g.en_mapa(self.u_tramo(a), a, self.h_tramo(a))

    def _eje_firme(self, a):
        return self.g.en_mapa(self.u_firme(a), a, self.h_firme(a))

    def chicote(self, k: _Cuerda) -> None:
        """El chicote, desde su punta: sus vueltas alrededor del tramo, la vuelta al firme y el
        giro hacia abajo, donde empieza el tramo."""
        g = self.g
        from ..libre import catmull_rom
        # Alrededor del tramo, subiendo: empieza por fuera (lejos del firme), a su altura.
        H = _helice(self._eje_tramo, self.a_h1, self.a_h0, -1.0, *self.fi_h, radio=RADIO_HELICE)
        atras = _unit(H[0] - H[2])   # la punta asoma un poco, en la dirección en que venía
        k.poner(np.array([H[0] + 0.5 * atras, H[0]]), ARRIBA, quieta=True)
        k.poner(H, ARRIBA, quieta=True)
        for q in range(1, 6):
            k.pasa(("H", q), q % 2 == 0)
        # Va hacia el firme y le da media vuelta subiendo: por encima (6), por fuera y por
        # debajo (7), y sale hacia el tramo.
        F = _helice(self._eje_firme, self.a_f[0], self.a_f[1], +1.0, *self.fi_f, radio=RADIO_HELICE)
        k.poner(g.hermite_mapa(H[-1], F[0], _dir(H), _dir(F, False)), ARRIBA, quieta=True)
        k.poner(F, ARRIBA, quieta=True)
        k.pasa(("H", 6), True)
        k.pasa(("H", 7), False)
        # Vuelve hacia el tramo y dobla hacia abajo: ahí empieza el tramo.
        T0 = self._eje_tramo(self.a_F)
        T1 = self._eje_tramo(self.a_F + 2.0)
        k.poner(g.hermite_mapa(F[-1], T0, _dir(F), _unit(T1 - T0)), ARRIBA, quieta=True)

    def tramo(self, k: _Cuerda, a_baja) -> np.ndarray:
        """El tramo, desde donde vuelve el chicote hasta donde baja entre los palos, por dentro
        de las vueltas del chicote."""
        if a_baja < self.a_h1 + 3.0:
            raise ValueError("las vueltas del chicote no caben en la cara del palo de arriba")
        A = _angulos(self.a_F, a_baja)
        P = np.array([self._eje_tramo(a) for a in A])
        # Después de las vueltas del chicote, el tramo ya baja entre los palos: ahí es parte de
        # la esquina, y los ahorcados lo cruzan en la cintura.
        j = int(np.searchsorted(A, self.a_h1 + 4.0))
        k.poner(P[:j + 1], ARRIBA, quieta=True)
        for q in range(5, 0, -1):
            k.pasa(("H", q), q % 2 == 1)
        return P, P[j:]

    def firme(self, k: _Cuerda) -> None:
        """El firme pasa por encima del chicote en 7 y por debajo en 6."""
        k.pasa(("H", 7), True)
        k.pasa(("H", 6), False)


def _ultimo_tramo(D, P0, P1):
    """Los puntos de una curva densa entre los más cercanos a P0 y a P1, ambos incluidos."""
    i = int(np.linalg.norm(D - P0, axis=1).argmin())
    j = int(np.linalg.norm(D - P1, axis=1).argmin())
    return slice(i, j + 1)


def _helice(eje, a0, a1, hacia_x, fi0, fi1, radio=1.0):
    """Una cuerda que se enrolla en otra (su eje: eje(a), con a el ángulo sobre el palo de
    arriba), de a0 a a1, a `radio` de su eje. El ángulo fi alrededor del eje va de fi0 a fi1:
    con fi = 0 queda a su lado, hacia x crecientes si `hacia_x` es +1 (o decrecientes si es
    −1), y con fi = π/2 por encima, lejos del palo."""
    A = np.linspace(a0, a1, 240)
    C = np.array([eje(a) for a in A])
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))])
    paso = 0.08
    largo_eje = s[-1]
    vueltas = abs(fi1 - fi0) / (2 * math.pi)
    k = max(30, int(math.hypot(largo_eje, 2 * math.pi * radio * vueltas) / paso))
    u = np.linspace(0.0, largo_eje, k)
    Cu = np.column_stack([np.interp(u, s, C[:, q]) for q in range(3)])
    Au = np.interp(u, s, A)
    Tg = np.gradient(Cu, axis=0)
    Tg /= np.linalg.norm(Tg, axis=1)[:, None]
    Nr = np.column_stack([np.zeros(len(Au)), np.cos(np.radians(Au)), np.sin(np.radians(Au))])
    L = np.array([hacia_x, 0.0, 0.0]) - (Tg @ np.array([hacia_x, 0.0, 0.0]))[:, None] * Tg
    L -= (L * Nr).sum(1)[:, None] * Nr
    L /= np.linalg.norm(L, axis=1)[:, None]
    N = np.cross(Tg, L)
    N *= np.sign((N * Nr).sum(1))[:, None]   # hacia afuera del palo
    N /= np.linalg.norm(N, axis=1)[:, None]
    fi = fi0 + (fi1 - fi0) * u / largo_eje
    return Cu + radio * (np.cos(fi)[:, None] * L + np.sin(fi)[:, None] * N)


def _segunda_y_resto(p: AmarreDiagonal, g: _Geo, cruz, c, d, k: _Cuerda, a_cambio, por_fuera):
    """La segunda diagonal, y después, en el marco del cuadrado, los ahorcados y el cierre."""
    n, m = p.vueltas, p.ahorcados
    dc = PASO_DIAGONAL * math.sqrt(2)
    # Los obstáculos de cada plano de la segunda diagonal: donde lo atraviesa la primera, sobre
    # el palo de arriba y bajo el de abajo.
    medio_z = (g.zb + g.zt) / 2
    obst = {l: ([], []) for l in range(n)}
    for P, zona in k.piezas:
        if zona not in (ARRIBA, ABAJO):
            continue
        for l, dl in enumerate(d):
            f = P[:, 0] - P[:, 1] - dl
            for q in np.nonzero(f[:-1] * f[1:] < 0)[0]:
                w = f[q] / (f[q] - f[q + 1])
                Q = P[q] + w * (P[q + 1] - P[q])
                obst[l][0 if Q[2] > medio_z else 1].append(g.al_plano(-1, Q)[0])
    for l in range(n):
        if len(obst[l][0]) != n + 1 or len(obst[l][1]) != n + 1:
            raise ValueError(f"la vuelta {l + 1} de la segunda diagonal no cruza una vez cada "
                             "vuelta de la primera sobre cada palo")
    T2 = [g.corte("arriba", -1, dl, obstaculos=obst[l][0]) for l, dl in enumerate(d)]
    B2 = [g.corte("abajo", -1, dl, obstaculos=obst[l][1]) for l, dl in enumerate(d)]
    sobre = None
    for l in range(n):
        # Baja entre los palos delante a la izquierda (s < 0): la primera, desde la cara de
        # delante del palo de arriba, donde termina la primera diagonal.
        if l == 0:
            U = k.fin
            _, ib = _puente(_Corte(np.array([np.nan]), g.al_plano(-1, U), np.atleast_2d(U)), B2[0], -1)
            t0 = _dir(k.piezas[-1][0])
        else:
            _, ib = _puente(T2[l - 1], B2[l], -1)
            U, t0 = sobre[-1], _dir(sobre)
        it2, ib2 = _puente(T2[l], B2[l], +1)
        bajo = _borde(B2[l], ib, ib2, +1)
        k.esquina(f"d2-{l}-baja", -1, U, bajo[0], t0, _dir(bajo, False))
        # Por debajo del palo de abajo, de izquierda a derecha, por fuera de la primera diagonal.
        k.poner(bajo, ABAJO)
        for i in range(len(c) - 1, -1, -1):
            k.pasa(("B", i, l), True)
        # Sube entre los palos atrás a la derecha (s > 0) y pasa por encima del palo de arriba,
        # de atrás hacia delante, por fuera de la primera diagonal.
        sig_b = B2[l + 1] if l + 1 < n else g.corte("abajo", -1, d[l] - dc)
        it3, _ = _puente(T2[l], sig_b, -1)
        sobre = _borde(T2[l], it2, it3, +1)
        k.esquina(f"d2-{l}-sube", +1, bajo[-1], sobre[0], _dir(bajo), _dir(sobre, False))
        k.poner(sobre, ARRIBA)
        for i in range(len(c)):
            k.pasa(("T", i, l), True)
        k.marcar(f"segunda-{l + 1}")

    # --- En el marco del cuadrado: los ahorcados y el cierre ---
    pal = _Palos(cruz)
    rb, zt = cruz.rb, cruz.zt
    t = Trazo()
    marcas_de: dict[int, list[str]] = {}
    for nombre, q in k.marcas.items():
        marcas_de.setdefault(q, []).append(nombre)
    for q, (P, zona) in enumerate(k.piezas):
        t.puntos(P * ESPEJO, zona + (QUIETA if q in k.quietas else 0))
        for nombre in marcas_de.get(q, []):
            t.marcar(nombre)
    esquinas = []
    for nombre, sube, qs in k.esquinas:
        P = np.vstack([k.piezas[q][0] for q in qs]) * ESPEJO
        esquinas.append(_Esquina(nombre, _cuadrante(P), sube, P))
    alto = alturas_de_ahorcados(m, por_fuera, cruz)
    arriba_pts = np.vstack([P * ESPEJO for P, zona in k.piezas if zona == ARRIBA])
    arriba_pts = arriba_pts[arriba_pts[:, 2] > zt]
    encima = {"der": float(arriba_pts[:, 0].max()), "izq": float(-arriba_pts[:, 0].min())}
    fin_dir = _dir(k.piezas[-1][0] * ESPEJO)

    def salida(planos, pasa_ar, punto):
        # La segunda diagonal termina en la cara de delante del palo de arriba, a la derecha, y
        # de ahí va a pasar bajo él, por fuera de las esquinas, donde empieza el primer ahorcado.
        if por_fuera:
            # En el error, el primer ahorcado pasa por encima del palo de arriba: la cuerda baja
            # un poco más por la cara de delante y vuelve a subir, en medio círculo, hasta donde
            # pasa por encima del palo, fuera de las vueltas.
            x0, P0 = t.fin[0], t.fin
            R = (planos["der"] - x0) / 2
            r = math.hypot(P0[1], P0[2] - zt)
            a0 = math.atan2(P0[2] - zt, P0[1])
            th = np.linspace(0.0, math.pi, 40)[1:]
            a = a0 + np.sin(th) * R / r   # baja por la cara de delante (el ángulo crece)
            # Termina un poco apartada del palo, para que de ahí salga tangente a él.
            ra = r + 0.1 * th / math.pi
            U = np.column_stack([x0 + R * (1 - np.cos(th)), ra * np.cos(a), zt + ra * np.sin(a)])
            t.puntos(U, ARRIBA)
            return
        zj = alto(1, 0.0)
        E0 = np.array([planos["der"], -pasa_ar(zj, 1), zj])
        llega_e0 = np.array([0.0, 1.0, 0.0])
        t.puntos(_hermite(t.fin, E0, fin_dir, llega_e0), ARRIBA)

    # En el error, los ahorcados empiezan a subir el palo de arriba más cerca de su cara que en
    # el cuadrado: con 1,0, uno cruza una esquina de la vuelta de braza justo donde llega al
    # palo y, al relajar, deja de cruzarla.
    ahorcados_y_cierre(t, pal, m, por_fuera, alto, [(e, e.P) for e in esquinas], encima, salida,
                       fuera=FUERA_ERROR)

    X, Z, hitos = t.muestrear(RADIO_ESQUINA)
    quietos, Z = Z >= QUIETA, Z % QUIETA
    espejo = np.array([-1.0 if p.cierre.lado == "izquierda" else 1.0, 1.0, 1.0])
    X = X * espejo
    restos = {}
    for nombre, i in hitos.items():
        if nombre != "cierre":
            sale = SALIDAS[nombre] if nombre in SALIDAS else SALIDAS[nombre.split("-")[0]]
            restos[nombre] = _resto_largo(X[i], _unit(X[i] - X[max(i - 3, 0)]),
                                          _unit(np.array([*sale, 0.0]) * espejo))
    alias = {"vueltas": f"vuelta-{n}", "segundas": f"segunda-{n}", "ahorcados": f"ahorcado-{m}"}
    return Cuerda(X, Z, hitos, restos, _secuencias(p, k.eventos, esquinas, alto, por_fuera), alias,
                  quietos)


def _resto_largo(P, llega, afuera) -> np.ndarray:
    """Como amarre._resto, lo que sigue de la cuerda después de un hito, pero girando más
    despacio hacia fuera: aquí la cuerda suele llegar bajando por la cara de un palo."""
    q1 = P + 1.6 * llega
    q2 = q1 + 1.6 * _unit(llega + afuera)
    return np.vstack([q1, _resto(q2, _unit(q2 - q1), afuera)])


def _secuencias(p: AmarreDiagonal, eventos, esquinas: list[_Esquina], alto,
                bajan: bool) -> dict[str, tuple[str, ...]]:
    """La secuencia de cruces del método hasta cada hito.

    La vuelta de braza da los 7 cruces de su chicote. Cada vuelta de la segunda diagonal pasa
    por encima de cada vuelta de la primera sobre el palo de arriba y bajo el de abajo. Cada
    ahorcado pasa por encima de cada esquina, recorriéndolas en el sentido en que gira desde
    que pasa bajo el palo de arriba, a la derecha; sobre cada esquina pasan de abajo arriba (el
    primero es el más bajo o, si `bajan`, el más alto). El ballestrinque de cierre da los dos
    últimos. Las etiquetas se numeran en el orden en que aparecen en la cuerda entera del amarre
    bien hecho, así que cada una nombra el mismo cruce en todos los pasos y en el error."""
    m = p.ahorcados

    def con_esquinas(bajan):
        ev = []
        for e in eventos:
            if e[0] == "esquina":
                _, nombre, sube = e
                orden = range(1, m + 1) if (sube > 0) != bajan else range(m, 0, -1)
                ev += [("pasa", ("K", nombre, j), False) for j in orden]
            else:
                ev.append(e)
        return ev
    ev = con_esquinas(bajan)
    # Dónde cruza cada esquina al primer ahorcado: da el orden en que los ahorcados las recorren.
    giro = {}
    for e in esquinas:
        dz = np.abs(e.P[:, 2] - np.array([alto(1, math.atan2(y, x)) for x, y in e.P[:, :2]]))
        x, y = e.P[int(dz.argmin()), :2]
        giro[e.nombre] = math.atan2(y, x) % (2 * math.pi)
    por_giro = sorted(giro, key=giro.get)
    for j in range(1, m + 1):
        ev += [("pasa", ("K", nombre, j), True) for nombre in por_giro]
        ev.append(("hito", f"ahorcado-{j}"))
    ev += [("pasa", ("C", 1), False), ("pasa", ("C", 1), True), ("hito", "cierre-1"),
           ("pasa", ("C", 2), True), ("pasa", ("C", 2), False), ("hito", "cierre")]
    # Se numeran por el orden del amarre bien hecho: así el error lleva las mismas etiquetas.
    numero: dict = {}
    for e in con_esquinas(False) + ev:
        if e[0] == "pasa":
            numero.setdefault(e[1], len(numero) + 1)
    out = {}
    hechos: list = []
    for e in ev:
        if e[0] == "hito":
            cuenta: dict = {}
            for x in hechos:
                cuenta[x[1]] = cuenta.get(x[1], 0) + 1
            out[e[1]] = tuple(f"{numero[x[1]]}{'O' if x[2] else 'U'}" for x in hechos
                              if cuenta[x[1]] == 2)
        else:
            hechos.append(e)
    for alias, k in (("vueltas", f"vuelta-{p.vueltas}"), ("segundas", f"segunda-{p.vueltas}"),
                     ("ahorcados", f"ahorcado-{m}")):
        out[alias] = out[k]
    return out
