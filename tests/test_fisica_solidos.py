"""T15f: los anfitriones como mallas para el motor (nudos/fisica/solidos.py)."""
from __future__ import annotations

import numpy as np
import pytest

from nudos.anfitrion import solido
from nudos.fisica.asentar import HOLGURA_SOLIDO, solidos
from nudos.fisica.contacto import DHAT, DMIN
from nudos.plantillas.puno import _dedos
from nudos.spec import Anfitrion, cargar

# La cuerda que toca la madera queda a dmin + dhat/2 + la holgura de la malla (T15d).
TOCA = DMIN + DHAT / 2 + HOLGURA_SOLIDO


def _distancia(P, mallas) -> np.ndarray:
    """La distancia de cada punto P (n, 3) a la malla más cercana (punto contra triángulo)."""
    mejor = np.full(len(P), np.inf)
    for s in mallas:
        A, B, C = (s.V[s.F[:, k]] for k in range(3))
        for i, p in enumerate(P):
            mejor[i] = min(mejor[i], float(_punto_triangulo(p, A, B, C).min()))
    return mejor


def _punto_triangulo(p, A, B, C) -> np.ndarray:
    """La distancia de p a cada triángulo (A, B, C), por el punto más cercano del plano si cae
    dentro y, si no, por la arista más cercana."""
    AB, AC = B - A, C - A
    n = np.cross(AB, AC)
    area = np.linalg.norm(n, axis=1)
    ok = area > 1e-12
    n = n / np.where(ok, area, 1.0)[:, None]
    d = np.einsum("ij,ij->i", p - A, n)
    q = p - d[:, None] * n
    # Coordenadas baricéntricas de q.
    v0, v1, v2 = AB, AC, q - A
    d00, d01, d11 = (np.einsum("ij,ij->i", a, b) for a, b in ((v0, v0), (v0, v1), (v1, v1)))
    d20, d21 = np.einsum("ij,ij->i", v2, v0), np.einsum("ij,ij->i", v2, v1)
    den = np.where(ok, d00 * d11 - d01 * d01, 1.0)
    v = (d11 * d20 - d01 * d21) / den
    w = (d00 * d21 - d01 * d20) / den
    dentro = ok & (v >= 0) & (w >= 0) & (v + w <= 1)
    aristas = np.min([_punto_segmento(p, a, b) for a, b in ((A, B), (B, C), (C, A))], axis=0)
    return np.where(dentro, np.abs(d), aristas)


def _punto_segmento(p, a, b) -> np.ndarray:
    ab = b - a
    t = np.clip(np.einsum("ij,ij->i", p - a, ab) / np.maximum(np.einsum("ij,ij->i", ab, ab), 1e-12), 0, 1)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def _tocando(anfitrion, caja, n=150, semilla=0):
    """Puntos al azar dentro de `caja` ((x0, y0, z0), (x1, y1, z1)) llevados por `empujar` a la
    superficie donde la cuerda toca la madera (solo los que estaban dentro)."""
    rng = np.random.default_rng(semilla)
    lo, hi = (np.asarray(c, float) for c in caja)
    X = lo + rng.random((n * 4, 3)) * (hi - lo)
    antes = X.copy()
    anfitrion.empujar(X, np.ones(len(X), bool))
    movidos = np.linalg.norm(X - antes, axis=1) > 1e-6
    X = X[movidos & np.array([anfitrion.penetracion(x[None]) < 1e-6 for x in X])]
    return X[:n]


def _anfitrion(slug):
    if slug == "tubo":   # la cabeza de turco publicada es un nudo libre; el tubo es de su plantilla
        return solido(Anfitrion(tipo="tubo", radio=3.0, largo=12.0))
    return solido(cargar(slug).anfitrion)


CASOS = {
    # slug: la caja de donde salen los puntos, lejos de las puntas abiertas de cada malla.
    "ballestrinque": ((-10, -3, 0), (10, 3, 5)),        # el poste
    "amarre-cuadrado": ((-3, -3, 0), (3, 3, 13)),       # la cruz
    "amarre-redondo": ((-15, -8, 0), (15, 8, 8)),       # dos palos
    "amarre-tripode": ((-15, -12, 0), (15, 12, 8)),     # tres palos
    "tubo": ((-5, -6, 0), (5, 6, 10)),                  # el de la cabeza de turco
    "refuerzo-de-cabo": ((-25, -4, 0), (-3, 4, 8)),     # el cabo
    "eslinga-de-andamio": ((-25, -7, 0), (-3, 7, 5)),   # el tablón
    "vuelta-de-cornamusa": ((-9, -3, 0.6), (9, 3, 5)),  # la cornamusa
    "eslinga-de-barril": ((-7, -7, 0), (7, 7, 13)),     # el barril
    "nudo-aguja": ((-3, -3, 0.4), (3, 3, 1.6)),         # el destorcedor
    "tensor-ajustable": ((-3, -3, 0.4), (3, 3, 4.6)),   # la estaca
}


@pytest.mark.parametrize("slug", sorted(CASOS))
def test_la_cuerda_que_toca_la_madera_queda_al_borde_de_la_barrera(slug):
    """Donde la geometría de siempre apoya la cuerda en la madera, la malla queda a dmin +
    dhat/2 + HOLGURA_SOLIDO del eje: la cuerda toca sin apretar. En los cantos vivos de la
    malla del tablón queda algo más lejos (hasta 0,11·√2), y las caras de un prisma de 64 lados
    quedan algo más cerca que la madera redonda."""
    a = _anfitrion(slug)
    P = _tocando(a, CASOS[slug])
    assert len(P) >= 50
    d = _distancia(P, solidos(a))
    assert d.min() > TOCA - 0.02
    assert d.max() < TOCA + 0.1
    assert np.median(d) == pytest.approx(TOCA, abs=0.02)


def test_los_dedos_del_puno_de_mono():
    dedos = _dedos(3)
    P = _tocando(dedos, ((-dedos.x - 3, -3, 0.4), (dedos.x + 3, 3, dedos.alto + 1)))
    d = _distancia(P, solidos(dedos))
    assert len(P) >= 50
    assert d.min() > TOCA - 0.02 and d.max() < TOCA + 0.1


def test_una_cuerda_mas_gruesa_queda_igual_de_al_borde():
    """Con una cuerda de grosor g, la malla va g/2 + holgura·g adentro: la que toca la madera
    queda a g·(dmin + dhat/2 + holgura), como su barrera."""
    a = _anfitrion("ballestrinque")
    P = _tocando(a, CASOS["ballestrinque"])
    # La cuerda de grosor 2 toca la madera medio diámetro más afuera.
    _, th, _ = a.cilindricas(P)
    P2 = a.punto(P[:, 0], np.degrees(th), a.rb + 0.5)
    d = _distancia(P2, solidos(a, grosor=2.0))
    assert np.median(d) == pytest.approx(2 * TOCA, abs=0.03)


def test_el_destorcedor_es_de_metal():
    from nudos.fisica.materiales import CUERDA_8MM
    (m,) = solidos(_anfitrion("nudo-aguja"))
    assert m.mu == CUERDA_8MM.mu_metal
    assert all(s.mu is None for s in solidos(_anfitrion("tensor-ajustable")))
