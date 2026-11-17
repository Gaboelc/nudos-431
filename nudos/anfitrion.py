"""Nudos sobre un anfitrión rígido: el poste, un cilindro horizontal, la cruz, los dos
palos del amarre cuadrado, los palos paralelos del redondo y el trípode, el tubo de la cabeza
de turco, y el destorcedor y la estaca, dos cilindros parados sobre la mesa. Los pasos sobre
la cruz, los palos y el tubo los construye su plantilla
(nudos/plantillas/pasos.py), y los del destorcedor y la estaca, el generador libre
(nudos/libre.py), porque todo el nudo va sobre la mesa; aquí están solo como sólidos.

Sobre el poste, cada paso se construye como en el generador libre (nudos/libre.py), con tres
diferencias:
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
from dataclasses import replace

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
    MEDIDA = ("penetracion_poste", "en el poste")   # la clave de la medida y dónde entra

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


HOLGURA_CAPAS = 0.1   # en la cruz con dos capas bajo el palo de abajo, ver Cruz


class Cruz:
    """Dos palos del mismo radio cruzados en ángulo recto en x = y = 0, para los amarres.

    El de abajo va a lo largo de y, con el eje en x = 0 y a la altura radio + 1: se apoya en
    la cuerda que pasa por debajo, como el poste. En el amarre diagonal se cruzan dos capas de
    cuerda bajo él, y su eje queda a radio + 2,1 (Anfitrion.capas). El de arriba va a lo largo de x, con el eje
    en y = 0, y se apoya sobre el de abajo. Cada palo mide `largo` y está centrado en el cruce.
    Alrededor de cada palo, un ángulo se mide en su plano de corte, desde su lado positivo
    (x para el de abajo, y para el de arriba) hacia arriba: 90° es la cara de arriba."""

    def __init__(self, a: Anfitrion):
        self.radio, self.largo = a.radio, a.largo
        self.zb = a.radio + 2 * R * a.capas   # eje del palo de abajo, sobre las capas de cuerda
        if a.capas > 1:
            # Donde se cruzan dos capas, la de abajo pasa algo por fuera de la otra (en su plano
            # deja 1,1): un poco de aire, para que no quede apretada contra la mesa.
            self.zb += HOLGURA_CAPAS
        self.zt = self.zb + 2 * a.radio    # eje del palo de arriba
        self.rb = a.radio + R              # distancia al eje del eje de una cuerda que toca un palo

    def abajo(self, X) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Respecto al palo de abajo: posición a lo largo (y), ángulo en radianes y distancia al eje."""
        dx, dz = X[:, 0], X[:, 2] - self.zb
        return X[:, 1], np.arctan2(dz, dx), np.hypot(dx, dz)

    def arriba(self, X) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Respecto al palo de arriba: posición a lo largo (x), ángulo en radianes y distancia al eje."""
        dy, dz = X[:, 1], X[:, 2] - self.zt
        return X[:, 0], np.arctan2(dz, dy), np.hypot(dy, dz)

    def empujar(self, X, libre) -> None:
        """Saca de los dos palos los puntos que entraron, en dirección radial."""
        medio = self.largo / 2
        for eje, otro, zc in ((0, 1, self.zb), (1, 0, self.zt)):
            # El de abajo: eje a lo largo de y, se mide en (x, z); el de arriba, en (y, z).
            d1, dz = X[:, eje], X[:, 2] - zc
            d = np.hypot(d1, dz)
            m = libre & (d < self.rb) & (np.abs(X[:, otro]) < medio)
            if m.any():
                k = self.rb / np.maximum(d[m], 1e-9)
                X[m, eje] = d1[m] * k
                X[m, 2] = zc + dz[m] * k

    def penetracion(self, X) -> float:
        """Cuánto entra la cuerda en el palo donde más entra (0 si no entra)."""
        medio = self.largo / 2
        peor = 0.0
        for (largo, _, r) in (self.abajo(X), self.arriba(X)):
            m = np.abs(largo) < medio
            if m.any():
                peor = max(peor, float((self.rb - r[m]).max()))
        return peor

    def datos(self) -> dict:
        """Lo que necesita render/escena.js para dibujarla: «z_abajo» y «z_arriba» son las
        alturas de los ejes del palo de abajo (a lo largo de y) y del de arriba (a lo largo
        de x)."""
        return {"tipo": "cruz", "radio": self.radio, "largo": self.largo,
                "z_abajo": self.zb, "z_arriba": self.zt}

    def voltear(self, r: Resultado) -> tuple[Resultado, dict]:
        """El amarre terminado, visto por detrás: los palos y la cuerda, juntos, se voltean
        como un marco sobre la mesa, con media vuelta alrededor del eje y (como una página),
        y se apoyan en lo que queda más abajo. Así el palo de abajo queda encima y se ven las
        vueltas que pasaban por debajo de él.

        Es un giro rígido: la cuerda no se relaja otra vez y, como los cruces se miden
        respecto a los palos y no a la mesa, la secuencia no cambia. Devuelve el paso
        volteado y los datos de la cruz volteada para render/escena.js, donde el palo de
        abajo tiene su eje más alto que el de arriba."""
        X = r.puntos
        alto = max(float((X[:, 2] + R).max()), self.zt + self.radio)   # lo más alto, antes de voltear
        Y = np.column_stack([-X[:, 0], X[:, 1], alto - X[:, 2]])
        volteado = replace(r, puntos=Y, resaltado=None,
                           cruces={et: (-x, y) for et, (x, y) in r.cruces.items()},
                           medidas={**r.medidas, "altura_max": float(Y[:, 2].max())})
        return volteado, {**self.datos(), "z_abajo": alto - self.zb, "z_arriba": alto - self.zt}


HUECO = 1.1   # entre las caras de dos palos vecinos: ahí pasan los ahorcados, de a uno
DEBAJO = 2.1  # de la mesa al eje de los palos, más su radio: dos capas de cuerda y algo de holgura


class Palos:
    """Dos o tres palos del mismo radio, acostados uno junto al otro a lo largo de x, para el
    amarre redondo y el trípode. Están centrados en x = 0, miden `largo` y van a lo largo de y,
    simétricos alrededor de y = 0, con HUECO entre sus caras. El de delante es el de y
    negativa, hacia quien ata. Sus ejes están a la altura radio + DEBAJO: por debajo del hueco
    pasan dos capas de cuerda, la vuelta y el ahorcado que la rodea, y así ninguna baja de la
    mesa. Los ahorcados las rodean con un poco de holgura, porque la relajación no deja que la
    cuerda se doble con menos de 1,1 de radio.

    Alrededor de cada palo, un ángulo se mide en su plano de corte (y, z), desde +y (hacia el
    fondo de la mesa) hacia arriba: 90° es la cara de arriba y 180° la de delante."""

    def __init__(self, a: Anfitrion, z: float | None = None):
        self.radio, self.largo, self.cantidad = a.radio, a.largo, a.cantidad
        self.zc = a.radio + DEBAJO if z is None else z   # altura de los ejes
        self.rb = a.radio + R                           # distancia al eje de una cuerda que toca un palo
        paso = 2 * a.radio + HUECO
        self.ys = tuple(paso * (i - (a.cantidad - 1) / 2) for i in range(a.cantidad))
        # El centro de cada hueco, de delante hacia atrás.
        self.huecos = tuple((u + v) / 2 for u, v in zip(self.ys, self.ys[1:]))

    def punto(self, i: int, x, grados, r=None) -> np.ndarray:
        """De [x, ángulo] alrededor del palo i (0 es el de delante) a [x, y, z]."""
        th = np.radians(grados)
        r = self.rb if r is None else r
        return np.stack([np.asarray(x, float) + 0 * th, self.ys[i] + r * np.cos(th),
                         self.zc + r * np.sin(th)], axis=-1)

    def cilindricas(self, i: int, X) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Respecto al palo i: x, ángulo en radianes y distancia al eje."""
        dy, dz = X[:, 1] - self.ys[i], X[:, 2] - self.zc
        return X[:, 0], np.arctan2(dz, dy), np.hypot(dy, dz)

    def empujar(self, X, libre) -> None:
        """Saca de cada palo los puntos que entraron, en dirección radial."""
        dentro = np.abs(X[:, 0]) < self.largo / 2
        for y in self.ys:
            dy, dz = X[:, 1] - y, X[:, 2] - self.zc
            d = np.hypot(dy, dz)
            m = libre & dentro & (d < self.rb)
            if m.any():
                k = self.rb / np.maximum(d[m], 1e-9)
                X[m, 1] = y + dy[m] * k
                X[m, 2] = self.zc + dz[m] * k

    def penetracion(self, X) -> float:
        """Cuánto entra la cuerda en el palo donde más entra (0 si no entra)."""
        m = np.abs(X[:, 0]) < self.largo / 2
        if not m.any():
            return 0.0
        d = np.min([np.hypot(X[m, 1] - y, X[m, 2] - self.zc) for y in self.ys], axis=0)
        return float(max(0.0, (self.rb - d).max()))

    def datos(self) -> dict:
        """Lo que necesita render/escena.js para dibujarlos: la «y» de cada eje y su altura «z»."""
        return {"tipo": "palos", "radio": self.radio, "largo": self.largo,
                "y": [float(y) for y in self.ys], "z": self.zc}

    def voltear(self, r: Resultado) -> tuple[Resultado, dict]:
        """El amarre terminado, visto por detrás: los palos y la cuerda, juntos, se voltean como
        una página, con media vuelta alrededor del eje y, y se apoyan en lo que queda más abajo.
        Los palos siguen a lo largo de x y el de delante sigue delante.

        Es un giro rígido, como el de la cruz: la cuerda no se relaja otra vez y, como los
        cruces se miden respecto a los palos, la secuencia no cambia. Devuelve el paso volteado
        y los datos de los palos volteados para render/escena.js."""
        X = r.puntos
        alto = max(float((X[:, 2] + R).max()), self.zc + self.radio)
        Y = np.column_stack([-X[:, 0], X[:, 1], alto - X[:, 2]])
        volteado = replace(r, puntos=Y, resaltado=None,
                           cruces={et: (-x, y) for et, (x, y) in r.cruces.items()},
                           medidas={**r.medidas, "altura_max": float(Y[:, 2].max())})
        return volteado, {**self.datos(), "z": alto - self.zc}


class Tubo:
    """El tubo de la cabeza de turco: un cilindro horizontal a lo largo de x, centrado en x = 0
    y con el eje en y = 0. El nudo lo rodea entero y se apoya sobre él: debajo de cada cruce
    hay dos capas de cuerda, así que su eje queda a la altura radio + 2.

    Alrededor del eje, un ángulo se mide como sobre el poste: 0 arriba, 90 hacia quien ata,
    180 abajo y 270 (o −90) atrás."""

    def __init__(self, a: Anfitrion):
        self.radio, self.largo = a.radio, a.largo
        self.zc = a.radio + 4 * R    # altura del eje: dos diámetros de cuerda sobre la mesa
        self.rb = a.radio + R        # distancia al eje del eje de una cuerda que toca el tubo

    def punto(self, x, grados, r=None) -> np.ndarray:
        """De [x, ángulo] alrededor del tubo a [x, y, z]."""
        th = np.radians(grados)
        r = self.rb if r is None else r
        return np.stack([np.asarray(x, float) + 0 * th, -r * np.sin(th), self.zc + r * np.cos(th)], axis=-1)

    def cilindricas(self, X) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """x, ángulo en radianes (entre -π y π) y distancia al eje."""
        dy, dz = X[:, 1], X[:, 2] - self.zc
        return X[:, 0], np.arctan2(-dy, dz), np.hypot(dy, dz)

    def empujar(self, X, libre) -> None:
        """Saca del tubo los puntos que entraron, en dirección radial."""
        dy, dz = X[:, 1], X[:, 2] - self.zc
        d = np.hypot(dy, dz)
        m = libre & (d < self.rb) & (np.abs(X[:, 0]) < self.largo / 2)
        if m.any():
            k = self.rb / np.maximum(d[m], 1e-9)
            X[m, 1] = dy[m] * k
            X[m, 2] = self.zc + dz[m] * k

    def penetracion(self, X) -> float:
        """Cuánto entra la cuerda en el tubo (0 si no entra)."""
        x, _, r = self.cilindricas(X)
        m = np.abs(x) < self.largo / 2
        return float(max(0.0, (self.rb - r[m]).max())) if m.any() else 0.0

    def datos(self) -> dict:
        """Lo que necesita render/escena.js para dibujarlo."""
        return {"tipo": "tubo", "radio": self.radio, "largo": self.largo, "z": self.zc}

    def voltear(self, r: Resultado) -> Resultado:
        """El nudo terminado, visto por detrás: el tubo y el nudo girados media vuelta
        alrededor del eje, como se gira el tubo en la mano. Es un giro rígido: la cuerda no se
        relaja otra vez, y como los cruces se miden respecto al tubo, la secuencia no cambia.
        Cada cruce guarda su lugar en el mapa del nudo, que no cambia al girarlo."""
        X = r.puntos
        Y = np.column_stack([X[:, 0], -X[:, 1], 2 * self.zc - X[:, 2]])
        giro = None if r.giro is None else r.giro + 180.0
        return replace(r, puntos=Y, resaltado=None, giro=giro,
                       medidas={**r.medidas, "altura_max": float(Y[:, 2].max())})


class Parado:
    """Un cilindro parado sobre la mesa, con el eje vertical en x = y = 0, de la mesa hasta
    `alto`: el destorcedor y la estaca. La cuerda le da la vuelta a ras de la mesa y nunca
    pasa por encima, así que el nudo se construye, se voltea y se aprieta como uno libre
    (nudos/libre.py, nudos/apretar.py): solo cambia que la cuerda no puede entrar en él. Como
    está en x = 0 y es simétrico, al voltear el nudo como una página queda en el mismo lugar.
    Cada tipo dice su nombre (TIPO) y la clave de su medida (MEDIDA)."""
    TIPO = ""
    MEDIDA = ("", "")

    def __init__(self, a: Anfitrion):
        self.radio, self.alto = a.radio, a.alto
        self.rb = a.radio + R    # distancia al eje del eje de una cuerda que lo toca

    def empujar(self, X, libre) -> None:
        """Saca del cilindro los puntos que entraron, hacia afuera en el plano de la mesa,
        a cualquier altura: la cuerda no pasa por encima. Un punto justo en el eje sale hacia
        x positivo."""
        d = np.hypot(X[:, 0], X[:, 1])
        m = libre & (d < self.rb)
        if m.any():
            dm = d[m]
            lejos = dm > 1e-9
            ux = np.where(lejos, X[m, 0] / np.maximum(dm, 1e-9), 1.0)
            uy = np.where(lejos, X[m, 1] / np.maximum(dm, 1e-9), 0.0)
            X[m, 0] = ux * self.rb
            X[m, 1] = uy * self.rb

    def penetracion(self, X) -> float:
        """Cuánto entra la cuerda en el cilindro (0 si no entra)."""
        return float(max(0.0, (self.rb - np.hypot(X[:, 0], X[:, 1])).max()))

    def datos(self) -> dict:
        """Lo que necesita render/escena.js para dibujarlo."""
        return {"tipo": self.TIPO, "radio": self.radio, "alto": self.alto}


class Destorcedor(Parado):
    """El ojo de un destorcedor de pesca, para el nudo aguja: un cilindro corto, de metal."""
    TIPO = "destorcedor"
    MEDIDA = ("penetracion_destorcedor", "en el destorcedor")


class Estaca(Parado):
    """La estaca del tensor ajustable, clavada en el suelo: el mismo cilindro, de madera y
    más alto."""
    TIPO = "estaca"
    MEDIDA = ("penetracion_estaca", "en la estaca")


def solido(a: Anfitrion) -> Poste | Cruz | Palos | Tubo | Parado:
    """El anfitrión de la especificación como sólido."""
    return {"cruz": Cruz, "palos": Palos, "tubo": Tubo, "destorcedor": Destorcedor,
            "estaca": Estaca}.get(a.tipo, Poste)(a)


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
    return _resultado(paso.n, Xr, h, paso.secuencia, resaltado,
                      buscar=lambda Y: _cruces(Y, h, sobre, poste), medir=_medir(paso.n, poste))


def _medir(n: int, poste: Poste | Parado):
    """La comprobación propia del anfitrión: cuánto entra la cuerda en él."""
    clave, donde = poste.MEDIDA

    def medir(X):
        pen = poste.penetracion(X)
        fallas = [] if pen <= PENETRACION_MAX else [
            f"Paso {n}: la cuerda entra {pen:.2f} diámetros {donde}; el máximo es "
            f"{PENETRACION_MAX}."]
        return {clave: pen}, fallas
    return medir


def en_la_mesa(a: Anfitrion | None, n: int) -> dict:
    """Lo que se le pasa a la relajación y a la comprobación de un nudo libre con este
    anfitrión (el destorcedor o la estaca), para el paso `n`: `anfitrion`, que saca la cuerda de él, y
    `medir`, cuánto entra. Sin anfitrión, nada."""
    if a is None:
        return {}
    d = solido(a)
    return {"anfitrion": d, "medir": _medir(n, d)}


def apretar_paso(paso: Paso, anfitrion: Anfitrion, final: Resultado, rondas: int,
                 registro: list | None = None) -> Resultado:
    """El último paso sobre el poste (`final`, ya construido), apretado con nudos/apretar.py.
    Se le pasa lo mismo que a la relajación y a la comprobación del paso: cómo sacar la
    cuerda del poste, dónde no cae (cerca de él no hay gravedad) y cómo buscar los cruces en
    sus dos mapas. Qué puntos van sobre el poste se decide en el último paso: cada punto del
    apretado lo toma de donde estaba ahí, por su coordenada material, aunque la cuerda se
    acorte."""
    from .apretar import apretar
    poste = Poste(anfitrion)
    X, h, _, sobre = _curva(paso, poste)
    if len(X) != len(final.puntos) or h != final.h:
        raise ValueError(f"Paso {paso.n}: el paso construido no es el de la especificación.")

    def buscar(Y, hY, u):
        return _cruces(Y, hY, sobre[np.clip(np.round(u / h).astype(int), 0, len(sobre) - 1)], poste)

    return apretar(final, paso.secuencia, rondas=rondas, anfitrion=poste,
                   gravedad=lambda Y: poste.cilindricas(Y)[2] > poste.rb + DISTANCIA_SIN_GRAVEDAD,
                   buscar=buscar, medir=_medir(paso.n, poste), registro=registro)


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

