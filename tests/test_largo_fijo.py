"""T21: atar con largo fijo.

La cuerda del video mide lo mismo en todos los cuadros: cada pausa es la ficha exacta con un
depósito de firme detrás y una cola de más delante de la punta (`poses_video`), la mano toma la
cuerda cerca de la punta y la enhebra, y lo que todavía no pasó queda suelto. Con el gancho de
test_atar.py, que es corto, y con las poses del as de guía.
"""
import types

import numpy as np
import pytest

from nudos.animar import (_cola, _recorrido_largo, animar_largo, comprobar_poses, poses_video)
from nudos.cruces import encontrar_cruces, secuencia_obtenida
from nudos.fisica.asentar import separar
from nudos.fisica.atar import FPS
from nudos.libre import catmull_rom, elevar, remuestrear

# El gancho de test_atar.py: un tramo recto, una vuelta y la cola que vuelve por arriba; en el
# paso 2 la cola sigue y baja cruzando el primer tramo.
BASE = [[-8.0, 0.0], [-4.0, 0.0], [0.0, 0.0], [4.0, 0.0], [6.5, 1.5], [6.5, 4.5], [4.0, 6.0],
        [1.0, 6.0]]
COLA = [[-1.0, 5.0], [-1.5, 2.5], [-1.5, -0.5], [-1.5, -3.0]]


def _pose(puntos, encima=None):
    D, ctrl = catmull_rom(np.asarray(puntos, float))
    X2, h, s_ctrl = remuestrear(D, ctrl)
    cruces = encontrar_cruces(X2, h)
    if cruces:
        X = elevar(X2, h, cruces, [encima] * len(cruces))
    else:
        X = np.column_stack([X2, np.full(len(X2), 0.5)])
    return separar(X, h), h, s_ctrl


def _modelo(pasos):
    """Un modelo mínimo de un nudo libre con los pasos [(X, h, resaltado, esperada)]."""
    spec = types.SimpleNamespace(plantilla=None, anfitrion=None, slug="gancho")
    P = [types.SimpleNamespace(n=i + 1, puntos=X, h=h, resaltado=r, esperada=e)
         for i, (X, h, r, e) in enumerate(pasos)]
    return types.SimpleNamespace(spec=spec, pasos=P, apretado=None)


@pytest.fixture(scope="module")
def gancho():
    A, hA, _ = _pose(BASE)
    out = {}
    for encima in (True, False):
        B, h, s_ctrl = _pose(BASE + COLA, encima=not encima)
        esperada = secuencia_obtenida(B, h, encontrar_cruces(B, h))
        res = (float(s_ctrl[len(BASE) - 1]), float(s_ctrl[-1]))
        out[encima] = poses_video(_modelo([(A, hA, None, None), (B, h, res, tuple(esperada))]))
    return out


def test_la_mano_arranca_y_frena_sin_cambios_en_seco():
    # La mano va a 5 d/s y frena a 2,5 cerca de un cruce, en u = 10: sin escalones de velocidad.
    U = _recorrido_largo(0.0, 20.0, lambda u: 2.5 if 9.0 < u < 11.0 else 5.0)
    assert U[0] == 0.0 and U[-1] == pytest.approx(20.0)
    v = np.diff(U) * FPS
    assert np.all(v >= -1e-9)
    assert v[0] < 0.2 and v[-1] < 0.2           # arranca y frena desde quieta
    a = np.diff(v) * FPS
    assert np.max(np.abs(a)) < 30.0              # T21a: la mano de T17 llegaba a unos 17 y la punta a 50
    j = np.diff(a) * FPS
    assert np.max(np.abs(j)) < 400.0             # la aceleración también es continua


def test_la_cola_va_acostada_si_cabe_y_si_no_sube():
    X = np.column_stack([np.linspace(0, 10, 51), np.zeros(51), np.full(51, 0.5)])
    C, l, arco = _cola(X, 0.2, 6.0, [])
    assert not arco
    assert np.allclose(C[:, 2], 0.5) and np.allclose(C[:, 1], 0.0)   # sigue derecho, sobre la mesa
    assert l[-1] >= 6.0
    # Con un anillo de cuerda alrededor de la punta, no cabe en la mesa: sube.
    t = np.linspace(0, 2 * np.pi, 120)
    anillo = np.column_stack([10 + 3 * np.cos(t), 3 * np.sin(t), np.full(len(t), 0.5)])
    C, l, arco = _cola(X, 0.2, 6.0, [anillo])
    assert arco and C[-1, 2] > 3.0
    # El largo es el del espacio: los puntos quedan a lo que dice l, aunque suba.
    assert np.allclose(np.linalg.norm(np.diff(C, axis=0), axis=1), np.diff(l))


def test_las_poses_del_gancho_miden_lo_mismo(gancho):
    P1, P2 = gancho[True]
    assert len(P1.X) == len(P2.X)
    assert P2.cola == pytest.approx(0.0) and P1.o == pytest.approx(0.0)
    assert P1.cola == pytest.approx(P2.largo - P1.largo, abs=P1.h)
    assert P2.modo == "punta"
    assert comprobar_poses([P1, P2]) == []


def test_las_poses_del_as_de_guia(modelo_as_de_guia):
    PV = poses_video(modelo_as_de_guia)
    assert len({len(p.X) for p in PV}) == 1
    # La cuerda mide lo que pide el paso más largo con lo que todavía le falta al firme, y el
    # último paso no lleva cola de más (el apretado del video parte de él).
    assert PV[-1].cola == pytest.approx(0.0) and PV[-1].o == pytest.approx(0.0)
    assert [p.modo for p in PV][1:3] == ["firme", "punta"]
    for p in PV:
        assert p.o + p.largo + p.cola == pytest.approx((len(p.X) - 1) * p.h, abs=1e-6)
        assert p.resaltado is None or p.resaltado[0] >= p.o
    assert comprobar_poses(PV) == []


@pytest.mark.parametrize("encima", [True, False])
def test_atar_el_gancho_con_largo_fijo(gancho, encima):
    P1, P2 = gancho[encima]
    a = animar_largo(P1, P2)
    assert a.fallas == []
    assert {len(x) for x in a.X} == {len(P1.X)}
    assert np.array_equal(a.X[0], P1.X) and np.array_equal(a.X[-1], P2.X)
    bajo, alto = a.medidas["largo"]
    assert 0.995 <= bajo and alto <= 1.005
    assert a.medidas["distancia_final"] < 0.3
    # La cola cruzó por el lado declarado: la secuencia del último cuadro del motor.
    x = a.X[a.fases["acercar"][0] - 1]
    i, j = P2.tramo_ficha()
    xs = x[i:j + 1]
    assert secuencia_obtenida(xs, P2.h, encontrar_cruces(xs, P2.h)) == list(P2.esperada)


def test_atar_con_largo_fijo_dos_veces_da_lo_mismo(gancho):
    P1, P2 = gancho[True]
    a, b = animar_largo(P1, P2), animar_largo(P1, P2)
    assert len(a.X) == len(b.X) and all(np.array_equal(x, y) for x, y in zip(a.X, b.X))
