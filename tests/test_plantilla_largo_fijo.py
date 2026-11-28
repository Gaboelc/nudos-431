"""T21d: una plantilla atada con largo fijo, con la cuerda que sale de la mano.

En un amarre la cuerda pasa por debajo de un palo que descansa sobre ella en la mesa, y ahí solo cabe
la punta: la mano lleva lo que falta sin que se vea y la cuerda nueva sale de ella, quieta donde la
dibuja el paso (`poses_plantilla`, `_tramo_plantilla`, `animar_plantilla`). La cuerda tiene siempre
los mismos nodos: lo que está en la mano espera donde va a quedar, sin dibujarse (`cuerda_visible`).
"""
import numpy as np
import pytest

from nudos.animar import (COLA_MANO, VEL_SERIE, PoseVideo, _serie, _tramo_plantilla, animar_plantilla,
                          comprobar_poses_plantilla, cuerda_visible, de_plantilla, poses_plantilla,
                          visibles)
from nudos.fisica.atar import FPS, CuadroGuia, comprobar, seguir
from nudos.fisica.calidad import BRINCO, SECO, largo, medir


@pytest.fixture(scope="module")
def poses_amarre(modelo_amarre_cuadrado):
    return poses_plantilla(modelo_amarre_cuadrado)


def test_las_poses_del_amarre_miden_lo_mismo(modelo_amarre_cuadrado, poses_amarre):
    PP = poses_amarre
    N = len(modelo_amarre_cuadrado.pasos[-1].puntos)
    assert {len(p.X) for p in PP} == {N}
    total = (N - 1) * PP[0].h
    # Cada pausa muestra la ficha hasta el hito y la cola en la mano; la última, la cuerda entera.
    for p in PP[:-1]:
        assert p.visible == pytest.approx(p.largo + COLA_MANO)
        assert p.resaltado[1] == pytest.approx(p.largo)
    assert PP[-1].visible == pytest.approx(total) and PP[-1].cola == 0.0
    assert [p.visible for p in PP] == sorted(p.visible for p in PP)
    solido, _ = de_plantilla(modelo_amarre_cuadrado.spec, 2)
    # Lo que está en la mano en una pose es lo mismo en la siguiente: al salir no salta.
    assert comprobar_poses_plantilla(PP, solido) == []


def test_lo_que_esta_en_la_mano_no_se_ve():
    X = np.column_stack([np.arange(11) * 0.2, np.zeros(11), np.zeros(11)])
    V, s = cuerda_visible(X, 0.2, 1.1)
    # En una recta, la curva suave de la punta es la recta.
    assert len(V) == 7 and s[-1] == pytest.approx(1.1) and np.allclose(V[-1], [1.1, 0, 0])
    assert np.allclose(s[:-1], np.arange(6) * 0.2)
    # Junto a un nodo, la punta lo reemplaza: un tramo tan corto doblaría la malla.
    V, s = cuerda_visible(X, 0.2, 1.21)
    assert len(V) == 7 and s[-2] == pytest.approx(1.0) and s[-1] == pytest.approx(1.21)
    V, s = cuerda_visible(X, 0.2, None)
    assert len(V) == 11 and visibles(None, 0.2, 11) == 11


def test_la_mano_tiende_la_cuerda_quieta(modelo_amarre_cuadrado, poses_amarre):
    # Las vueltas que completan la serie (paso 3): la cuerda sale de la mano y queda quieta donde la
    # dibuja el paso, y la mano va más despacio en las curvas, sin cambios de rapidez en seco.
    spec = modelo_amarre_cuadrado.spec
    A, B = poses_amarre[1], poses_amarre[2]
    assert _serie(spec, 3) and not _serie(spec, 2)
    tr = _tramo_plantilla(A, B, serie=True)
    h = B.h
    n = [len(g.G) for g in tr.guia]
    assert n == sorted(n) and n[0] == visibles(A.visible, h, len(B.X)) and n[-1] == visibles(B.visible, h, len(B.X))
    a0 = n[0]
    for g in tr.guia:
        assert np.allclose(g.G[a0:], B.X[a0:len(g.G)])           # lo que sale queda donde lo dibuja B
    assert np.allclose(tr.guia[0].G, A.X[:a0]) and np.allclose(tr.guia[-1].G, B.X[:n[-1]])
    f1 = tr.fases["tender"][1]
    U = np.array(tr.visible[:f1 + 1])
    v = np.diff(U) * FPS
    assert U[0] == pytest.approx(A.visible) and U[-1] == pytest.approx(B.visible)
    assert np.all(v >= -1e-9) and v[0] < 1.0 and v[-1] < 1.0
    # La punta, con lo que se ve de cada cuadro de la guía: su rapidez cambia sin frenadas en seco
    # y no acelera como un brinco.
    punta = np.array([cuerda_visible(np.vstack([g.G, B.X[len(g.G):]]), h, u)[0][-1]
                      for g, u in zip(tr.guia, U)])
    rapidez = np.linalg.norm(np.diff(punta, axis=0), axis=1) * FPS
    assert rapidez.max() <= 1.05 * VEL_SERIE
    assert np.max(np.abs(np.diff(rapidez)) * FPS) < SECO
    acel = np.linalg.norm(np.diff(punta, n=2, axis=0), axis=1) * FPS ** 2
    assert acel.max() < BRINCO


def _recta(N, h, z=0.55):
    return np.column_stack([np.arange(N) * h, np.zeros(N), np.full(N, z)])


def test_la_cuerda_sale_de_la_mano_con_el_motor():
    # Una cuerda recta sobre la mesa: se ve hasta 4 d y la mano tiende el resto. Lo que sale entra
    # quieto donde esperaba, la cuerda tiene siempre los mismos nodos y nada se mueve.
    h, N = 0.2, 61
    X = _recta(N, h)
    A = PoseVideo(1, X.copy(), h, 0.0, 2.0, 2.0, X[:11], h, (0.0, 2.0), None, "mano", visible=4.0)
    B = PoseVideo(2, X.copy(), h, 0.0, 12.0, 0.0, X, h, (2.0, 12.0), None, "mano", visible=12.0)
    a = animar_plantilla(A, B)
    assert a.fallas == []
    assert {len(x) for x in a.X} == {N}
    assert len(a.visible) == len(a.X) and a.visible == sorted(a.visible)
    assert np.allclose(a.X[0], X) and np.allclose(a.X[-1], X)
    assert max(float(np.max(np.linalg.norm(x - X, axis=1))) for x in a.X) < 0.05
    bajo, alto = a.medidas["largo"]
    assert 0.995 <= bajo and alto <= 1.005


def test_comprobar_sabe_de_los_nodos_que_salen():
    # El motor agrega los nodos donde los pone la guía, y `comprobar` revisa el paso desde ahí.
    h = 0.2
    X = _recta(31, h)

    def cuadro(n):
        return CuadroGuia(G=X[:n].copy(), k=np.full(n, 5.0), manos=np.array([0]), largos=np.full(n - 1, h),
                          curvatura=np.zeros((n - 2, 3)), largo_fijo=True)

    c = seguir(X[:10], [cuadro(n) for n in (10, 12, 15, 15, 20)])
    assert [len(x) for x in c.X] == [10, 12, 15, 15, 20] and sorted(c.anadido) == [1, 2, 4]
    assert np.allclose(c.anadido[2], X[12:15])
    assert comprobar(c.X, medio=c.medio, anadido=c.anadido) == []
    assert any("sin decir cómo" in f for f in comprobar(c.X))


def test_la_calidad_mide_la_punta_que_se_ve():
    # La punta que sale de la mano entra a la medida como un nodo más; el largo es el que se da.
    X = _recta(20, 0.2)
    cuadros = [X.copy() for _ in range(30)]
    puntas = [np.array([1.0 + 0.1 * k, 0.0, 0.55]) for k in range(30)]
    puntas[15] = puntas[15] + [0.0, 0.3, 0.0]
    m = medir(cuadros, FPS, puntas=puntas, largos=[largo(x) for x in cuadros])
    assert m["nodos"]["min"] == m["nodos"]["max"] == 20
    assert m["brincos"] >= 1 and m["punta"]["velocidad"]["p50"] == pytest.approx(6.0)
    assert m["largo"]["variacion"] == 0.0
