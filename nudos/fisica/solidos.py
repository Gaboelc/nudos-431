"""Los anfitriones como mallas para el contacto del motor (T15f).

Cada anfitrión de `nudos/anfitrion.py` (y los dedos del puño de mono) pasa a una o varias mallas
de triángulos (`Solido`), que van `adentro` diámetros por dentro de la madera: la barrera de la
IPC deja el eje de la cuerda a dmin + dhat/2 de la malla, que es donde la cuerda toca la madera
(ver `asentar.solidos`, que da `adentro`). Así una superficie de la malla es la de la madera
desplazada hacia dentro, y las formas redondeadas pierden radio:

- **Los cilindros** (el poste, la cruz, los palos, el tubo, el cabo, la estaca y el destorcedor)
  son prismas de 64 lados con un anillo en cada punta (`contacto.cilindro`), abiertos en las
  puntas: la cuerda no pasa por ellas, salvo por delante del corte del cabo, donde no hay nada.
- **El tablón** es un prisma con el corte del tablón desplazado: con cantos de radio CANTO
  menor que `adentro`, el corte de la malla es un rectángulo de esquinas vivas, y la cuerda que
  rodea un canto lo rodea a un diámetro de esa esquina, casi como al canto de la madera.
- **La cornamusa** es una barra con las puntas redondas (un sólido de revolución alrededor de
  x) y el pie, un estadio parado de la mesa a la barra.
- **El barril** es el sólido de revolución de su núcleo desplazado (`Barril._contorno`), sin las
  ranuras de la banda, que la cuerda no toca.
- **Los dedos** del puño de mono son dos cilindros parados con la punta redonda.

El roce es el de la madera, salvo el del destorcedor, que es de metal (`Material.mu_metal`).
"""
from __future__ import annotations

import math

import numpy as np

from .contacto import LADOS, Solido, cilindro
from .materiales import CUERDA_8MM

ARCO = 0.25   # diámetros: el largo de cada tramo de un perfil curvo (un canto, una punta, el barril)


class SinMalla(ValueError):
    """El anfitrión no tiene malla para el motor."""


def _base(eje):
    """Dos vectores unitarios perpendiculares a `eje` y entre sí, y el eje unitario."""
    w = np.asarray(eje, float)
    w = w / np.linalg.norm(w)
    a = np.cross(w, [0.0, 0.0, 1.0] if abs(w[2]) < 0.9 else [1.0, 0.0, 0.0])
    a /= np.linalg.norm(a)
    return a, np.cross(w, a), w


def extrusion(contorno, origen, eje_u, eje_v, eje_w, w0: float, w1: float,
              mu: float | None = None) -> Solido:
    """El prisma de un contorno cerrado (n, 2) en el plano (u, v), de w0 a w1 a lo largo de
    `eje_w`, con un anillo en cada punta y abierto en ellas. Los ejes van en el mundo."""
    C = np.asarray(contorno, float)
    n = len(C)
    o, u, v, w = (np.asarray(x, float) for x in (origen, eje_u, eje_v, eje_w))
    V = np.vstack([o + C[:, :1] * u + C[:, 1:] * v + t * w for t in (w0, w1)])
    F = []
    for j in range(n):
        p, q = j, (j + 1) % n
        F += [(p, q, q + n), (p, q + n, p + n)]
    return Solido(V, np.array(F, dtype=np.int32), mu)


def revolucion(perfil, origen, eje, lados: int = LADOS, mu: float | None = None) -> Solido:
    """El sólido de revolución de un perfil (n, 2) de [distancia al eje, posición a lo largo del
    eje], alrededor de `eje` por `origen`. Un punto del perfil sobre el eje es un solo vértice."""
    P = np.asarray(perfil, float)
    a, b, w = _base(eje)
    o = np.asarray(origen, float)
    t = np.linspace(0, 2 * math.pi, lados, endpoint=False)
    anillo = np.cos(t)[:, None] * a + np.sin(t)[:, None] * b
    V, filas = [], []
    for rho, s in P:
        if rho < 1e-9:
            filas.append([len(V)] * lados)
            V.append(o + s * w)
        else:
            filas.append(list(range(len(V), len(V) + lados)))
            V.extend(o + s * w + rho * anillo)
    F = []
    for f0, f1 in zip(filas[:-1], filas[1:]):
        for j in range(lados):
            k = (j + 1) % lados
            p, q, r, s = f0[j], f0[k], f1[k], f1[j]
            for tri in ((p, q, r), (p, r, s)):
                if len(set(tri)) == 3:
                    F.append(tri)
    return Solido(np.array(V), np.array(F, dtype=np.int32), mu)


def arco(centro, radio: float, a0: float, a1: float) -> np.ndarray:
    """Puntos de un arco de a0 a a1 (radianes, sin el último), cada ARCO más o menos."""
    k = max(2, int(math.ceil(abs(a1 - a0) * radio / ARCO)))
    f = np.linspace(a0, a1, k + 1)[:-1]
    return np.asarray(centro, float) + radio * np.column_stack([np.cos(f), np.sin(f)])


def rectangulo(au: float, av: float, e: float) -> np.ndarray:
    """El contorno a `e` de un rectángulo de medios lados au y av: con e > 0, de esquinas
    redondeadas de radio e; si no, el rectángulo achicado, de esquinas vivas."""
    if e <= 1e-9:
        u, v = au + e, av + e
        return np.array([[u, v], [-u, v], [-u, -v], [u, -v]])
    esquinas = [((au, av), 0.0), ((-au, av), 0.5 * math.pi), ((-au, -av), math.pi),
                ((au, -av), 1.5 * math.pi)]
    return np.vstack([arco(c, e, a, a + 0.5 * math.pi) for c, a in esquinas])


def estadio(medio: float, radio: float) -> np.ndarray:
    """El contorno de un estadio: dos medios círculos de `radio` con centros en ±medio sobre u."""
    return np.vstack([arco((medio, 0.0), radio, -0.5 * math.pi, 0.5 * math.pi),
                      arco((-medio, 0.0), radio, 0.5 * math.pi, 1.5 * math.pi)])


def capsula(medio: float, radio: float) -> np.ndarray:
    """El perfil de revolución de una barra de `radio` con las puntas redondas, de −medio −
    radio a medio + radio a lo largo de su eje (los centros de las puntas en ±medio)."""
    ida = arco((-medio, 0.0), radio, math.pi, 0.5 * math.pi)            # (s, ρ) de la punta de atrás
    vuelta = arco((medio, 0.0), radio, 0.5 * math.pi, 0.0)
    P = np.vstack([ida, vuelta, [[medio + radio, 0.0]]])
    return np.column_stack([np.abs(P[:, 1]), P[:, 0]])                 # [ρ, s]


def mallas(solido, adentro: float, mu_metal: float = CUERDA_8MM.mu_metal) -> list[Solido]:
    """Las mallas del anfitrión `solido`, `adentro` diámetros por dentro de su superficie."""
    from ..anfitrion import Barril, Cabo, Cornamusa, Cruz, Destorcedor, Palos, Parado, Poste, Tablon, Tubo
    from ..plantillas.puno import Dedos
    from ..anfitrion import CANTO
    from ..spec import CANTO_BARRIL
    r = adentro
    t = type(solido)
    if t is Poste:
        largo = solido.hasta - solido.desde
        centro = ((solido.desde + solido.hasta) / 2, 0.0, solido.zc)
        return [cilindro(centro, (1, 0, 0), solido.radio - r, largo)]
    if t is Cruz:
        return [cilindro((0, 0, solido.zb), (0, 1, 0), solido.radio - r, solido.largo),
                cilindro((0, 0, solido.zt), (1, 0, 0), solido.radio - r, solido.largo)]
    if t is Palos:
        return [cilindro((0, y, solido.zc), (1, 0, 0), solido.radio - r, solido.largo)
                for y in solido.ys]
    if t is Tubo:
        return [cilindro((0, 0, solido.zc), (1, 0, 0), solido.radio - r, solido.largo)]
    if t is Cabo:
        return [cilindro((-solido.largo / 2, 0, solido.zc), (1, 0, 0), solido.radio - r, solido.largo)]
    if isinstance(solido, Parado):
        mu = mu_metal if isinstance(solido, Destorcedor) else None
        return [cilindro((0, 0, solido.alto / 2), (0, 0, 1), solido.radio - r, solido.alto, mu=mu)]
    if t is Tablon:
        corte = rectangulo(solido.ay, solido.az, CANTO - r)
        return [extrusion(corte, (0, 0, solido.zc), (0, 1, 0), (0, 0, 1), (1, 0, 0),
                          -solido.largo + r, -r)]
    if t is Cornamusa:
        rc = solido.radio - r
        barra = revolucion(capsula(solido.punta, rc), (0, 0, solido.zc), (1, 0, 0))
        pie = extrusion(estadio(solido.pie, rc), (0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
                        0.0, solido.zc)
        return [barra, pie]
    if t is Barril:
        _, rho, z, _ = solido._contorno(CANTO_BARRIL - r, paso=ARCO)
        return [revolucion(np.column_stack([rho, z]), (0, 0, 0), (0, 0, 1))]
    if t is Dedos:
        rc = solido.radio - r
        tope = solido.alto - solido.radio
        f = np.linspace(0.0, 0.5 * math.pi, max(2, int(math.ceil(0.5 * math.pi * rc / ARCO))) + 1)
        perfil = np.vstack([[[rc, 0.0]], np.column_stack([rc * np.cos(f), tope + rc * np.sin(f)])])
        perfil[-1, 0] = 0.0
        return [revolucion(perfil, (lado * solido.x, 0, 0), (0, 0, 1)) for lado in (-1, 1)]
    raise SinMalla(f"el motor no tiene malla para el anfitrión «{t.__name__}»")
