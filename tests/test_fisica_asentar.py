"""T15d: asentar y apretar con el motor (nudos/fisica/asentar.py y nudos/fisica/manos.py)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from nudos.fisica.asentar import (FACTOR_AHORCADO, TENSIONES, apretar, asentar, contacto, material_de,
                                  separar, tensiones_de_amarre)
from nudos.fisica.contacto import ContactoCompuesto, MallaContacto
from nudos.fisica.manos import Manos, para_apretar, sostener
from nudos.fisica.materiales import CUERDA_8MM
from nudos.libre import Reparto


def cuerda_recta(desde, hasta, h=0.2):
    desde, hasta = np.asarray(desde, float), np.asarray(hasta, float)
    n = int(round(np.linalg.norm(hasta - desde) / h))
    return desde + np.linspace(0, 1, n + 1)[:, None] * (hasta - desde)


def test_el_material_de_una_cuerda_mas_gruesa():
    m = material_de(1.5)
    assert m.EA == pytest.approx(CUERDA_8MM.EA * 2.25)
    assert m.EI == pytest.approx(CUERDA_8MM.EI * 1.5 ** 4)
    assert m.peso_por_d == pytest.approx(CUERDA_8MM.peso_por_d * 2.25)
    assert material_de(1.0) is CUERDA_8MM


def test_dos_grosores_chocan_a_la_suma_de_sus_radios():
    """Una cuerda de 1,5 y una de 1 cruzadas: el contacto compuesto pone la barrera entre sus
    ejes a 1,25 (la suma de los radios) y cada una apoyada en la mesa a su radio."""
    a = cuerda_recta((-6, 0, 0.75), (6, 0, 0.75))
    b = cuerda_recta((0, -6, 0.5), (0, 6, 0.5))
    X = np.vstack([a, b])
    cortes = np.array([0, len(a), len(a) + len(b)])
    c = contacto(X, cortes, [1.5, 1.0])
    assert isinstance(c, ContactoCompuesto)
    assert len(c.partes) == 3            # la gruesa, la delgada y las dos juntas
    # Separadas (la gruesa a 2,0 sobre la delgada), ninguna barrera de una contra la otra.
    Y = X.copy()
    Y[:len(a), 2] = 0.5 + 2.0
    E_lejos = c.barrera(Y, 1.0, 0)
    # A 1,2 (menos que 1,25 · 0,95 = 1,19 no se puede, pero dentro de la franja sí hay barrera).
    Y[:len(a), 2] = 0.5 + 1.25
    assert c.barrera(Y, 1.0, 0) > E_lejos
    # El paso que las lleva a 1,1 se recorta antes de 0,95 · 1,25.
    Z = Y.copy()
    Z[:len(a), 2] = 0.5 + 1.1
    t = c.paso_libre(Y, Z)
    assert 0 < t < 1
    altura = 0.5 + 1.25 + t * (1.1 - 1.25)
    assert altura - 0.5 >= 0.95 * 1.25 - 1e-6


def test_el_contacto_compuesto_da_lo_que_dice_su_gradiente():
    a = cuerda_recta((-3, 0, 0.75), (3, 0, 0.75), h=0.5)
    b = cuerda_recta((0, -3, 0.5), (0, 3, 0.5), h=0.5)
    X = np.vstack([a, b])
    X[:len(a), 2] = 0.5 + 1.27
    c = contacto(X, np.array([0, len(a), len(a) + len(b)]), [1.5, 1.0])
    x = X.ravel()
    E, g, H = c.barrera(x, 1.0)
    h = 1e-7
    for i in np.flatnonzero(np.abs(g) > 1e-9)[:6]:
        u = np.zeros_like(x)
        u[i] = h
        assert (c.barrera(x + u, 1.0, 0) - c.barrera(x - u, 1.0, 0)) / (2 * h) == pytest.approx(g[i], rel=1e-4)
    assert H.shape == (x.size, x.size)


def test_con_un_grosor_el_contacto_es_una_malla():
    X = cuerda_recta((-3, 0, 0.5), (3, 0, 0.5))
    assert isinstance(contacto(X, np.array([0, len(X)]), [1.0]), MallaContacto)


def test_sostener_el_firme_y_el_chicote():
    m = sostener(np.array([0, 10, 25]), 25)
    assert m.fijos.tolist() == [0, 1, 2, 7, 8, 9, 10, 11, 12, 22, 23, 24]
    assert not m.fuerzas.any()


def test_para_apretar_sostiene_la_gaza_y_tira_del_firme():
    """Una cuerda que baja al nudo, sale a una gaza que vuelve al nudo y sale como chicote: se
    sostienen la gaza y el chicote y se tira del firme, hacia donde viene, y del chicote, más
    suave. Lo que está cerca del cruce no se sostiene."""
    firme = cuerda_recta((0, 20, 0.5), (0, 0.2, 0.5))
    izquierda = cuerda_recta((0, 0, 0.5), (-3, -15, 0.5))[1:]
    derecha = cuerda_recta((-3, -15, 0.5), (1, 0, 0.5))[1:]
    chicote = cuerda_recta((1, 0, 0.5), (1, -3, 0.5))[1:]
    X = np.vstack([firme, izquierda, derecha, chicote])
    m = para_apretar(X, np.array([0, len(X)]), [(0.0, 0.0)], 60.0)
    assert np.allclose(m.fuerzas[0], [0, 60.0, 0])        # el firme, hacia donde viene
    assert np.allclose(m.fuerzas[-1], [0, -20.0, 0])      # el chicote, con un tercio
    assert np.count_nonzero(np.linalg.norm(m.fuerzas, axis=1)) == 2
    gaza = np.arange(len(firme), len(firme) + len(izquierda) + len(derecha))
    lejos = gaza[np.linalg.norm(X[gaza, :2], axis=1) > 6.0]
    assert set(lejos) <= set(m.fijos.tolist())             # la gaza, sostenida
    cerca = np.flatnonzero(np.linalg.norm(X[:, :2], axis=1) <= 6.0)
    assert not set(cerca) & set(m.fijos.tolist())          # el nudo, libre
    assert 0 not in m.fijos                                 # el firme no se sostiene


def test_para_apretar_sin_lazos_sostiene_el_firme_y_tira_del_chicote():
    """Sin lazos (como el nudo simple o el ballestrinque), el firme queda sostenido en su punta
    y donde entra al nudo, y se tira del chicote: el nudo no viaja mientras se aprieta."""
    firme = cuerda_recta((0, 20, 0.5), (0, 0.2, 0.5))
    chicote = cuerda_recta((0, 0, 0.5), (10, 0, 0.5))[1:]
    X = np.vstack([firme, chicote])
    m = para_apretar(X, np.array([0, len(X)]), [(0.0, 0.0)], 60.0)
    entra = int(np.argmax(np.linalg.norm(X[:, :2], axis=1) <= 6.0))
    assert m.fijos.tolist() == [0, 1, 2, entra - 3, entra - 2, entra - 1]
    assert np.allclose(m.fuerzas[-1], [60.0, 0, 0])
    assert np.count_nonzero(np.linalg.norm(m.fuerzas, axis=1)) == 1


def test_las_tensiones_de_un_amarre():
    hitos = {"inicio": 2.0, "vuelta-1": 4.0, "vuelta-3": 8.0, "ahorcado-1": 9.0, "ahorcado-3": 12.0}
    T = tensiones_de_amarre(100, hitos, 0.2, 14.0, "apretada")
    s = np.arange(100) * 0.2
    assert np.all(T[s < 8.0] == TENSIONES["apretada"])
    assert np.all(T[(s >= 8.0) & (s < 12.0)] == TENSIONES["apretada"] * FACTOR_AHORCADO)
    assert np.all(T[(s >= 12.0) & (s < 14.0)] == TENSIONES["apretada"])
    assert np.all(T[s >= 14.0] == 0.0)


def test_separar_deja_cada_par_a_su_distancia():
    """Dos tramos que se atraviesan en el trazado quedan separados, sin atravesar la mesa."""
    a = cuerda_recta((-5, 0, 0.5), (5, 0, 0.5))
    b = cuerda_recta((0, -5, 0.5), (0, 5, 0.5))
    b[:, 2] = 0.5 + 0.6 * np.exp(-(b[:, 1] / 2) ** 2)    # sube, pero no lo bastante
    X = np.vstack([a, b])
    rep = Reparto(np.r_[np.zeros(len(a), int), np.ones(len(b), int)], np.ones(len(X)))
    Y = separar(X, 0.2, rep)
    c = contacto(Y, np.array([0, len(a), len(X)]), [1.0, 1.0])
    assert c.distancia_minima(Y) > 0.95
    assert Y[:, 2].min() >= 0.5 - 1e-12


def test_asentar_un_tramo_que_cruza_otro_lo_apoya():
    """Un tramo trazado alto sobre otro, sin memoria y con sus puntas sostenidas, baja hasta
    tocarlo; los dos quedan sobre la mesa y la cuerda deja de moverse."""
    a = cuerda_recta((-8, 0, 0.5), (8, 0, 0.5))
    b = cuerda_recta((0, -8, 0.5), (0, 8, 0.5))
    b[:, 2] = 0.5 + 1.6 * np.exp(-(b[:, 1] / 3) ** 2)
    X = np.vstack([a, b])
    cortes = np.array([0, len(a), len(X)])
    m = sostener(cortes, len(X))
    r = asentar(X, cortes, [1.0, 1.0], m, memoria=False, largos=np.full(len(X), 0.2))
    assert r.quieto
    medio = len(a) + len(b) // 2
    debajo = len(a) // 2
    # Tocándolo: dentro de la franja de la barrera, sin bajar de dmin.
    assert 0.95 - 1e-9 <= r.X[medio, 2] - r.X[debajo, 2] < 1.05
    assert r.X[medio, 2] < X[medio, 2] - 0.5
    assert np.abs(r.X[:len(a), 2] - 0.5).max() < 0.1


def test_apretar_dos_veces_da_lo_mismo():
    a = cuerda_recta((-8, 0, 0.5), (8, 0, 0.5))
    b = cuerda_recta((0, -8, 0.5), (0, 8, 0.5))
    b[:, 2] = 0.5 + 1.2 * np.exp(-(b[:, 1] / 3) ** 2)
    X = np.vstack([a, b])
    rep = Reparto(np.r_[np.zeros(len(a), int), np.ones(len(b), int)], np.ones(len(X)))
    r1 = apretar(X, rep, None, [(0.0, 0.0)], 20.0)
    r2 = apretar(X, rep, None, [(0.0, 0.0)], 20.0)
    assert np.array_equal(r1.X, r2.X)


# --- El nudo simple apretado, contra los nudos ideales (Pieranski y otros) ---

# Pieranski, Przybyl y Stasiak, «Tight open knots» (Eur. Phys. J. E 6, 123, 2001): con una
# cuerda ideal (perfectamente flexible, de diámetro D, sin roce), el nudo simple más apretado
# gasta Λ = (L − L')/D = 10,1, donde L es el largo de la cuerda y L' la distancia entre sus
# puntas tiradas hacia afuera. Con cuerda de verdad se midió 10,35 (Diao y otros), por el roce.
LAMBDA_IDEAL = 10.1


def test_el_nudo_simple_apretado_gasta_lo_que_dice_pieranski(monkeypatch):
    """El último paso del nudo simple, asentado con el motor, con el firme sostenido en su
    punta y el chicote tirado con 60 N hacia el otro lado, sin roce. Una cuerda con rigidez no
    llega al ideal, pero el motor no puede pasarlo: solo la deja comprimirse hasta dmin (0,95)."""
    from nudos.libre import construir_paso
    from nudos.spec import cargar
    monkeypatch.setenv("NUDOS_MOTOR", "1")
    spec = cargar("simple")
    r = construir_paso(spec.pasos[-1], None, ())
    X = r.puntos
    N = len(X)
    d = X[-1] - X[0]
    d[2] = 0
    fuerzas = np.zeros((N, 3))
    fuerzas[-1] = 60.0 * d / np.linalg.norm(d)
    a = asentar(X, np.array([0, N]), [1.0], Manos(np.arange(3), fuerzas, None),
                memoria=False, roce=False, max_pasos=60)
    L = float(np.sum(np.linalg.norm(np.diff(a.X, axis=0), axis=1)))
    Lp = float(np.linalg.norm(a.X[-1] - a.X[0]))
    lam = L - Lp
    print(f"Λ = {lam:.2f} (ideal {LAMBDA_IDEAL}, cuerda real 10,35)")
    assert 0.95 * LAMBDA_IDEAL <= lam <= 1.1 * LAMBDA_IDEAL
