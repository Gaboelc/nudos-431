"""T17: atar con el motor, con cuerdas cortas.

Una cuerda en forma de gancho cuya punta, en el paso siguiente, cruza el primer tramo por encima
o por debajo. La guía (`nudos/animar.py`) tiene que llevarla por el lado declarado, el motor
(`nudos/fisica/atar.py`) no tiene que dejar que se atraviese, y la comprobación de los cuadros
tiene que ver cuando una cuerda pasa a través de otra.
"""
import numpy as np
import pytest

from nudos.animar import animar_tramo, tramo
from nudos.cruces import encimas, encontrar_cruces, secuencia_obtenida
from nudos.fisica.asentar import separar
from nudos.fisica.atar import comprobar, seguir
from nudos.libre import TrazadoError, catmull_rom, elevar, remuestrear

# El gancho: un tramo recto a lo largo de x, una vuelta y la cola que vuelve por arriba.
BASE = [[-8.0, 0.0], [-4.0, 0.0], [0.0, 0.0], [4.0, 0.0], [6.5, 1.5], [6.5, 4.5], [4.0, 6.0],
        [1.0, 6.0]]
# La cola sigue y baja cruzando el primer tramo en x = -1.
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


@pytest.fixture(scope="module")
def gancho():
    A, hA, _ = _pose(BASE)
    out = {}
    for encima in (True, False):
        # La segunda pasada (la cola) va encima si la primera va debajo.
        B, h, s_ctrl = _pose(BASE + COLA, encima=not encima)
        out[encima] = (A, B, h, (float(s_ctrl[len(BASE) - 1]), float(s_ctrl[-1])))
    return out


@pytest.mark.parametrize("encima", [True, False])
def test_la_punta_cruza_por_el_lado_declarado(gancho, encima):
    A, B, h, resaltado = gancho[encima]
    cruces = encontrar_cruces(B, h)
    esperada = secuencia_obtenida(B, h, cruces)
    assert esperada == (["1U", "1O"] if encima else ["1O", "1U"])
    a = animar_tramo(2, A, B, h, resaltado, esperada=esperada)
    assert a.fallas == []
    assert a.medidas["distancia_encaje"] < 0.3
    # El último cuadro del motor, antes de la recta, ya tiene el cruce del lado declarado.
    x = a.X[a.fases["encaje"][0] - 1]
    assert secuencia_obtenida(x, h, encontrar_cruces(x, h)) == esperada
    assert np.array_equal(a.X[-1], B)
    # La mano dio cuerda: la cuerda crece y termina con los nodos de B.
    assert len(a.X[0]) == len(A) and len(a.X[-1]) == len(B)


def test_por_debajo_la_guia_levanta_el_tramo(gancho):
    A, B, h, resaltado = gancho[False]
    tr = tramo(2, A, B, h, resaltado)
    # El tramo de abajo del cruce (la base, en x = -1.5) sube antes de que llegue la punta.
    s = np.arange(len(A)) * h
    i = int(np.argmin(np.abs(A[:, 0] + 1.5) + np.abs(A[:, 1])))
    alto = max(g.G[i, 2] for g in tr.guia[:tr.fases["enhebrar"][1]])
    assert alto > A[i, 2] + 1.5


def test_un_cruce_al_reves_en_los_dos_pasos_falla_antes_de_simular(gancho):
    _, B_debajo, h, _ = gancho[False]
    _, B_encima, _, _ = gancho[True]
    # Sin cuerda nueva: la cola no se recoge, así que el cruce sigue de un paso al otro.
    # (Con la cola resaltada, la guía la recogería y la volvería a pasar por debajo.)
    fin = (len(B_debajo) - 1) * h
    with pytest.raises(TrazadoError, match="al revés"):
        tramo(3, B_encima, B_debajo, h, (fin, fin))


def test_atar_dos_veces_da_lo_mismo(gancho):
    A, B, h, resaltado = gancho[True]
    tr = tramo(2, A, B, h, resaltado)
    c1 = seguir(tr.x0, tr.guia[:40])
    c2 = seguir(tr.x0, tr.guia[:40])
    assert all(np.array_equal(a, b) for a, b in zip(c1.X, c2.X))


def test_la_comprobacion_ve_una_cuerda_que_atraviesa_a_otra(gancho):
    _, B, h, _ = gancho[True]
    assert comprobar([B, B]) == []
    # El primer tramo salta por encima de la cola, que lo cruzaba por arriba: los dos cuadros
    # están bien, pero entre uno y otro una cuerda atraviesa a la otra.
    D = B.copy()
    D[np.arange(len(B)) * h < 10.0, 2] += 2.5
    fallas = comprobar([B, D])
    assert fallas == ["cuadro 1: entre el cuadro 0 y este, dos tramos pasan a menos de 0.90 d"]
