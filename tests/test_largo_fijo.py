"""T21: atar con largo fijo.

La cuerda del video mide lo mismo en todos los cuadros: cada pausa es la ficha con un depósito de
firme detrás y la cuerda de más acostada delante de la punta o, si ahí no cabe, en una bolsa
(`poses_video`); la mano toma la cuerda cerca de la punta y la enhebra, y lo que todavía no pasó
queda suelto, o se achica guiado si es una bolsa (`_Cinta`). Con el gancho de test_atar.py, que es
corto, y con las poses del as de guía.
"""
import math
import types

import numpy as np
import pytest

from nudos.animar import (ALTO_MANO, BOLSA_RAMPA, GAZA_ARRIBA, RADIO_GUIA, _cola, _inflar,
                          _por_largo, _recorrido_largo, _tramo_largo_enhebrar, _tramo_largo_firme,
                          _tramo_largo_gaza, _tramo_largo_punta, animar_largo, comprobar_poses,
                          poses_video, radio_minimo)
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


def test_la_cola_va_acostada_si_cabe():
    X = np.column_stack([np.linspace(0, 10, 51), np.zeros(51), np.full(51, 0.5)])
    C, l = _cola(X, 0.2, 6.0, [])
    assert np.allclose(C[:, 2], 0.5) and np.allclose(C[:, 1], 0.0)   # sigue derecho, sobre la mesa
    assert l[-1] >= 6.0
    assert np.allclose(np.linalg.norm(np.diff(C, axis=0), axis=1), np.diff(l))
    # Con un anillo de cuerda alrededor de la punta, no cabe en la mesa sin cruzarla: la cuerda de
    # más va en una bolsa (antes subía en arco fuera del cuadro).
    t = np.linspace(0, 2 * np.pi, 120)
    anillo = np.column_stack([10 + 3 * np.cos(t), 3 * np.sin(t), np.full(len(t), 0.5)])
    assert _cola(X, 0.2, 6.0, [anillo]) is None


def test_la_bolsa_se_estira_sin_doblar_mas():
    # Una vuelta de 180° de radio 2 entre dos tramos rectos: inflada 6 d, sale como una lengua más
    # larga con las mismas puntas y la misma dirección en ellas, y no dobla más cerrado.
    a = np.linspace(np.pi / 2, -np.pi / 2, 200)
    vuelta = np.column_stack([2 * np.cos(a), 2 * np.sin(a)])
    P2 = np.vstack([np.column_stack([np.linspace(-2, 0, 40, endpoint=False), np.full(40, 2.0)]), vuelta,
                    np.column_stack([np.linspace(0, -2, 41)[1:], np.full(40, -2.0)])])
    P = np.column_stack([P2, np.full(len(P2), 0.5)])
    Y = _inflar(P, 6.0)
    assert Y is not None
    largo = lambda Z: float(np.sum(np.linalg.norm(np.diff(Z, axis=0), axis=1)))
    assert largo(Y) == pytest.approx(largo(P) + 6.0, abs=1e-3)
    assert np.allclose(Y[0], P[0]) and np.allclose(Y[-1], P[-1])

    def angulo(d):
        return math.degrees(math.atan2(d[1], d[0]))

    for i, j in ((0, 3), (-4, -1)):
        assert abs(angulo(Y[j] - Y[i]) - angulo(P[j] - P[i])) < 2.0
    assert radio_minimo(_por_largo(Y, 0.2)[0]) >= min(RADIO_GUIA, radio_minimo(_por_largo(P, 0.2)[0]))
    assert np.max(Y[:, 0]) > np.max(P[:, 0]) + 2.0         # se alarga hacia afuera de la vuelta


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
    total = (len(PV[0].X) - 1) * PV[0].h
    # La cuerda mide lo que pide el paso más largo con lo que todavía le falta al firme, y el
    # último paso no lleva cuerda de más (el apretado del video parte de él).
    assert PV[-1].cola == pytest.approx(0.0) and PV[-1].o == pytest.approx(0.0) and PV[-1].bolsa is None
    assert [p.modo for p in PV][1:3] == ["firme", "punta"]
    # La cuerda de más (T21c): en el paso 3 no cabe después de la punta, que apunta a la gaza
    # pequeña, así que espera en la gaza grande, y también en los pasos 1 y 2, a los que se llega
    # sin que la punta pase por ningún cruce. En los 4 y 5 va acostada, y en el 6, en la vuelta del
    # collar.
    assert [p.bolsa is not None for p in PV] == [True, True, True, False, False, True, False]
    for p in PV:
        sobra = p.bolsa[2] if p.bolsa else 0.0
        assert p.o + p.largo + p.cola + sobra == pytest.approx(total, abs=1e-6)
        assert p.resaltado is None or p.resaltado[0] >= p.o
        if p.bolsa:
            # Sin cola: la punta de la cuerda es la del chicote de la ficha, a la vista.
            assert p.cola == 0.0 and p.fin == pytest.approx(total)
    # Desde el paso 3, la ficha resalta hasta la punta, y el video también: hasta la de la cuerda,
    # con la cola acostada, que va adelante al enhebrar.
    assert all(p.resaltado[1] == pytest.approx(total) for p in PV[2:])
    assert PV[1].resaltado[1] < PV[1].fin - 10
    # La de la gaza es el mismo tramo de cuerda en los tres pasos; la del collar va en la cuerda que
    # el paso 6 tiende.
    assert PV[0].bolsa[0] == pytest.approx(PV[2].bolsa[0])
    assert PV[5].bolsa_ficha[0] >= (PV[5].r1 - 1) * PV[5].h_ficha - BOLSA_RAMPA
    assert comprobar_poses(PV) == []


def test_acercar_el_chicote_lo_lleva_la_mano(modelo_as_de_guia):
    # En el paso 3 la punta no pasa por ningún cruce nuevo: la mano la lleva levantada y todo va
    # guiado, sin aire ni cuerda suelta (por el aire, con lo de detrás suelto, el chicote se
    # doblaba en un gancho). En los pasos 4 a 7 la punta enhebra.
    PV = poses_video(modelo_as_de_guia)
    assert PV[2].modo == "punta" and not PV[2].enhebra
    assert all(p.enhebra for p in PV[3:])
    A, B = PV[1], PV[2]
    tr = _tramo_largo_firme(A, B, mano=True)
    assert tr.modo == "mano" and "aire" not in tr.fases
    assert all(np.all(g.k > 0) for g in tr.guia)
    f0, f1 = tr.fases["acomodar"]
    medio = tr.guia[(f0 + f1) // 2].G
    recta = (A.X[-1] + B.X[-1]) / 2
    assert medio[-1, 2] > recta[2] + 0.8 * ALTO_MANO          # la punta va levantada
    assert np.allclose(tr.guia[f1].G, B.X)


def _sin_saltos(tr, A, B, fin: str):
    """La guía parte de A, llega a B al terminar la fase `fin` y no salta más de 0,5 d."""
    G = [g.G for g in tr.guia]
    assert np.max(np.linalg.norm(G[0] - A.X, axis=1)) < 0.05
    assert np.max(np.linalg.norm(G[tr.fases[fin][1]] - B.X, axis=1)) < 0.05
    assert max(float(np.max(np.linalg.norm(b - a, axis=1))) for a, b in zip(G[:-1], G[1:])) < 0.5
    largo = np.array([np.sum(np.linalg.norm(np.diff(g, axis=0), axis=1)) for g in G]) / ((len(B.X) - 1) * B.h)
    assert largo.min() > 0.98 and largo.max() < 1.05
    return G


def test_la_gaza_pequena_se_forma_volteando_una_bolsa(modelo_as_de_guia):
    # Paso 2: la cuerda que entra por el firme forma la gaza pequeña. Un lazo no sale de una
    # cuerda acostada sin levantarla (nodo a nodo, el firme se ondulaba y la gaza nacía de un
    # gancho): sale una bolsa junto al cruce, se voltea con el tramo del chicote por arriba del
    # firme y crece hasta su tamaño, y el firme corre derecho.
    PV = poses_video(modelo_as_de_guia)
    A, B = PV[0], PV[1]
    tr = _tramo_largo_gaza(A, B)
    assert tr is not None and tr.modo == "gaza"
    assert {"bolsa", "voltear", "crecer", "asentar"} <= set(tr.fases)
    G = _sin_saltos(tr, A, B, "crecer")
    h = B.h
    s = np.arange(len(B.X)) * h
    for g in G[:tr.fases["bolsa"][1] + 1]:
        assert not encontrar_cruces(g, h)                     # la bolsa no se cruza
    for g in G[tr.fases["voltear"][1]:tr.fases["crecer"][1] + 1]:
        (c,) = encontrar_cruces(g, h)
        a, b = sorted((c.sa, c.sb))
        assert np.interp(b, s, g[:, 2]) > np.interp(a, s, g[:, 2])   # el del chicote, encima
    # El firme, por encima de la gaza, a menos de 0,3 d de su recta en todo el paso.
    (c,) = encontrar_cruces(B.X, h)
    j = int(min(c.sa, c.sb) / h)
    alto = B.X[j, 1] + GAZA_ARRIBA
    yf, xf = B.X[j::-1, 1], B.X[j::-1, 0]
    for g in G:
        arriba = (g[:, 1] > alto) & (g[:, 1] < yf[-1])
        assert np.all(np.abs(g[arriba, 0] - np.interp(g[arriba, 1], yf, xf)) < 0.3)


def test_cada_paso_del_as_de_guia_se_ata_a_su_manera(modelo_as_de_guia):
    # La punta enhebra en los pasos 4 a 7: con la cinta si ya está en el camino (4 y 7); si no,
    # con el lazo o el barrido, según quepa la bolsa (6 y 5). Nunca por el aire con la cola
    # suelta, que se amontonaba en un rollo.
    PV = poses_video(modelo_as_de_guia)
    assert [_tramo_largo_enhebrar(A, B).modo for A, B in zip(PV[2:-1], PV[3:])] == \
        ["cinta", "barrido", "lazo", "cinta"]


def test_pasar_bajo_el_firme_barre_la_cola(modelo_as_de_guia):
    # Paso 5: la punta está lejos, al final de la cola acostada (23 d), y la bolsa del lazo se
    # cruzaría a sí misma (las dos puntas de la bolsa van casi paralelas junto al nudo): la cola
    # gira entera por debajo del firme, sin estirarse, y el firme sube mientras pasa.
    PV = poses_video(modelo_as_de_guia)
    A, B = PV[3], PV[4]
    tr = _tramo_largo_enhebrar(A, B)
    assert tr.modo == "barrido"
    G = _sin_saltos(tr, A, B, "barrer")
    h = B.h
    s = np.arange(len(B.X)) * h
    firme = min(min(c.sa, c.sb) for c in encontrar_cruces(A.X, h))     # donde empieza la gaza pequeña
    cola = B.en_video((B.r1 - 1) * B.h_ficha)
    for g in G[:tr.fases["barrer"][1] + 1]:
        for c in encontrar_cruces(g, h):
            lo, hi = sorted((c.sa, c.sb))
            if lo < firme and hi >= cola:
                assert np.interp(lo, s, g[:, 2]) > np.interp(hi, s, g[:, 2])   # el firme, encima


def test_volver_por_encima_dobla_la_cola_en_un_lazo(modelo_as_de_guia):
    # Paso 6: la cola acostada (15 d) se dobla, sin estirarse ni cruzarse, en una bolsa junto al
    # firme; después la punta lo cruza por encima y la bolsa se achica hasta la vuelta del collar.
    PV = poses_video(modelo_as_de_guia)
    A, B = PV[4], PV[5]
    tr = _tramo_largo_enhebrar(A, B)
    assert tr.modo == "lazo" and {"aire", "enhebrar", "asentar"} <= set(tr.fases)
    G = _sin_saltos(tr, A, B, "tirar")
    cola = B.en_video((B.r1 - 1) * B.h_ficha)
    for g in G:
        assert not [c for c in encontrar_cruces(g, B.h) if min(c.sa, c.sb) >= cola]


@pytest.mark.parametrize("n", [4, 7])
def test_la_bolsa_se_achica_mientras_la_mano_tira(modelo_as_de_guia, n):
    # Al subir el chicote por la gaza pequeña (paso 4) y al bajarlo (paso 7), la punta ya está en
    # el camino nuevo: la mano tira sin levantarla por el aire, y la gaza grande, o la vuelta del
    # collar, se achica guiada hasta la pose del paso. La guía parte de A, llega a B y no salta.
    PV = poses_video(modelo_as_de_guia)
    A, B = PV[n - 2], PV[n - 1]
    tr = _tramo_largo_punta(A, B)
    assert tr.modo == "cinta" and "aire" not in tr.fases
    G = [g.G for g in tr.guia]
    assert np.max(np.linalg.norm(G[0] - A.X, axis=1)) < 0.05
    assert np.max(np.linalg.norm(G[tr.fases["asentar"][0] - 1] - B.X, axis=1)) < 0.05
    assert max(float(np.max(np.linalg.norm(b - a, axis=1))) for a, b in zip(G[:-1], G[1:])) < 0.3
    largo = np.array([np.sum(np.linalg.norm(np.diff(g, axis=0), axis=1)) for g in G]) / ((len(B.X) - 1) * B.h)
    assert largo.min() > 0.99 and largo.max() < 1.03


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
