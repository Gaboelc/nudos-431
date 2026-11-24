"""T15a: lo que T14a aprendió de ipctk, en nudos/fisica/contacto.py."""
from __future__ import annotations

import math

import numpy as np
import pytest

from nudos.fisica.contacto import DHAT, DMIN, MallaContacto, cilindro


def recta(n=40, h=0.2, origen=(0.0, 0.0, 0.5), direccion=(1.0, 0.0, 0.0)):
    d = np.asarray(direccion, float)
    return np.asarray(origen, float) + h * np.arange(n)[:, None] * d / np.linalg.norm(d)


def horquilla(separacion, h=0.2, largo=6.0):
    """Una cuerda que va, da media vuelta y vuelve paralela a `separacion` entre ejes."""
    n = int(largo / h)
    ida = np.column_stack([h * np.arange(n), np.zeros(n), np.full(n, 0.5)])
    r = separacion / 2
    t = np.linspace(0, math.pi, max(3, int(math.pi * r / h)))[1:-1]
    curva = np.column_stack([ida[-1, 0] + r * np.sin(t), r - r * np.cos(t), np.full(len(t), 0.5)])
    vuelta = ida[::-1] + [0.0, separacion, 0.0]
    return np.vstack([ida, curva, vuelta])


def test_la_cuerda_apoyada_queda_a_media_franja_de_la_mesa():
    X = recta()
    m = MallaContacto(X, altura_mesa=0.0)
    assert m.distancia_minima(X) == pytest.approx(DMIN + DHAT / 2, abs=1e-9)
    # Más alto, la cuerda sale de la franja de la barrera y no hay contacto con la mesa.
    assert m.distancia_minima(X + [0, 0, 0.2]) == math.inf
    # Y no se hunde: bajarla 1 diámetro se recorta en el borde de la franja.
    alfa = m.paso_libre(X, X - [0, 0, 1.0])
    assert alfa == pytest.approx(DHAT / 2, abs=0.01)


def test_el_plano_de_ipctk_no_sirve_de_mesa():
    # En ipctk 1.6.1, un Hyperplane solo ve los nodos a menos de (dmin + dhat)/2: una cuerda
    # apoyada a dmin + dhat/2 no tiene contacto con él. Por eso la mesa es una malla. Si esta
    # prueba falla al cambiar de versión, el plano volvió a servir.
    import ipctk
    X = recta(n=4)
    E = np.array([[0, 1], [1, 2], [2, 3]], np.int32)
    m = ipctk.CollisionMesh(np.asfortranarray(X), np.asfortranarray(E), np.zeros((0, 3), np.int32))
    m.can_collide = ipctk.make_static_obstacle_filter(4)

    def contactos(distancia):
        # Hyperplane(normal, origen): primero la normal.
        m.planes = [ipctk.Hyperplane(np.array([0.0, 0.0, 1.0]), np.array([0.0, 0.0, 0.5 - distancia]))]
        col = ipctk.NormalCollisions()
        col.build(m, np.asfortranarray(X), DHAT, DMIN)
        return len(col.pv_collisions)

    assert contactos(DMIN + DHAT / 2) == 0
    assert contactos((DMIN + DHAT) / 2 - 0.01) == 4


def test_la_distancia_minima_no_viene_al_cuadrado():
    X = horquilla(1.02)
    m = MallaContacto(X)
    assert m.distancia_minima(X) == pytest.approx(1.02, abs=1e-6)


def test_los_vecinos_a_lo_largo_de_la_cuerda_no_chocan():
    X = recta(n=200)
    m = MallaContacto(X)
    assert len(m.colisiones(X)) == 0
    # Pero sí dos tramos lejanos a lo largo de la cuerda que se acercan.
    X = horquilla(1.0)
    assert len(MallaContacto(X).colisiones(X)) > 0


def test_la_ccd_no_deja_que_un_tramo_atraviese_a_otro():
    X0 = horquilla(2.0)
    m = MallaContacto(X0)
    # La vuelta se mueve 3 diámetros hacia la ida: la atravesaría.
    X1 = X0.copy()
    mitad = len(X0) // 2
    X1[mitad + 10:, 1] -= 3.0
    alfa = m.paso_libre(X0, X1)
    assert 0 < alfa < 1
    Xa = X0 + alfa * (X1 - X0)
    assert m.distancia_minima(Xa) >= DMIN - 1e-6
    # Un paso que no acerca nada se da entero.
    assert m.paso_libre(X0, X0 + [0.3, 0, 0]) == 1.0


def test_la_cuerda_no_atraviesa_un_palo():
    palo = cilindro((3.0, 0.0, 3.0), (0, 1, 0), radio=2.5, largo=10.0)
    X0 = recta(n=30, origen=(0.0, -3.0, 6.5), direccion=(1, 0, 0)) + [0, 3.0, 0]
    m = MallaContacto(X0, [palo])
    X1 = X0 - [0, 0, 4.0]   # bajarla 4 diámetros la metería dentro del palo
    alfa = m.paso_libre(X0, X1)
    assert 0 < alfa < 1
    assert m.distancia_minima(X0 + alfa * (X1 - X0)) >= DMIN - 1e-6


@pytest.mark.parametrize("radio", [0.75, 1.5, 2.5])
def test_el_palo_de_64_lados_es_casi_redondo(radio):
    palo = cilindro((0, 0, 0), (1, 0, 0), radio=radio, largo=4.0)
    # Los vértices están en la superficie; el centro de cada cara, a lo más esto por dentro.
    assert np.allclose(np.hypot(palo.V[:, 1], palo.V[:, 2]), radio)
    centros = palo.V[palo.F].mean(axis=1)
    hundido = radio - np.hypot(centros[:, 1], centros[:, 2])
    assert hundido.max() < 0.003


def test_calcular_dos_veces_da_lo_mismo():
    rng = np.random.default_rng(431)
    X = horquilla(1.0) + rng.normal(scale=0.01, size=(1, 3))
    X[:, 2] += rng.normal(scale=0.02, size=len(X))
    palo = cilindro((3.0, 0.5, -2.2), (0, 1, 0), radio=2.5, largo=10.0)
    resultados = []
    for _ in range(2):
        m = MallaContacto(X, [palo], altura_mesa=0.0)
        col = m.colisiones(X)
        resultados.append((len(col), m.distancia_minima(X), m.paso_libre(X, X - [0, 0, 1.0])))
    assert resultados[0] == resultados[1]
