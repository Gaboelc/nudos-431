"""T15c: el contacto y el roce del motor (la barrera de IPC, la CCD y el roce de Coulomb, en
nudos/fisica/contacto.py, y el paso de nudos/fisica/integrador.py), contra la física conocida."""
from __future__ import annotations

import math

import ipctk
import numpy as np
import pytest

from nudos.fisica.contacto import (DHAT, DMIN, FUERZA_MEDIA_FRANJA, MallaContacto, Solido,
                                   cilindro, rigidez_barrera)
from nudos.fisica.integrador import Sistema
from nudos.fisica.materiales import CUERDA_8MM, GRAVEDAD
from nudos.fisica.varilla import Varilla

G = GRAVEDAD / CUERDA_8MM.diametro_m    # la gravedad, en diámetros por segundo²


def recta(n, h, origen, direccion):
    d = np.asarray(direccion, float)
    return np.asarray(origen, float) + h * np.arange(n)[:, None] * d / np.linalg.norm(d)


def test_la_fuerza_de_la_barrera_a_media_franja():
    # Un nodo apoyado en una cara, a media franja: la barrera de rigidez 1 empuja
    # FUERZA_MEDIA_FRANJA, sea cual sea el largo de los tramos. Los nodos van lejos de la
    # diagonal de la mesa (x = y), que suma contactos con sus aristas.
    for h in (0.1, 0.25):
        X = recta(9, h, (0.013, -20.0, 0.5), (1, 0, 0))
        m = MallaContacto(X, altura_mesa=0.0)
        g = m.barrera(X, 1.0, 1)[1].reshape(-1, 3)
        assert -g[:, 2] == pytest.approx(np.full(9, FUERZA_MEDIA_FRANJA), rel=1e-4)
        assert np.abs(g[:, :2]).max() < 1e-9
    assert rigidez_barrera(2 * FUERZA_MEDIA_FRANJA) == pytest.approx(2.0)


def test_la_barrera_y_el_roce_dan_lo_que_dice_su_gradiente():
    # Contra diferencias finitas, en el borde de la franja y con el roce de un paso corrido.
    a = recta(11, 0.2, (-1, 0, 0), (1, 0, 0))
    b = recta(11, 0.2, (0, -1, DMIN + 0.03), (0.1, 1, 0))
    X = np.vstack([a, b])
    m = MallaContacto(X, nodos_por_cuerda=[11, 11])
    roce = m.roce_retrasado(X, 1.0)
    assert len(roce) > 0
    x = (X + [0.004, 0.002, 0.001] * np.r_[np.zeros(11), np.ones(11)][:, None]).ravel()
    for f in (lambda y, o: m.barrera(y, 1.0, o), roce.evaluar):
        g = f(x, 1)[1]
        h = 1e-7
        gfd = np.array([(f(x + h * u, 0) - f(x - h * u, 0)) / (2 * h) for u in np.eye(len(x))])
        assert np.abs(gfd - g).max() <= 1e-5 * np.abs(g).max()


# --- No atravesarse ---

@pytest.mark.parametrize("rapidez", [60.0, 600.0])
def test_dos_cuerdas_lanzadas_no_se_atraviesan(rapidez):
    # Dos cuerdas de 30 diámetros, cruzadas a 3 una de otra, lanzadas una contra otra a 0,5 y
    # a 5 m/s. A 5 m/s, en un paso cada una avanza 10 diámetros: sin la CCD, se atravesarían.
    # (Con cuerdas cortas, Newton puede llevar una por el costado de la otra dentro de un paso
    # largo, sin atravesarla: por eso las cuerdas son largas, y por eso T17 anima con subpasos.)
    n, dt = 151, 1 / 60
    a = recta(n, 0.2, (-15, 0, 0), (1, 0, 0))
    b = recta(n, 0.2, (0, -15, 3), (0, 1, 0))
    X = np.vstack([a, b])
    m = MallaContacto(X, nodos_por_cuerda=[n, n])
    s = Sistema([Varilla.desde_forma(a), Varilla.desde_forma(b)], m, kappa=rigidez_barrera(0.01))
    v = np.zeros_like(X)
    v[:n, 2], v[n:, 2] = rapidez, -rapidez
    assert rapidez * dt * 2 > 3 or rapidez < 100
    menor = math.inf
    for _ in range(20):
        p = s.paso(X, v, dt)
        assert p.convergio
        X, v = p.x, p.v
        menor = min(menor, m.distancia_minima(X))
        assert X[n + n // 2, 2] > X[n // 2, 2] + DMIN - 1e-9     # la de arriba sigue arriba
    assert DMIN - 1e-9 <= menor < DMIN + DHAT                      # se tocaron


def test_una_cuerda_lanzada_contra_un_palo_no_lo_atraviesa():
    # Una cuerda de 30 diámetros que cae a 5 m/s sobre un palo de 5 diámetros (4 cm): queda
    # arriba, con su eje a no menos de dmin de la malla del palo.
    R = 2.5
    palo = cilindro((0, 0, 0), (0, 1, 0), R - 0.5, 20.0)
    X = recta(151, 0.2, (-15, 0, R + 2.0), (1, 0, 0))
    m = MallaContacto(X, [palo])
    s = Sistema([Varilla.desde_forma(X)], m, kappa=rigidez_barrera(0.01))
    v = np.zeros_like(X)
    v[:, 2] = -600.0
    for _ in range(20):
        p = s.paso(X, v, 1 / 60)
        assert p.convergio
        X, v = p.x, p.v
        assert np.hypot(X[:, 0], X[:, 2]).min() >= R - 0.5 + DMIN - 1e-9
    assert X[75, 2] > 0                                            # sobre el palo, no debajo


def test_dar_pasos_dos_veces_da_lo_mismo():
    def correr():
        n = 21
        a = recta(n, 0.2, (-2, 0, 0), (1, 0, 0))
        b = recta(n, 0.2, (0, -2, 1.5), (0, 1, 0))
        X = np.vstack([a, b])
        m = MallaContacto(X, nodos_por_cuerda=[n, n])
        s = Sistema([Varilla.desde_forma(a), Varilla.desde_forma(b)], m, kappa=rigidez_barrera(0.01))
        v = np.zeros_like(X)
        v[n:, 2] = -100.0
        for _ in range(8):
            p = s.paso(X, v, 1 / 60)
            X, v = p.x, p.v
        return X
    assert correr().tobytes() == correr().tobytes()


# --- El cabrestante (Euler-Eytelwein) ---

def cuerda_sobre_palo(R, h, colgado):
    """La cuerda colgada a los dos lados de un palo horizontal: media vuelta por arriba."""
    r = R + 0.5
    izq = [[-r, 0, z] for z in np.arange(-colgado, 0, h)]
    arco = [[r * math.cos(t), 0, r * math.sin(t)] for t in np.linspace(math.pi, 0, int(math.pi * r / h) + 1)]
    der = [[r, 0, z] for z in np.arange(-h, -colgado - 1e-9, -h)]
    return np.array(izq + arco + der)


def corrimiento_por_paso(cociente, T=100.0, pasos=20):
    """Una cuerda sobre un palo de 4 cm, con μ = 0,45 con la madera, media vuelta (θ = π), T
    de un lado y cociente·e^(μθ)·T del otro: cuánto se corre por paso al final, en diámetros."""
    R, h, mu = 2.5, 0.25, 0.45
    X = cuerda_sobre_palo(R, h, 5.0)
    N = len(X)
    W = cociente * math.exp(mu * math.pi) * T
    F = np.zeros((N, 3))
    F[0, 2], F[-1, 2] = -W, -T
    m = MallaContacto(X, [cilindro((0, 0, 0), (0, 1, 0), R - 0.5, 10.0)], mu_solidos=mu)
    s = Sistema([Varilla.desde_forma(X)], m, fuerzas=F, kappa=rigidez_barrera(W * h / R),
                tol_fuerza=1e-6 * T, eps_roce=1e-4)
    z = []
    for _ in range(pasos):
        p = s.paso(X)
        assert p.convergio
        X = p.x
        z.append(X[0, 2])
    return (z[-6] - z[-1]) / 5


def test_el_cabrestante_aguanta_debajo_del_limite():
    # Al 95 % de e^(μθ), el roce aguanta: la cuerda se corre menos que el roce estático
    # suavizado (eps_roce = 10⁻⁴ diámetros por paso).
    assert abs(corrimiento_por_paso(0.95)) < 3e-4


def test_el_cabrestante_desliza_encima_del_limite():
    assert corrimiento_por_paso(1.05, pasos=8) > 1e-2


# --- La tabla inclinada ---

def tabla(alfa, medio=50.0):
    """Una tabla que sube en x con el ángulo alfa: la malla, la dirección cuesta arriba y la
    normal."""
    s = np.array([math.cos(alfa), 0.0, math.sin(alfa)])
    y = np.array([0.0, 1.0, 0.0])
    V = np.array([-medio * (s + y), medio * (s - y), medio * (s + y), medio * (y - s)])
    return Solido(V, np.array([[0, 1, 2], [0, 2, 3]], np.int32)), s, np.cross(s, y)


def cuesta_abajo(grados, mu=0.45, pasos=60, dt=1 / 240):
    """Un trozo de cuerda de 3 diámetros apoyado en la tabla, suelto: cuánto baja, en
    diámetros, en pasos·dt segundos."""
    alfa = math.radians(grados)
    t, s, normal = tabla(alfa)
    h = 0.25
    X = (np.arange(13) * h - 1.5)[:, None] * s + [0, 0.3, 0] + (DMIN + DHAT / 2) * normal
    m = MallaContacto(X, [t], mu_solidos=mu)
    S = Sistema([Varilla.desde_forma(X)], m, eps_roce=1e-5, tol_fuerza=1e-10,
                kappa=rigidez_barrera(CUERDA_8MM.peso_por_d * h * math.cos(alfa)))
    Y, V = X, np.zeros_like(X)
    for _ in range(pasos):
        p = S.paso(Y, V, dt)
        assert p.convergio
        Y, V = p.x, p.v
        assert m.distancia_minima(Y) >= DMIN - 1e-9
    return -float((Y - X).mean(axis=0) @ s)


def test_la_tabla_inclinada_sostiene_debajo_del_angulo_del_roce():
    # Con μ = 0,45, el ángulo del roce es atan(0,45) = 24,2°.
    assert abs(cuesta_abajo(20.0)) < 0.002
    assert abs(cuesta_abajo(23.0)) < 0.005


@pytest.mark.parametrize("grados", [28.0, 35.0])
def test_la_tabla_inclinada_desliza_encima_del_angulo_del_roce(grados):
    # Desliza con la aceleración g (sen α − μ cos α).
    alfa, t = math.radians(grados), 60 / 240
    esperado = 0.5 * G * (math.sin(alfa) - 0.45 * math.cos(alfa)) * t ** 2
    assert cuesta_abajo(grados) == pytest.approx(esperado, rel=0.03)


def test_el_roce_con_un_anfitrion_es_el_suyo():
    # El roce de un par es el promedio de sus vértices (ipctk): cada vértice de un anfitrión
    # lleva 2·μ − μ_cuerda, así que cuerda con anfitrión da μ, y cuerda con cuerda, μ_cuerda.
    X = recta(5, 0.25, (0, 0, 0.5), (1, 0, 0))
    m = MallaContacto(X, [cilindro((0, 5, 0), (1, 0, 0), 1.0, 4.0, mu=0.2)], altura_mesa=0.0)
    mezcla = ipctk.TangentialCollisions.default_blend_mu
    assert mezcla(m.mu[0], m.mu[-1]) == pytest.approx(CUERDA_8MM.mu_madera)    # la mesa
    assert mezcla(m.mu[0], m.mu[5]) == pytest.approx(0.2)                       # el palo
    assert mezcla(m.mu[0], m.mu[1]) == pytest.approx(CUERDA_8MM.mu_cuerda)
