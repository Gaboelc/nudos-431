"""Generador libre: del trazado y la secuencia de cruces a la línea central 3D.

Cada paso se construye así:
1. Una curva suave pasa por los puntos de control y se muestrea a paso fijo.
2. En cada cruce, el tramo que va por encima se eleva sobre el de abajo.
3. Se relaja: la cuerda no se estira, cae por gravedad, se apoya en la mesa y
   ningún tramo atraviesa a otro.

Unidades: el diámetro de la cuerda es 1. x a la derecha, y hacia el fondo de la
mesa (lejos de quien ata), z hacia arriba desde la mesa.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import cKDTree

from .cruces import (Cruce, emparejar, encimas, encontrar_cruces, numerada,
                     secuencia_obtenida)
from .spec import Paso

H = 0.2            # paso de muestreo a lo largo de la cuerda
R = 0.5            # radio de la cuerda
SEPARACION = 1.0   # distancia mínima entre los ejes de dos tramos que se tocan

LIMITES = {
    "separacion_min": 0.97,    # diámetros
    "curvatura_min": 0.9,      # radio de curvatura, en diámetros
    "estiramiento_max": 0.02,  # fracción del largo de cada tramo
}


class TrazadoError(ValueError):
    """El trazado de un paso no corresponde a su secuencia de cruces."""


@dataclass
class Resultado:
    n: int
    puntos: np.ndarray                      # (N, 3) línea central relajada
    h: float                                # separación entre puntos
    resaltado: tuple[float, float] | None   # tramo resaltado, a lo largo de la cuerda
    cruces: dict[str, tuple[float, float]]  # etiqueta → posición sobre la mesa
    secuencia: list[str]                    # obtenida después de relajar
    esperada: list[str]                     # declarada, numerada igual
    medidas: dict[str, float]
    fallas: list[str] = field(default_factory=list)


def construir_paso(paso: Paso) -> Resultado:
    D, ctrl = catmull_rom(paso.puntos)
    X2, h, ctrl_s = remuestrear(D, ctrl)
    cruces = encontrar_cruces(X2, h)
    declarados = len(paso.secuencia) // 2
    if len(cruces) != declarados:
        raise TrazadoError(
            f"Paso {paso.n}: el trazado tiene {len(cruces)} cruces y la secuencia "
            f"declara {declarados}.")
    if cruces and emparejar(cruces, paso.secuencia) is None:
        raise TrazadoError(
            f"Paso {paso.n}: los cruces del trazado aparecen en otro orden que en la secuencia.")
    X = elevar(X2, h, cruces, encimas(cruces, paso.secuencia))
    Xr = relajar(X, h)

    cruces_r = encontrar_cruces(Xr, h)
    obtenida = secuencia_obtenida(Xr, h, cruces_r)
    esperada = numerada(paso.secuencia)
    etiquetas = emparejar(cruces_r, paso.secuencia) if obtenida == esperada else None
    largos = np.linalg.norm(np.diff(Xr, axis=0), axis=1)
    radio, donde = curvatura_min(Xr, h, ventana=1)
    medidas = {
        "largo": float(largos.sum()),
        "separacion_min": separacion_min(Xr, h),
        "curvatura_min": radio,
        "estiramiento_max": float(np.abs(largos / h - 1).max()),
        "altura_max": float(Xr[:, 2].max()),
    }
    resaltado = None
    if paso.resaltar is not None:
        a, b = paso.resaltar
        resaltado = (float(ctrl_s[a]), float(ctrl_s[b]))
    return Resultado(
        n=paso.n,
        puntos=Xr,
        h=h,
        resaltado=resaltado,
        cruces={} if etiquetas is None else {e: c.xy for e, c in zip(etiquetas, cruces_r)},
        secuencia=obtenida,
        esperada=esperada,
        medidas=medidas,
        fallas=_fallas(paso.n, obtenida, esperada, medidas, donde),
    )


def _fallas(n, obtenida, esperada, medidas, donde) -> list[str]:
    out = []
    if obtenida != esperada:
        out.append(f"Paso {n}: después de relajar, la secuencia es «{' '.join(obtenida)}» "
                   f"y debía ser «{' '.join(esperada)}».")
    if medidas["separacion_min"] < LIMITES["separacion_min"]:
        out.append(f"Paso {n}: dos tramos quedan a {medidas['separacion_min']:.2f} diámetros; "
                   f"el mínimo es {LIMITES['separacion_min']}.")
    if medidas["curvatura_min"] < LIMITES["curvatura_min"]:
        out.append(f"Paso {n}: la cuerda se dobla con radio {medidas['curvatura_min']:.2f} "
                   f"cerca de ({donde[0]:.1f}, {donde[1]:.1f}); el mínimo es "
                   f"{LIMITES['curvatura_min']}.")
    if medidas["estiramiento_max"] > LIMITES["estiramiento_max"]:
        out.append(f"Paso {n}: la cuerda se estira {medidas['estiramiento_max']:.1%}; "
                   f"el máximo es {LIMITES['estiramiento_max']:.0%}.")
    return out


# --------------------------------------------------------------------------
# Curva
# --------------------------------------------------------------------------
def catmull_rom(P, alpha=0.5):
    """Catmull-Rom centrípeta por todos los puntos. Devuelve la polilínea densa y
    el índice denso donde cae cada punto de control."""
    P = np.asarray(P, float)
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    densa, ctrl = [], []
    cuenta = 0
    for i in range(len(Q) - 3):
        p0, p1, p2, p3 = Q[i:i + 4]
        ctrl.append(cuenta)
        d01 = max(np.linalg.norm(p1 - p0), 1e-6) ** alpha
        d12 = max(np.linalg.norm(p2 - p1), 1e-6) ** alpha
        d23 = max(np.linalg.norm(p3 - p2), 1e-6) ** alpha
        t0, t1 = 0.0, d01
        t2, t3 = t1 + d12, t1 + d12 + d23
        n = max(8, int(np.linalg.norm(p2 - p1) * 24))
        t = np.linspace(t1, t2, n, endpoint=False)[:, None]
        A1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        A2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        A3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        B1 = (t2 - t) / (t2 - t0) * A1 + (t - t0) / (t2 - t0) * A2
        B2 = (t3 - t) / (t3 - t1) * A2 + (t - t1) / (t3 - t1) * A3
        C = (t2 - t) / (t2 - t1) * B1 + (t - t1) / (t2 - t1) * B2
        densa.append(C)
        cuenta += n
    ctrl.append(cuenta)
    densa.append(Q[-2][None])
    return np.vstack(densa), ctrl


def remuestrear(D, ctrl, h=H):
    """Puntos equiespaciados a lo largo de la curva; devuelve también la posición
    a lo largo de la cuerda de cada punto de control."""
    seg = np.linalg.norm(np.diff(D, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    L = s[-1]
    n = int(round(L / h))
    hh = L / n
    sg = np.linspace(0.0, L, n + 1)
    X = np.stack([np.interp(sg, s, D[:, k]) for k in range(D.shape[1])], axis=1)
    return X, hh, s[ctrl]


# --------------------------------------------------------------------------
# Elevación y relajación
# --------------------------------------------------------------------------
def _suave(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def elevar(X2, h, cruces: list[Cruce], primera_encima: list[bool]):
    """Sube el tramo de encima de cada cruce sobre el de abajo."""
    N = len(X2)
    s = np.arange(N) * h
    z = np.full(N, R)
    for _ in range(6):
        for k, c in enumerate(cruces):
            so, su = (c.sa, c.sb) if primera_encima[k] else (c.sb, c.sa)
            zu = np.interp(su, s, z)
            alto = zu + SEPARACION - R
            w = float(np.clip(2.6 / max(c.seno, 0.25), 2.6, 5.0))
            b = _suave((1.0 - np.abs(s - so) / w) / 0.65)
            z = np.maximum(z, R + alto * b)
    return np.column_stack([X2, z])


def _colisiones(X, salto, libre, ganancia=1.0):
    arbol = cKDTree(X)
    pares = arbol.query_pairs(r=SEPARACION, output_type="ndarray")
    if len(pares):
        pares = pares[np.abs(pares[:, 0] - pares[:, 1]) > salto]
    if not len(pares):
        return 0.0
    d = X[pares[:, 1]] - X[pares[:, 0]]
    dist = np.linalg.norm(d, axis=1)
    corr = ((SEPARACION - dist) / 2.0 / np.maximum(dist, 1e-9))[:, None] * d
    acc = np.zeros_like(X)
    cnt = np.zeros(len(X))
    np.add.at(acc, pares[:, 0], -corr)
    np.add.at(acc, pares[:, 1], corr)
    np.add.at(cnt, pares[:, 0], 1)
    np.add.at(cnt, pares[:, 1], 1)
    m = (cnt > 0) & libre
    X[m] += ganancia * acc[m] / cnt[m][:, None]
    return float((SEPARACION - dist).max())


def _largos(X, h, libre, pasadas=8):
    """Gauss-Seidel rojo-negro sobre el largo de cada tramo (vectorizado)."""
    N = len(X)
    for _ in range(pasadas):
        for paridad in (0, 1):
            i = np.arange(paridad, N - 1, 2)
            seg = X[i + 1] - X[i]
            L = np.linalg.norm(seg, axis=1)
            c = ((L - h) / np.maximum(L, 1e-9))[:, None] * seg
            fa, fb = libre[i], libre[i + 1]
            wa = np.where(fa & fb, 0.5, np.where(fa, 1.0, 0.0))
            wb = np.where(fa & fb, 0.5, np.where(fb, 1.0, 0.0))
            X[i] += wa[:, None] * c
            X[i + 1] -= wb[:, None] * c


def _limitar_curva(X, h, libre, rmin=1.0, ganancia=0.5):
    """Suaviza solo donde el radio local es menor que rmin, sin mover el resto."""
    t = X[1:] - X[:-1]
    t /= np.maximum(np.linalg.norm(t, axis=1), 1e-9)[:, None]
    ang = np.arccos(np.clip((t[1:] * t[:-1]).sum(1), -1, 1))
    malos = np.nonzero(ang > h / rmin)[0] + 1
    malos = malos[libre[malos]]
    if len(malos):
        X[malos] += ganancia * (X[malos - 1] + X[malos + 1] - 2 * X[malos])
    return len(malos)


def relajar(X, h, iteraciones=1000, fijos=3):
    """Relajación por posiciones. Las anclas en xy imitan el roce con la mesa; son
    débiles para que la cuerda se deslice y dé el largo que cuesta subir sobre otro
    tramo. La gravedad asienta cada tramo de encima sobre el de abajo."""
    X = X.copy()
    ancla = X[:, :2].copy()
    N = len(X)
    salto = int(math.ceil(1.6 / h))
    libre = np.ones(N, bool)
    libre[:fijos] = False
    for it in range(iteraciones):
        tarde = it > iteraciones * 0.75
        g = 0.0 if tarde else 0.003
        ka = 0.004 if tarde else 0.012
        X[libre, 2] -= g
        lap = X[:-2] + X[2:] - 2 * X[1:-1]
        X[1:-1, 2] += 0.45 * lap[:, 2]
        X[1:-1, :2] += 0.02 * lap[:, :2]
        X[libre, :2] += ka * (ancla[libre] - X[libre, :2])
        for _ in range(2):
            _limitar_curva(X, h, libre, rmin=1.1, ganancia=0.35)
            _colisiones(X, salto, libre)
            X[:, 2] = np.maximum(X[:, 2], R)
            _largos(X, h, libre, pasadas=4)
    for _ in range(80):
        _limitar_curva(X, h, libre, rmin=1.1, ganancia=0.25)
        _colisiones(X, salto, libre)
        X[:, 2] = np.maximum(X[:, 2], R)
        _largos(X, h, libre, pasadas=4)
    return X


# --------------------------------------------------------------------------
# Medidas
# --------------------------------------------------------------------------
def separacion_min(X, h) -> float:
    """Distancia mínima entre ejes de tramos que no son vecinos en la cuerda."""
    salto = int(math.ceil(1.6 / h))
    arbol = cKDTree(X)
    pares = arbol.query_pairs(r=SEPARACION * 1.05, output_type="ndarray")
    if len(pares):
        pares = pares[np.abs(pares[:, 0] - pares[:, 1]) > salto]
    if not len(pares):
        return SEPARACION * 1.05
    return float(np.linalg.norm(X[pares[:, 1]] - X[pares[:, 0]], axis=1).min())


def curvatura_min(X, h, ventana=3) -> tuple[float, np.ndarray]:
    """Radio de curvatura mínimo, medido sobre `ventana` tramos a cada lado, y
    dónde ocurre."""
    t = np.diff(X, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    a, b = t[:-2 * ventana], t[2 * ventana:]
    ang = np.arccos(np.clip((a * b).sum(1), -1, 1))
    k = ang / (2 * ventana * h)
    i = int(k.argmax())
    return float(1.0 / max(k[i], 1e-9)), X[i + ventana + 1]
