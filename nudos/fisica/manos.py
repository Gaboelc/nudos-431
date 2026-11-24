"""Las manos del motor (T15d): qué nodos se sostienen, de cuáles se tira y con cuánto.

Las manos son condiciones de borde. Una mano que sostiene deja sus nodos fijos (`fijos`); una
que tira empuja un nodo con una fuerza (`fuerzas`, en N); y la tensión de atado (`tension`,
en N por tramo) acorta el largo de reposo de cada tramo, como si la cuerda se hubiera tirado al
darla y el roce guardara esa tensión (T14a, `Varilla.desde_forma`).

- Al asentar un paso (`sostener`), la mano del firme sostiene sus primeros nodos y la del
  chicote, sus últimos nodos, si hace falta: la cuerda queda como la dejaron las manos, y lo demás se apoya.
- Al apretar el terminado (`para_apretar`), se asienta como a mano:
  - Si la cuerda tiene un lazo que sale del nudo y vuelve a él (la gaza del as de guía), el
    lazo se sostiene abierto y se tira fuerte del firme, por su punta y hacia donde viene, y
    más suave del chicote (CHICOTE): así se asienta un as de guía.
  - Si no, una mano sostiene el firme (su punta y donde entra al nudo) y se tira fuerte del
    chicote, por su punta y hacia donde sigue.
  Medido con los pilotos (T15d): tirar de la gaza desde un punto la estiraba en una V larga y
  la doblaba demasiado ahí; tirar solo del chicote del as de guía lo alargaba hasta cruzar la
  gaza, y el nudo dejaba de verse como en la ficha antes de apretarse; con el firme sostenido
  solo en su punta, el nudo viajaba hacia el chicote y salía del encuadre; y tirar del firme
  del ballestrinque, que viene por la mesa, hacía girar sus vueltas sobre el poste.

Las posiciones van en diámetros; la cuerda entera es una fila de nodos, con cada cuerda
seguida de la siguiente (`cortes`, como en `Sistema`).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

SOSTENIDOS = 3          # los nodos que sostiene cada mano
DISTANCIA_NUDO = 6.0    # diámetros, sobre la mesa, desde algún cruce: lo que está en el nudo
LAZO_MIN = 3.0          # diámetros: un lazo más corto que esto no se sostiene
CHICOTE = 1 / 3         # del chicote se tira con esta parte de la fuerza del firme


@dataclass
class Manos:
    fijos: np.ndarray            # los nodos sostenidos
    fuerzas: np.ndarray          # (N, 3) en N
    tension: np.ndarray | None   # (N,) la tensión de atado del tramo que empieza en cada nodo


def cortes_de(cuerdas) -> np.ndarray:
    """[0, n₀, n₀ + n₁, …] desde los nodos de cada cuerda."""
    return np.cumsum([0, *cuerdas])


def sostener(cortes, N: int, chicotes: bool = True, extra=(), nodos: int = SOSTENIDOS) -> Manos:
    """El firme de cada cuerda sostenido (sus primeros nodos) y, con `chicotes`, también el
    chicote (sus últimos). `nodos` es cuántos sostiene cada mano: con uno, la punta queda
    sujeta pero puede girar, y la cuerda sale de la mano hacia donde la tira la tensión (en un
    amarre, sostener tres nodos fijaba una dirección, y la tensión de atado la doblaba ahí con
    radio 0,29). `extra` son otros nodos sostenidos."""
    fijos = []
    for a, b in zip(cortes[:-1], cortes[1:]):
        fijos += list(range(a, min(a + nodos, b)))
        if chicotes:
            fijos += list(range(max(b - nodos, a), b))
    fijos = np.unique(np.concatenate([np.asarray(fijos, int), np.asarray(extra, int)]))
    return Manos(fijos, np.zeros((N, 3)), None)


def para_apretar(X, cortes, cruces_xy, fuerza: float) -> Manos:
    """Las manos que aprietan el nudo terminado X (N, 3), tirando con `fuerza` (ver arriba). Está en el nudo lo que queda a menos de
    DISTANCIA_NUDO, sobre la mesa, de algún cruce (`cruces_xy`)."""
    X = np.asarray(X, float)
    N = len(X)
    xy = np.asarray(list(cruces_xy), float).reshape(-1, 2)
    if len(xy):
        en_nudo = np.linalg.norm(X[:, None, :2] - xy[None], axis=2).min(axis=1) <= DISTANCIA_NUDO
    else:
        en_nudo = np.ones(N, bool)
    fuerzas = np.zeros((N, 3))
    fijos = []
    for a, b in zip(cortes[:-1], cortes[1:]):
        fuera = ~en_nudo[a:b]
        lazos = [(i, j) for i, j in _tramos(fuera) if i > 0 and j < b - a - 1
                 and _largo(X[a + i:a + j + 1]) >= LAZO_MIN]
        chicote = _hacia(X[b - 1] - X[max(b - 6, a)])
        if lazos:
            for i, j in lazos:
                fijos += list(range(a + i, a + j + 1))
            fuerzas[a] += fuerza * _hacia(X[a] - X[min(a + 5, b - 1)])
            fuerzas[b - 1] += fuerza * CHICOTE * chicote
        else:
            fijos += list(range(a, min(a + SOSTENIDOS, b)))
            if fuera[0] and not fuera.all():
                k = a + int(np.argmin(fuera))    # el primer nodo del firme que está en el nudo
                fijos += list(range(max(a, k - SOSTENIDOS), k))
            fuerzas[b - 1] += fuerza * chicote
    return Manos(np.unique(np.asarray(fijos, int)), fuerzas, None)


def _tramos(m) -> list[tuple[int, int]]:
    """El primer y el último índice de cada tramo seguido de True en m."""
    out, i = [], 0
    while i < len(m):
        if not m[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(m) and m[j + 1]:
            j += 1
        out.append((i, j))
        i = j + 1
    return out


def _largo(X) -> float:
    return float(np.sum(np.linalg.norm(np.diff(X, axis=0), axis=1)))


def _hacia(v) -> np.ndarray:
    """La dirección de v sobre la mesa (sin su parte vertical), unitaria."""
    v = np.array([v[0], v[1], 0.0])
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else np.array([1.0, 0.0, 0.0])
