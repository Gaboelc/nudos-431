"""T15b: la varilla elástica discreta (nudos/fisica/varilla.py) y el Newton mínimo
(nudos/fisica/integrador.py), contra diferencias finitas y contra la física conocida."""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.integrate import solve_bvp
from scipy.optimize import brentq

from nudos.fisica.integrador import newton
from nudos.fisica.materiales import CUERDA_8MM, Material
from nudos.fisica.varilla import Varilla, marco_paralelo


def curva_al_azar(n=8, semilla=1):
    """Una cuerda torcida en 3D, con tramos de largos distintos y ángulos de hasta unos 90°."""
    rng = np.random.default_rng(semilla)
    return np.cumsum(rng.normal(size=(n, 3)) * 0.3 + [0.25, 0.0, 0.0], axis=0)


def hessiano_completo(v, parte, x):
    B = getattr(v, parte)(x)[2]
    vacio6, vacio9 = np.zeros((v.N - 1, 6, 6)), np.zeros((max(v.N - 2, 0), 9, 9))
    if parte == "estiramiento":
        return v.hessiano_de_bloques(B, vacio9).toarray()
    return v.hessiano_de_bloques(vacio6, B).toarray()


@pytest.mark.parametrize("semilla", [1, 2, 3])
@pytest.mark.parametrize("parte", ["estiramiento", "flexion", "peso"])
def test_gradiente_y_hessiano_contra_diferencias_finitas(parte, semilla):
    X = curva_al_azar(semilla=semilla)
    rng = np.random.default_rng(semilla + 10)
    # Largos de reposo distintos de los de la forma: unos tramos estirados y otros comprimidos.
    v = Varilla(np.linalg.norm(np.diff(X, axis=0), axis=1) * rng.uniform(0.9, 1.1, len(X) - 1))
    f = getattr(v, parte)
    x = X.ravel()
    E, g, _ = f(x)
    h, n = 1e-6, len(x)
    gfd = np.array([(f(x + h * u, 0)[0] - f(x - h * u, 0)[0]) / (2 * h) for u in np.eye(n)])
    assert np.abs(gfd - g.ravel()).max() <= 1e-7 * max(np.abs(g).max(), 1e-3)
    if parte == "peso":
        return
    H = hessiano_completo(v, parte, x)
    Hfd = np.array([(f(x + h * u, 1)[1].ravel() - f(x - h * u, 1)[1].ravel()) / (2 * h) for u in np.eye(n)])
    assert np.abs(Hfd - H).max() <= 1e-6 * np.abs(H).max()
    assert np.array_equal(H, H.T)


def test_el_hessiano_proyectado_es_semidefinido():
    X = curva_al_azar(n=12)
    v = Varilla(np.linalg.norm(np.diff(X, axis=0), axis=1) * 1.05)   # todo comprimido
    _, _, H = v.evaluar(X.ravel(), 2, proyectar=True)
    H = H.toarray()
    assert np.allclose(H, H.T, atol=1e-12)
    assert np.linalg.eigvalsh(H).min() > -1e-9 * np.abs(H).max()
    _, _, H0 = v.evaluar(X.ravel(), 2, proyectar=False)
    assert np.linalg.eigvalsh(H0.toarray()).min() < 0   # sin proyectar, no lo es


def test_la_flexion_es_la_de_la_viga():
    # Un arco de radio R: la energía es EI/2 · (1/R)² por largo, la de la teoría de vigas.
    R, n = 3.0, 200
    t = np.linspace(0, math.pi, n + 1)
    X = np.column_stack([R * np.cos(t), R * np.sin(t), np.zeros(n + 1)])
    v = Varilla.desde_forma(X, gravedad=False)
    E = v.flexion(X.ravel(), 0)[0]
    largo_interior = v.l.sum() - (v.l[0] + v.l[-1]) / 2
    assert E == pytest.approx(CUERDA_8MM.EI / 2 / R ** 2 * largo_interior, rel=1e-3)


def test_doblarse_sobre_si_misma_no_tiene_fin():
    X = np.array([[0.0, 0, 0], [1, 0, 0], [0, 1e-9, 0]])
    v = Varilla([1.0, 1.0])
    assert v.flexion(X.ravel(), 0)[0] > 1e15
    X[2] = [0, 0, 0]
    assert v.energia(X.ravel()) == math.inf


def test_la_tension_de_atado():
    # Una cuerda recta con los largos de reposo acortados T/EA tira de los extremos con T.
    X = np.column_stack([np.linspace(0, 10, 51), np.zeros(51), np.zeros(51)])
    v = Varilla.desde_forma(X, tension=60.0, gravedad=False)
    g = v.evaluar(X.ravel(), 1)[1].reshape(-1, 3)
    assert g[0, 0] == pytest.approx(-60.0, rel=1e-9)    # el extremo lo tira hacia adentro
    assert g[-1, 0] == pytest.approx(60.0, rel=1e-9)
    assert np.abs(g[1:-1]).max() < 1e-9


def test_el_peso_es_el_de_la_cuerda():
    X = np.column_stack([np.linspace(0, 125, 501), np.zeros(501), np.zeros(501)])   # 1 m
    g = Varilla.desde_forma(X).peso(X.ravel())[1]
    assert g[:, 2].sum() == pytest.approx(0.045 * 9.81, rel=1e-9)     # 45 g/m


def test_calcular_dos_veces_da_lo_mismo():
    X = curva_al_azar(n=30)
    v = Varilla.desde_forma(X * 1.01)
    a = v.evaluar(X.ravel(), 2, proyectar=True)
    b = v.evaluar(X.ravel(), 2, proyectar=True)
    assert a[0] == b[0] and a[1].tobytes() == b[1].tobytes()
    for campo in ("data", "indices", "indptr"):
        assert getattr(a[2], campo).tobytes() == getattr(b[2], campo).tobytes()


# --- La catenaria ---

def colgar(S, L, n):
    """La cuerda de largo L colgada de dos puntos a la misma altura y a S uno del otro."""
    xs = np.linspace(-S / 2, S / 2, n + 1)
    X0 = np.column_stack([xs, np.zeros(n + 1), -0.5 * (L - S) * (1 - (2 * xs / S) ** 2)])
    v = Varilla(np.full(n, L / n))
    return newton(v.evaluar, X0, fijos=[0, n])


def test_la_catenaria():
    # 4,8 m de cuerda colgada entre dos puntos a 3,2 m: la forma es a·cosh(x/a). La cuerda
    # tiene su rigidez a la flexión, que solo se nota cerca de los extremos.
    S, L, n = 400.0, 600.0, 300
    r = colgar(S, L, n)
    assert r.convergio
    a = brentq(lambda a: 2 * a * math.sinh(S / (2 * a)) - L, 1.0, 1e5)
    flecha = a * (math.cosh(S / (2 * a)) - 1)
    X = r.x
    z = a * (np.cosh(X[:, 0] / a) - math.cosh(S / (2 * a)))
    assert np.abs(X[:, 2] - z).max() < 1e-3 * flecha
    assert -X[n // 2, 2] == pytest.approx(flecha, rel=1e-3)


def test_resolver_dos_veces_da_lo_mismo():
    a, b = colgar(100.0, 150.0, 75), colgar(100.0, 150.0, 75)
    assert a.iteraciones == b.iteraciones and a.x.tobytes() == b.x.tobytes()


# --- La elástica: un voladizo que cae con su propio peso ---

def voladizo(largo, h, material=CUERDA_8MM):
    """La cuerda horizontal, empotrada en x = 0 y suelta del otro lado. Los nodos 0 y 1 fijos
    hacen el empotramiento; la flexión del nodo 1 abarca medio tramo hacia atrás, así que el
    largo que se dobla es `largo` + h/2."""
    n = int(round(largo / h))
    X0 = np.column_stack([h * np.arange(-1, n + 1), np.zeros(n + 2), np.zeros(n + 2)])
    r = newton(Varilla(np.full(n + 1, h), material).evaluar, X0, fijos=[0, 1])
    assert r.convergio
    return -r.x[-1, 2]


def caida_elastica(largo, material=CUERDA_8MM):
    """La caída de la punta según la elástica con peso propio, sin linealizar:
    EI θ'' = −w (L − s) cos θ, θ(0) = 0, θ'(L) = 0."""
    w, EI = material.peso_por_d, material.EI

    def f(s, y):
        return np.vstack([y[1], -w * np.cos(y[0]) * (largo - s) / EI])

    s = np.linspace(0, largo, 200)
    sol = solve_bvp(f, lambda ya, yb: np.array([ya[0], yb[1]]), s, np.zeros((2, s.size)), tol=1e-10)
    assert sol.success
    ss = np.linspace(0, largo, 20001)
    return float(np.trapezoid(np.sin(sol.sol(ss)[0]), ss))


def test_la_elastica_chica_es_la_formula_de_la_viga():
    # 8 cm de cuerda: cae poco, y la caída es la de la viga, w L⁴ / (8 EI).
    h = 0.1
    L = 10.0 + h / 2
    formula = CUERDA_8MM.peso_por_d * L ** 4 / (8 * CUERDA_8MM.EI)
    assert voladizo(10.0, h) == pytest.approx(formula, rel=5e-3)


def test_la_elastica_grande():
    # 20 cm de cuerda, la medida de T15e: cae más de un 20 % de su largo y la fórmula lineal
    # ya no sirve, pero la elástica sí.
    h = 0.1
    caida = voladizo(25.0, h)
    assert caida == pytest.approx(caida_elastica(25.0 + h / 2), rel=5e-3)
    assert caida < 0.98 * CUERDA_8MM.peso_por_d * 25 ** 4 / (8 * CUERDA_8MM.EI)


def test_una_cuerda_mas_rigida_cae_menos():
    tiesa = Material(**{**CUERDA_8MM.__dict__, "EI": 4 * CUERDA_8MM.EI})
    assert voladizo(10.0, 0.2, tiesa) == pytest.approx(voladizo(10.0, 0.2) / 4, rel=0.02)


# --- El marco material ---

def test_el_marco_paralelo_no_gira_en_un_plano():
    t = np.linspace(0, 3, 60)
    X = np.column_stack([t, np.sin(2 * t), np.zeros_like(t)])
    T, D1, D2 = marco_paralelo(X)
    assert np.allclose(D1, [0, 0, 1], atol=1e-12)
    assert np.allclose(np.einsum("ij,ij->i", T, D1), 0, atol=1e-12)
    assert np.allclose(np.einsum("ij,ij->i", T, D2), 0, atol=1e-12)


def test_el_marco_paralelo_en_una_helice():
    # Respecto de la normal de la hélice, el marco sin torsión gira −τ·s: en una vuelta,
    # 2π c / √(R² + c²).
    R, c = 2.0, 0.5
    t = np.linspace(0, 2 * math.pi, 2001)
    X = np.column_stack([R * np.cos(t), R * np.sin(t), c * t])
    T, D1, _ = marco_paralelo(X, d1_inicial=[-1, 0, 0])

    def angulo(k):
        tm = (t[k] + t[k + 1]) / 2
        N = np.array([-math.cos(tm), -math.sin(tm), 0.0])
        return math.atan2(D1[k] @ np.cross(T[k], N), D1[k] @ N)

    assert angulo(len(T) - 1) - angulo(0) == pytest.approx(-2 * math.pi * c / math.hypot(R, c), rel=2e-3)


# --- La memoria (T15d) ---

@pytest.mark.parametrize("semilla", [1, 2])
def test_la_memoria_contra_diferencias_finitas(semilla):
    X = curva_al_azar(semilla=semilla)
    rng = np.random.default_rng(semilla + 20)
    K = Varilla.curvatura_de(X) + rng.normal(size=(len(X) - 2, 3)) * 0.3
    v = Varilla(np.linalg.norm(np.diff(X, axis=0), axis=1), curvatura=K)
    x = X.ravel() + rng.normal(size=X.size) * 0.05
    E, g, _ = v.memoria(x)
    h, n = 1e-6, len(x)
    gfd = np.array([(v.memoria(x + h * u, 0)[0] - v.memoria(x - h * u, 0)[0]) / (2 * h) for u in np.eye(n)])
    assert np.abs(gfd - g.ravel()).max() <= 1e-7 * np.abs(g).max()
    H = v.hessiano_de_bloques(np.zeros((v.N - 1, 6, 6)), v.memoria(x)[2]).toarray()
    Hfd = np.array([(v.memoria(x + h * u, 1)[1].ravel() - v.memoria(x - h * u, 1)[1].ravel()) / (2 * h)
                    for u in np.eye(n)])
    assert np.abs(Hfd - H).max() <= 1e-6 * np.abs(H).max()
    # Con la flexión, es EI·|κb − κb₀|²/(l₀ + l₁).
    kb = Varilla.curvatura_de(x.reshape(-1, 3))
    esperada = float(np.sum(v.k_doblar * np.sum((kb - K) ** 2, axis=1)))
    assert v.flexion(x, 0)[0] + E == pytest.approx(esperada, rel=1e-12)


def test_con_memoria_la_cuerda_guarda_su_forma():
    """Una curva en S sobre la mesa, sin peso, con sus puntas sostenidas: sin memoria cambia
    de forma (un arco de círculo no, porque ya es un equilibrio); con memoria, se queda como
    estaba."""
    t = np.linspace(0, 20, 41)
    X = np.column_stack([t, 3 * np.sin(t / 3), np.zeros_like(t)])
    l = np.linalg.norm(np.diff(X, axis=0), axis=1)
    fijos = [0, 1, 39, 40]
    for memoria in (True, False):
        v = Varilla(l, gravedad=False, curvatura=Varilla.curvatura_de(X) if memoria else None)
        r = newton(v.evaluar, X, fijos=fijos)
        assert r.convergio
        if memoria:
            assert np.abs(r.x - X).max() < 1e-9
        else:
            assert np.abs(r.x - X).max() > 0.1
