"""Nudos sobre un anfitrión rígido. Por ahora, el poste: un cilindro horizontal.

Cada paso se construye como en el generador libre (nudos/libre.py), con tres diferencias:
1. Los puntos sobre el poste se dan como [x, ángulo] y se densifican sobre su superficie
   antes de pasar la curva suave, para que la cuerda no corte por dentro del poste.
2. Los cruces se buscan en dos mapas. Los tramos que van sobre el poste se comparan en su
   superficie desenrollada (x a lo largo del eje y el arco alrededor), donde encima es lo
   que queda más lejos del eje. Los tramos sobre la mesa, en la proyección de siempre,
   donde encima es lo más alto. Un cruce entre un tramo del poste y uno de la mesa no se
   busca: ahí la comprobación es solo de separación.
3. En cada cruce, el tramo de encima se separa del de abajo hacia afuera del eje (sobre el
   poste) o hacia arriba (sobre la mesa), y en la relajación la cuerda no puede entrar al poste.
"""
from __future__ import annotations

import math

import numpy as np

from .cruces import Cruce, cruces_2d, emparejar, encimas
from .libre import R, Resultado, TrazadoError, _resultado, catmull_rom, elevar, relajar, remuestrear
from .spec import Anfitrion, Paso

ARCO_DENSO = 0.6       # cada cuánto se toma un punto sobre la superficie del poste, en diámetros
PENETRACION_MAX = 0.05  # cuánto puede entrar el eje de la cuerda en el poste, en diámetros
DISTANCIA_SIN_GRAVEDAD = 2.5  # hasta esta distancia de la superficie, la cuerda no cae
PASADAS_LARGO = 16    # correcciones de largo por vuelta de la relajación (en la mesa son 4)


class Poste:
    """Cilindro horizontal a lo largo de x, con el eje en y = 0 y a la altura radio + 1:
    se apoya sobre la cuerda que pasa por debajo."""

    def __init__(self, a: Anfitrion):
        self.radio = a.radio
        self.desde, self.hasta = a.desde, a.hasta
        self.zc = a.radio + 2 * R    # altura del eje
        self.rb = a.radio + R        # distancia al eje del eje de una cuerda que toca el poste

    def punto(self, x, grados, r=None) -> np.ndarray:
        """De [x, ángulo] sobre el poste a [x, y, z]. 0° arriba, 90° hacia quien ata."""
        th = np.radians(grados)
        r = self.rb if r is None else r
        return np.stack([np.asarray(x, float) + 0 * th, -r * np.sin(th), self.zc + r * np.cos(th)], axis=-1)

    def cilindricas(self, X) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """x, ángulo en radianes (entre -π y π) y distancia al eje."""
        dy, dz = X[:, 1], X[:, 2] - self.zc
        return X[:, 0], np.arctan2(-dy, dz), np.hypot(dy, dz)

    def empujar(self, X, libre) -> None:
        """Saca del poste los puntos que entraron, en dirección radial."""
        dy, dz = X[:, 1], X[:, 2] - self.zc
        d = np.hypot(dy, dz)
        m = libre & (d < self.rb) & (X[:, 0] > self.desde) & (X[:, 0] < self.hasta)
        if m.any():
            k = self.rb / np.maximum(d[m], 1e-9)
            X[m, 1] = dy[m] * k
            X[m, 2] = self.zc + dz[m] * k

    def penetracion(self, X) -> float:
        """Cuánto entra la cuerda en el poste (0 si no entra)."""
        x, _, r = self.cilindricas(X)
        m = (x > self.desde) & (x < self.hasta)
        return float(max(0.0, (self.rb - r[m]).max())) if m.any() else 0.0

    def datos(self) -> dict:
        """Lo que necesita render/escena.js para dibujarlo."""
        return {"tipo": "poste", "radio": self.radio, "desde": self.desde,
                "hasta": self.hasta, "y": 0.0, "z": self.zc}


def construir_paso(paso: Paso, anfitrion: Anfitrion) -> Resultado:
    poste = Poste(anfitrion)
    X, h, ctrl_s, sobre = _curva(paso, poste)
    cruces, _ = _cruces(X, h, sobre, poste)
    declarados = len(paso.secuencia) // 2
    if len(cruces) != declarados:
        raise TrazadoError(
            f"Paso {paso.n}: el trazado tiene {len(cruces)} cruces y la secuencia "
            f"declara {declarados}.")
    if cruces and emparejar(cruces, paso.secuencia) is None:
        raise TrazadoError(
            f"Paso {paso.n}: los cruces del trazado aparecen en otro orden que en la secuencia.")
    # Cuánto sube cada punto: lo mismo que en el generador libre, pero sobre el poste
    # se aplica hacia afuera del eje.
    extra = elevar(np.zeros((len(X), 2)), h, cruces, encimas(cruces, paso.secuencia))[:, 2] - R
    X = X.copy()
    x, th, r = poste.cilindricas(X)
    X[sobre] = poste.punto(x[sobre], np.degrees(th[sobre]), r[sobre] + extra[sobre])
    X[~sobre, 2] += extra[~sobre]

    resaltado = None
    if paso.resaltar is not None:
        a, b = paso.resaltar
        resaltado = (float(ctrl_s[a]), float(ctrl_s[b]))
    # Cerca del poste la cuerda se modela algo tensa, como cuando se ata: sin gravedad, para
    # que los tramos que suben por el frente no se descuelguen ni amontonen la cuerda.
    _, _, r0 = poste.cilindricas(X)
    Xr = relajar(X, h, anfitrion=poste, gravedad=r0 > poste.rb + DISTANCIA_SIN_GRAVEDAD,
                 pasadas_largo=PASADAS_LARGO)

    def medir(Xr):
        pen = poste.penetracion(Xr)
        fallas = [] if pen <= PENETRACION_MAX else [
            f"Paso {paso.n}: la cuerda entra {pen:.2f} diámetros en el poste; el máximo es "
            f"{PENETRACION_MAX}."]
        return {"penetracion_poste": pen}, fallas

    return _resultado(paso.n, Xr, h, paso.secuencia, resaltado,
                      buscar=lambda Y: _cruces(Y, h, sobre, poste), medir=medir)


# --------------------------------------------------------------------------
# Curva
# --------------------------------------------------------------------------
def _curva(paso: Paso, poste: Poste):
    """La línea central muestreada cada h, la posición a lo largo de la cuerda de cada punto
    de control y qué puntos van sobre el poste."""
    P = paso.puntos
    sobre_ctrl = np.zeros(len(P), bool) if paso.sobre is None else paso.sobre
    aumentados, origen, es_poste = [], [], []
    i = 0
    while i < len(P):
        j = i
        while j + 1 < len(P) and sobre_ctrl[j + 1] == sobre_ctrl[i]:
            j += 1
        if not sobre_ctrl[i]:
            for k in range(i, j + 1):
                origen.append(len(aumentados))
                aumentados.append([P[k, 0], P[k, 1], R])
                es_poste.append(False)
        else:
            # Curva suave en la superficie desenrollada: x y el arco alrededor del eje.
            Q = np.column_stack([P[i:j + 1, 0], np.radians(P[i:j + 1, 1]) * poste.rb])
            if len(Q) == 1:
                D, ctrl = Q, [0]
            else:
                D, ctrl = catmull_rom(Q)
            largo = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(D, axis=0), axis=1))])
            tomar = set(ctrl)
            ultimo = -math.inf
            for k, s in enumerate(largo):
                if s - ultimo >= ARCO_DENSO:
                    tomar.add(k)
                    ultimo = s
            for k in sorted(tomar):
                if k in ctrl:
                    origen.append(len(aumentados))
                aumentados.append(poste.punto(D[k, 0], np.degrees(D[k, 1] / poste.rb)))
                es_poste.append(True)
        i = j + 1
    A = np.asarray(aumentados, float)
    D, ctrl_aug = catmull_rom(A)
    X, h, s_aug = remuestrear(D, ctrl_aug)
    # Qué puntos muestreados van sobre el poste: los que caen entre dos puntos aumentados
    # que lo están.
    es_poste = np.asarray(es_poste)
    s = np.arange(len(X)) * h
    tramo = np.clip(np.searchsorted(s_aug, s, side="right") - 1, 0, len(A) - 1)
    siguiente = np.minimum(tramo + 1, len(A) - 1)
    sobre = es_poste[tramo] & es_poste[siguiente]
    return X, h, s_aug[origen], sobre


# --------------------------------------------------------------------------
# Cruces
# --------------------------------------------------------------------------
def _cruces(X, h, sobre, poste: Poste) -> tuple[list[Cruce], list[tuple[float, float]]]:
    """Los cruces de la cuerda y, para cada uno, la «altura» de sus dos pasadas: distancia
    al eje sobre el poste, altura sobre la mesa."""
    x, th, r = poste.cilindricas(X)
    seg_poste = sobre[:-1] & sobre[1:]
    seg_mesa = ~sobre[:-1] & ~sobre[1:]
    # Sobre el poste, el ángulo se desenrolla a lo largo de la cuerda y se compara módulo
    # una vuelta.
    u = np.unwrap(th) * poste.rb
    en_poste = cruces_2d(np.column_stack([x, u]), seg_poste, h, periodo=2 * math.pi * poste.rb)
    en_mesa = cruces_2d(X[:, :2], seg_mesa, h)
    s = np.arange(len(X)) * h
    cruces, alturas = [], []
    for (sa, sb, seno, _), valor in [(c, r) for c in en_poste] + [(c, X[:, 2]) for c in en_mesa]:
        p = np.array([np.interp(sa, s, X[:, k]) for k in range(2)])
        cruces.append(Cruce(sa, sb, (float(p[0]), float(p[1])), seno))
        alturas.append((float(np.interp(sa, s, valor)), float(np.interp(sb, s, valor))))
    orden = sorted(range(len(cruces)), key=lambda k: cruces[k].sa)
    return [cruces[k] for k in orden], [alturas[k] for k in orden]

