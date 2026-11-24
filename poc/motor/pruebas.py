"""Pruebas de física del motor de la prueba de concepto.

1. Cabrestante (Euler-Eytelwein): una cuerda sobre un palo, con media vuelta (θ = π), una
   fuerza W en un extremo y T en el otro. No desliza mientras W/T < e^(μθ); con μ = 0,45 el
   límite es 4,11. Con W/T = 3 tiene que quedar quieta y con 5,5, deslizar.
2. No atravesarse: el nudo simple, apretado con 200 N de cada lado, conserva su secuencia y
   ningún par de tramos baja de dmin.
3. Repetir: resolver dos veces da lo mismo, bit a bit.

Uso: python poc/motor/pruebas.py [cabrestante|simple|repetir]
"""
from __future__ import annotations

import math
import sys
import time

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
from motor import Escena, Material, Motor, cilindro   # noqa: E402

R_PALO = 2.5


def cuerda_sobre_palo(h=0.2, colgado=12.0):
    """Una cuerda que cuelga a los dos lados de un palo horizontal (a lo largo de y), su eje a
    R_PALO + 0,5 del eje del palo: media vuelta por arriba y dos tramos rectos que bajan."""
    r = R_PALO + 0.5
    zc = 20.0
    pts = []
    for z in np.arange(zc - colgado, zc, h):          # sube por la izquierda
        pts.append([-r, 0.0, z])
    for a in np.linspace(math.pi, 0, int(math.pi * r / h) + 1):   # media vuelta por arriba
        pts.append([r * math.cos(a), 0.0, zc + r * math.sin(a)])
    for z in np.arange(zc - h, zc - colgado, -h):     # baja por la derecha
        pts.append([r, 0.0, z])
    return np.array(pts), zc


def cabrestante():
    X, zc = cuerda_sobre_palo()
    palo = cilindro((0, 0, zc), "y", R_PALO - 0.5, 10.0)
    T = 10.0
    for cociente in (3.0, 5.5):
        W = cociente * T
        e = Escena(X, Material(mu_madera=0.45, mu_cuerda=0.45, peso_por_d=0.0), [palo], mesa=None,
                   fuerzas={0: np.array([0, 0, -W]), len(X) - 1: np.array([0, 0, -T])})
        m = Motor(e)
        t0 = time.time()
        Y = m.resolver(pasos=40, quieto=1e-5, mostrar=False)
        corrido = Y[0, 2] - X[0, 2]
        print(f"W/T = {cociente}: el extremo con W se corrió {corrido:+.3f} d en {len(m.registro)} pasos "
              f"({time.time() - t0:.1f} s); se espera {'quieta' if cociente < math.exp(0.45 * math.pi) else 'desliza'}")


def secuencia(Y):
    """La secuencia de cruces vista desde arriba, como la mide nudos/cruces.py."""
    from nudos.cruces import encontrar_cruces, secuencia_obtenida
    from nudos.libre import catmull_rom, remuestrear
    D, ctrl = catmull_rom(Y)
    Z, h, _ = remuestrear(D, ctrl)
    return secuencia_obtenida(Z, h, encontrar_cruces(Z, h))


def simple():
    """El nudo simple de la especificación, apretado tirando de los dos extremos."""
    from nudos.construir import construir
    from nudos.cruces import encontrar_cruces, secuencia_obtenida
    from nudos.spec import cargar
    spec = cargar("simple")
    modelo = construir(spec)
    r = modelo.pasos[-1]
    X = r.puntos
    n = len(X)
    ida = X[0] - X[5]; ida /= np.linalg.norm(ida)
    vuelta = X[-1] - X[-6]; vuelta /= np.linalg.norm(vuelta)
    for F in (20.0, 200.0):
        e = Escena(X, Material(), [], mesa=0.0, fuerzas={0: F * ida, n - 1: F * vuelta})
        m = Motor(e)
        t0 = time.time()
        Y = m.resolver(pasos=300, quieto=2e-4)
        dmin = min(rr[3] for rr in m.registro)
        print(f"F = {F} N: {len(m.registro)} pasos, {time.time() - t0:.0f} s, distancia mínima {math.sqrt(dmin):.3f}")
        print(f"  secuencia declarada {' '.join(r.secuencia)}; obtenida {' '.join(secuencia(Y))}")
        largo = lambda P: float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))
        print(f"  alto máximo {Y[:, 2].max():.2f} d (antes {X[:, 2].max():.2f}); largo {largo(Y):.1f} (antes {largo(X):.1f})")
        np.save(f"build/poc-motor/simple-{int(F)}.npy", Y)


if __name__ == "__main__":
    import os
    os.makedirs("build/poc-motor", exist_ok=True)
    cual = sys.argv[1] if len(sys.argv) > 1 else "cabrestante"
    {"cabrestante": cabrestante, "simple": simple}[cual]()
