"""Herramientas para trazar la cuerda de una plantilla a mano alzada, pieza por pieza.

Una cuerda se arma con rectas, puntos sueltos (por ejemplo, sobre la superficie de un palo)
y vueltas alrededor de un palo en su plano de corte. Cada pieza lleva su zona, que dice en
qué mapa se buscan sus cruces (nudos/plantillas/pasos.py). Las esquinas entre dos rectas se
redondean con un arco antes de muestrear, para que la cuerda no se doble más de la cuenta.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

PASO = 0.3   # cada cuánto se toma un punto de una recta o un arco, en diámetros

# Zonas: dónde va cada tramo de la cuerda.
MESA, ABAJO, ARRIBA, CINTURA = 0, 1, 2, 3
NOMBRES_ZONA = {MESA: "mesa", ABAJO: "palo de abajo", ARRIBA: "palo de arriba", CINTURA: "cintura"}


@dataclass
class TrazoDePaso:
    """Un paso de una plantilla listo para construir (nudos/plantillas/pasos.py): los puntos de
    control en la mesa, su zona, el índice del punto donde termina el paso y del punto donde
    termina el anterior (None si es el primero), y en la cabeza de turco cuánto está girado el
    nudo, en grados."""
    puntos: np.ndarray
    zonas: np.ndarray
    fin: int
    inicio: int | None
    giro: float | None = None


@dataclass
class _Pieza:
    zona: int
    puntos: np.ndarray            # (N, 3); en una recta, solo sus dos extremos
    recta: bool = False


@dataclass
class Trazo:
    piezas: list[_Pieza] = field(default_factory=list)
    marcas: dict[str, int] = field(default_factory=dict)   # nombre → pieza en cuyo final está

    @property
    def fin(self) -> np.ndarray:
        return self.piezas[-1].puntos[-1].copy()

    def puntos(self, P, zona: int) -> None:
        P = np.atleast_2d(np.asarray(P, float))
        if self.piezas and np.linalg.norm(P[0] - self.fin) < 1e-9:
            P = P[1:]
        if len(P):
            self.piezas.append(_Pieza(zona, P))

    def ir(self, Q, zona: int) -> None:
        """Una recta desde el final hasta Q."""
        Q = np.asarray(Q, float)
        if np.linalg.norm(Q - self.fin) > 1e-9:
            self.piezas.append(_Pieza(zona, np.array([self.fin, Q]), recta=True))

    def marcar(self, nombre: str) -> None:
        self.marcas[nombre] = len(self.piezas) - 1

    def rodear(self, centro, plano, Q, sentido: int, zona_arco: int, zona_rectas: int,
               radio: float) -> None:
        """Desde el final hasta Q dando la vuelta a un círculo (el corte de un palo) en un
        plano. `plano(u, v)` da el punto 3D de las coordenadas del plano y `plano.de(P)` las
        coordenadas de un punto. `sentido` +1 es antihorario en (u, v). Llega y sale por
        rectas tangentes; si la recta hasta Q ya pasa por fuera del círculo, va recta."""
        c = np.asarray(centro, float)
        P2, Q2 = plano.de(self.fin), plano.de(Q)
        d = Q2 - P2
        t = float(np.clip(np.dot(c - P2, d) / np.dot(d, d), 0, 1))
        if np.linalg.norm(P2 + t * d - c) >= radio:
            self.ir(Q, zona_rectas)
            return
        mejor = None
        for a0 in _tangentes(c, radio, P2):
            if np.dot(_en(c, radio, a0) - P2, _dir(a0, sentido)) <= 0:
                continue
            for a1 in _tangentes(c, radio, Q2):
                if np.dot(Q2 - _en(c, radio, a1), _dir(a1, sentido)) <= 0:
                    continue
                giro = (a1 - a0) * sentido % (2 * math.pi)
                if mejor is None or giro < mejor[0]:
                    mejor = (giro, a0)
        if mejor is None:
            raise ValueError("no hay tangente para rodear el palo")
        giro, a0 = mejor
        n = max(2, int(giro * radio / PASO) + 1)
        angs = a0 + sentido * np.linspace(0, giro, n)
        arco = np.array([plano(*_en(c, radio, a)) for a in angs])
        self.ir(arco[0], zona_rectas)
        self.puntos(arco, zona_arco)
        self.ir(Q, zona_rectas)

    def muestrear(self, radio: float = 1.3) -> tuple[np.ndarray, np.ndarray, dict[str, int]]:
        """Los puntos de la cuerda, su zona y el índice del punto de cada marca. Antes redondea
        cada esquina entre dos rectas con un arco de `radio` (o menos, si las rectas son cortas)."""
        piezas = [_Pieza(p.zona, p.puntos.copy(), p.recta) for p in self.piezas]
        arcos: dict[int, _Pieza] = {}
        largo = [float(np.linalg.norm(p.puntos[1] - p.puntos[0])) if p.recta else 0.0 for p in piezas]
        for k in range(len(piezas) - 1):
            a, b = piezas[k], piezas[k + 1]
            if not (a.recta and b.recta):
                continue
            v = self.piezas[k].puntos[1]
            u1 = _unit(v - self.piezas[k].puntos[0])
            u2 = _unit(self.piezas[k + 1].puntos[1] - v)
            ang = math.acos(float(np.clip(np.dot(u1, u2), -1, 1)))
            if ang < math.radians(2):
                continue
            t = min(radio * math.tan(ang / 2), 0.48 * largo[k], 0.48 * largo[k + 1])
            r = t / math.tan(ang / 2)
            T1, T2 = v - u1 * t, v + u2 * t
            a.puntos[1], b.puntos[0] = T1, T2
            # Arco de T1 a T2, tangente a las dos rectas.
            normal = _unit(u2 - np.dot(u2, u1) * u1)   # perpendicular a la primera recta, hacia dentro
            C = T1 + normal * r
            e1, e2 = _unit(T1 - C), _unit(T2 - C)
            om = math.acos(float(np.clip(np.dot(e1, e2), -1, 1)))
            n = max(2, int(om * r / PASO) + 1)
            arc = []
            for s in np.linspace(0, 1, n)[1:-1]:
                w = (math.sin((1 - s) * om) * e1 + math.sin(s * om) * e2) / math.sin(om)
                arc.append(C + r * w)
            if arc:
                arcos[k] = _Pieza(a.zona, np.array(arc))   # la curva va en la zona de la primera recta
        P, Z, fin_de = [], [], []
        for k, p in enumerate(piezas):
            pts = _densa(p.puntos) if p.recta else p.puntos
            for q in pts:
                if P and np.linalg.norm(q - P[-1]) < 1e-9:
                    continue
                P.append(q)
                Z.append(p.zona)
            fin_de.append(len(P) - 1)
            if k in arcos:
                for q in arcos[k].puntos:
                    P.append(q)
                    Z.append(arcos[k].zona)
        marcas = {nombre: fin_de[k] for nombre, k in self.marcas.items()}
        return np.array(P), np.array(Z), marcas


class Plano:
    """El plano de corte de un palo: `eje` es la coordenada constante (0 para x, 1 para y)."""

    def __init__(self, eje: int, valor: float):
        self.eje, self.valor = eje, valor
        self.u = 1 - eje   # la otra coordenada horizontal

    def __call__(self, u, v) -> np.ndarray:
        P = np.zeros(3)
        P[self.eje], P[self.u], P[2] = self.valor, u, v
        return P

    def de(self, P) -> np.ndarray:
        return np.array([P[self.u], P[2]])


def _densa(P) -> np.ndarray:
    a, b = P[0], P[-1]
    n = max(2, int(np.linalg.norm(b - a) / PASO) + 1)
    return a + np.linspace(0, 1, n)[:, None] * (b - a)


def _unit(v) -> np.ndarray:
    return v / max(float(np.linalg.norm(v)), 1e-12)


def _en(c, r, a) -> np.ndarray:
    return c + r * np.array([math.cos(a), math.sin(a)])


def _dir(a, sentido) -> np.ndarray:
    return sentido * np.array([-math.sin(a), math.cos(a)])


def _tangentes(c, r, P) -> tuple[float, float]:
    d = P - c
    a = math.atan2(d[1], d[0])
    b = math.acos(min(1.0, r / float(np.linalg.norm(d))))
    return a + b, a - b
