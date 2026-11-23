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
from .spec import HUECO_CORNAMUSA, PIE_CORNAMUSA, Anfitrion, Paso

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


class Cabo:
    """La punta de un cabo, para el refuerzo de cabo: un cilindro horizontal a lo largo de x,
    con el eje en y = 0, que es un sólido aunque se dibuja como cuerda. La punta, cortada, está
    en x = 0, y el cabo sigue hacia x negativo hasta -largo. Se apoya en la mesa sobre las
    vueltas del cordel, que pasan por debajo, así que su eje queda a la altura radio + 1, como
    el poste. Más allá de la punta no empuja: el cordel puede pasar por delante del corte.

    Alrededor del eje, un ángulo se mide como sobre el poste: 0 arriba, 90 hacia quien ata."""
    MEDIDA = ("penetracion_cabo", "en el cabo")

    def __init__(self, a: Anfitrion):
        self.radio, self.largo = a.radio, a.largo
        self.zc = a.radio + 2 * R    # altura del eje
        self.rb = a.radio + R        # distancia al eje del eje de una cuerda que toca el cabo

    def punto(self, x, grados, r=None) -> np.ndarray:
        """De [x, ángulo] alrededor del cabo a [x, y, z]."""
        th = np.radians(grados)
        r = self.rb if r is None else r
        return np.stack([np.asarray(x, float) + 0 * th, -r * np.sin(th), self.zc + r * np.cos(th)], axis=-1)

    def cilindricas(self, X) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """x, ángulo en radianes (entre -π y π) y distancia al eje."""
        dy, dz = X[:, 1], X[:, 2] - self.zc
        return X[:, 0], np.arctan2(-dy, dz), np.hypot(dy, dz)

    def _dentro(self, x) -> np.ndarray:
        return (x > -self.largo) & (x < 0.0)

    def empujar(self, X, libre) -> None:
        """Saca del cabo los puntos que entraron, en dirección radial."""
        dy, dz = X[:, 1], X[:, 2] - self.zc
        d = np.hypot(dy, dz)
        m = libre & (d < self.rb) & self._dentro(X[:, 0])
        if m.any():
            k = self.rb / np.maximum(d[m], 1e-9)
            X[m, 1] = dy[m] * k
            X[m, 2] = self.zc + dz[m] * k

    def penetracion(self, X) -> float:
        """Cuánto entra el cordel en el cabo (0 si no entra)."""
        x, _, r = self.cilindricas(X)
        m = self._dentro(x)
        return float(max(0.0, (self.rb - r[m]).max())) if m.any() else 0.0

    def datos(self) -> dict:
        """Lo que necesita render/escena.js para dibujarlo: el cabo va de -largo a 0 a lo
        largo de x, con el eje a la altura z."""
        return {"tipo": "cabo", "radio": self.radio, "largo": self.largo, "z": self.zc}

    def voltear(self, r: Resultado) -> tuple[Resultado, dict]:
        """El refuerzo terminado, visto por detrás: el cabo y el cordel girados media vuelta
        alrededor del eje, como se gira el cabo en la mano, y apoyados en lo que queda más
        abajo. Es un giro rígido: el cordel no se relaja otra vez y, como los cruces se miden
        respecto al cabo, la secuencia no cambia. Devuelve el paso girado y los datos del cabo
        girado para render/escena.js."""
        X = r.puntos
        Y = np.column_stack([X[:, 0], -X[:, 1], 2 * self.zc - X[:, 2]])
        # Lo más bajo, el cordel o el cabo, queda sobre la mesa.
        bajar = min(float(Y[:, 2].min()) - R, self.zc - self.radio)
        Y[:, 2] -= bajar
        volteado = replace(r, puntos=Y, resaltado=None,
                           cruces={et: (x, -y) for et, (x, y) in r.cruces.items()},
                           medidas={**r.medidas, "altura_max": float(Y[:, 2].max())})
        return volteado, {**self.datos(), "z": self.zc - bajar}


CANTO = 0.45  # radio de los cantos del tablón: casi vivos, y la cuerda que los rodea se dobla con
#               radio 0,95, apenas más que el mínimo (0,9). Un canto vivo la doblaría con 0,5.


class Tablon:
    """El tablón de la eslinga de andamio: una tabla acostada a lo largo de x, de `ancho` y
    `grueso`, con los cantos redondeados con radio CANTO. La punta está en x = 0 y la tabla
    sigue hacia x negativo hasta -`largo`. Se apoya sobre la cuerda que pasa por debajo, así
    que su cara de abajo queda a la altura 1, como el poste.

    Es el poste con otro perfil: un punto sobre él es [x, ángulo], y el ángulo se reparte parejo
    a lo largo del contorno que sigue el eje de una cuerda que lo toca (a CANTO + R del núcleo,
    el rectángulo sin los cantos). Así 0, 90, 180 y 270 caen en el medio de la cara de arriba,
    la de delante, la de abajo y la de atrás. `rb` es el radio de un círculo del mismo
    perímetro que ese contorno, y `cilindricas` da la «distancia al eje» como rb más lo que el
    punto se aleja del contorno: con eso, todo lo del poste (_curva, _cruces, construir_paso,
    apretar_paso) vale igual, y encima es lo más lejos de la superficie del tablón."""
    MEDIDA = ("penetracion_tablon", "en el tablón")

    def __init__(self, a: Anfitrion):
        self.ancho, self.grueso, self.largo = a.ancho, a.grueso, a.largo
        self.zc = a.grueso / 2 + 2 * R           # altura del centro
        self.ay = a.ancho / 2 - CANTO            # medio núcleo, a lo largo de y
        self.az = a.grueso / 2 - CANTO           # y a lo largo de z
        self.e0 = CANTO + R                      # del núcleo al eje de una cuerda que lo toca
        # Los tramos del contorno, desde el medio de la cara de arriba hacia delante: la mitad
        # de la cara de arriba, un canto, la cara de delante, un canto, la de abajo, un canto,
        # la de atrás, un canto y la otra mitad de la de arriba.
        cuarto = self.e0 * math.pi / 2
        self._largos = np.array([self.ay, cuarto, 2 * self.az, cuarto, 2 * self.ay, cuarto,
                                 2 * self.az, cuarto, self.ay])
        self._inicios = np.concatenate([[0.0], np.cumsum(self._largos)[:-1]])
        self.perimetro = float(self._largos.sum())
        self.rb = self.perimetro / (2 * math.pi)

    # Del ángulo al contorno y de vuelta -------------------------------------------------
    def _contorno(self, s):
        """Para cada largo s a lo largo del contorno (0 en el medio de la cara de arriba,
        hacia delante), el punto del núcleo más cercano (qy, qz) y la normal (ny, nz)."""
        s = np.mod(np.asarray(s, float), self.perimetro)
        k = np.clip(np.searchsorted(self._inicios, s, side="right") - 1, 0, 8)
        t = s - self._inicios[k]
        ay, az, e0 = self.ay, self.az, self.e0
        cara = [k == 0, k == 2, k == 4, k == 6, k == 8]
        fi = np.select([k == 1, k == 3, k == 5, k == 7],
                       [t / e0, math.pi / 2 + t / e0, math.pi + t / e0, 1.5 * math.pi + t / e0], 0.0)
        esquina = np.array([[-ay, az], [-ay, -az], [ay, -az], [ay, az]])[np.clip((k - 1) // 2, 0, 3)]
        uno = np.ones_like(t)
        qy = np.select(cara, [-t, -ay * uno, -ay + t, ay * uno, ay - t], esquina[..., 0])
        qz = np.select(cara, [az * uno, az - t, -az * uno, -az + t, az * uno], esquina[..., 1])
        ny = np.select(cara, [0 * uno, -uno, 0 * uno, uno, 0 * uno], -np.sin(fi))
        nz = np.select(cara, [uno, 0 * uno, -uno, 0 * uno, uno], np.cos(fi))
        return qy, qz, ny, nz

    def punto(self, x, grados, r=None) -> np.ndarray:
        """De [x, ángulo] sobre el tablón a [x, y, z]. 0° arriba, 90° hacia quien ata. `r`, si
        se da, es la «distancia al eje» de cilindricas: rb toca el tablón."""
        grados = np.asarray(grados, float)
        qy, qz, ny, nz = self._contorno(np.radians(grados) * self.rb)
        lejos = self.e0 + (0.0 if r is None else np.asarray(r, float) - self.rb)
        return np.stack([np.asarray(x, float) + 0 * grados, qy + ny * lejos,
                         self.zc + qz + nz * lejos], axis=-1)

    def _corte(self, dy, dz):
        """En el corte (y, z): el punto del núcleo más cercano, la normal hacia afuera y la
        distancia con signo al núcleo, negativa si el punto está dentro de él."""
        ay, az = self.ay, self.az
        qy, qz = np.clip(dy, -ay, ay), np.clip(dz, -az, az)
        vy, vz = dy - qy, dz - qz
        d = np.hypot(vy, vz)
        fuera = d > 1e-12
        div = np.where(fuera, d, 1.0)
        ny, nz = np.where(fuera, vy / div, 0.0), np.where(fuera, vz / div, 0.0)
        # Dentro del núcleo, la cara más cercana.
        fy, fz = ay - np.abs(dy), az - np.abs(dz)
        arriba_o_abajo = ~fuera & (fz <= fy)
        de_lado = ~fuera & ~arriba_o_abajo
        sz, sy = np.where(dz >= 0, 1.0, -1.0), np.where(dy >= 0, 1.0, -1.0)
        qz = np.where(arriba_o_abajo, sz * az, qz)
        nz = np.where(arriba_o_abajo, sz, nz)
        qy = np.where(de_lado, sy * ay, qy)
        ny = np.where(de_lado, sy, ny)
        d = np.where(arriba_o_abajo, -fz, np.where(de_lado, -fy, d))
        return qy, qz, ny, nz, d

    def cilindricas(self, X) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """x, ángulo en radianes (entre -π y π) y «distancia al eje»: rb más lo que el punto
        se aleja del contorno de una cuerda que toca el tablón."""
        ay, az, e0 = self.ay, self.az, self.e0
        qy, qz, ny, nz, d = self._corte(X[:, 1], X[:, 2] - self.zc)
        # El largo a lo largo del borde del núcleo, desde el medio de arriba hacia delante,
        # más lo que gira la normal (e0 por radián), es el largo a lo largo del contorno.
        arriba_delante = (qz >= az) & (qy <= 0)
        delante = ~arriba_delante & (qy <= -ay)
        abajo = ~arriba_delante & ~delante & (qz <= -az)
        atras = ~arriba_delante & ~delante & ~abajo & (qy >= ay)
        arriba_atras = ~arriba_delante & ~delante & ~abajo & ~atras
        borde = np.select([arriba_delante, delante, abajo, atras],
                          [-qy, ay + (az - qz), ay + 2 * az + (qy + ay), 3 * ay + 2 * az + (qz + az)],
                          3 * ay + 4 * az + (ay - qy))
        fi = np.mod(np.arctan2(-ny, nz), 2 * math.pi)
        # En la mitad de atrás de la cara de arriba, la normal ya dio la vuelta entera.
        fi = np.where(arriba_atras & (fi < math.pi), 2 * math.pi, fi)
        th = (borde + e0 * fi) / self.rb
        th = np.where(th > math.pi, th - 2 * math.pi, th)
        return X[:, 0], th, self.rb + (d - e0)

    # El sólido --------------------------------------------------------------------------
    def _caja(self, X):
        """En 3D, el punto más cercano del núcleo (el tablón sin los cantos, también en la
        punta y en el otro extremo), la normal y la distancia con signo."""
        lo = np.array([-self.largo + CANTO, -self.ay, self.zc - self.az])
        hi = np.array([-CANTO, self.ay, self.zc + self.az])
        Q = np.clip(X, lo, hi)
        V = X - Q
        d = np.linalg.norm(V, axis=1)
        fuera = d > 1e-12
        N = np.zeros_like(X)
        N[fuera] = V[fuera] / d[fuera, None]
        dentro = ~fuera
        if dentro.any():
            P = X[dentro]
            caras = np.column_stack([P - lo, hi - P])          # x-, y-, z-, x+, y+, z+
            c = np.argmin(caras, axis=1)
            i = np.arange(len(P))
            eje = c % 3
            Nd = np.zeros_like(P)
            Nd[i, eje] = np.where(c < 3, -1.0, 1.0)
            Qd = P.copy()
            Qd[i, eje] = np.where(c < 3, lo[eje], hi[eje])
            N[dentro], Q[dentro], d[dentro] = Nd, Qd, -caras[i, c]
        return Q, N, d

    def empujar(self, X, libre) -> None:
        """Saca del tablón los puntos que entraron, hacia la cara o el canto más cercano."""
        Q, N, d = self._caja(X)
        m = libre & (d < self.e0)
        if m.any():
            X[m] = Q[m] + N[m] * self.e0

    def penetracion(self, X) -> float:
        """Cuánto entra la cuerda en el tablón (0 si no entra)."""
        _, _, d = self._caja(X)
        return float(max(0.0, (self.e0 - d).max()))

    def datos(self, z: float | None = None, desde: float | None = None) -> dict:
        """Lo que necesita render/escena.js para dibujarlo: va de «desde» a «hasta» a lo largo
        de x, con el centro del corte en y = 0 y a la altura «z»."""
        desde = -self.largo if desde is None else desde
        return {"tipo": "tablon", "ancho": self.ancho, "grueso": self.grueso, "canto": CANTO,
                "desde": desde, "hasta": desde + self.largo, "y": 0.0,
                "z": self.zc if z is None else z}

    def voltear(self, r: Resultado) -> tuple[Resultado, dict]:
        """La eslinga terminada, vista por detrás: el tablón y la cuerda, juntos, se voltean
        como una página, con media vuelta alrededor del eje y, y se apoyan en lo que queda más
        abajo, como los palos. Se ve la cara de abajo, la que en los pasos queda contra la
        mesa. Es un giro rígido: la cuerda no se relaja otra vez y, como los cruces se miden
        respecto al tablón, la secuencia no cambia. Devuelve el paso volteado y los datos del
        tablón volteado para render/escena.js."""
        X = r.puntos
        alto = max(float((X[:, 2] + R).max()), self.zc + self.grueso / 2)
        Y = np.column_stack([-X[:, 0], X[:, 1], alto - X[:, 2]])
        volteado = replace(r, puntos=Y, resaltado=None,
                           cruces={et: (-x, y) for et, (x, y) in r.cruces.items()},
                           medidas={**r.medidas, "altura_max": float(Y[:, 2].max())})
        return volteado, self.datos(z=alto - self.zc, desde=0.0)


CERCA_CORNAMUSA = 3.0   # dos pasadas a menos de esto a lo largo de la cuerda no son un cruce


class Cornamusa:
    """La cornamusa de la vuelta de cornamusa, fija a la mesa, a lo largo de x y centrada en
    x = y = 0. Tiene dos partes:
    - Los cuernos: una barra de `radio`, de `largo` de punta a punta y con las puntas
      redondeadas, con el eje en y = 0 y a la altura HUECO_CORNAMUSA + radio: bajo cada cuerno
      pasa la cuerda, y la barra se apoya en ella, como el poste.
    - El pie: un bloque en el medio, de PIE_CORNAMUSA de largo y del ancho de la barra, que va
      de la mesa a la barra. Visto desde arriba, sus puntas son redondas, así que la cuerda que
      le da la vuelta bajo un cuerno se dobla con radio de al menos `radio` + R.

    Lo que va pegado a la barra, por encima o rodeando un cuerno, se escribe [x, ángulo], como
    sobre el poste: `punto` y `cilindricas` son los del poste, alrededor del eje de la barra. Lo
    demás va sobre la mesa. Los cruces se buscan todos desde arriba, como sobre la mesa
    (`cruces`): la cornamusa es baja, y donde un tramo pasa sobre un cuerno y otro por debajo de
    él, hay un cruce de verdad, con encima el de arriba. Esos cruces no se elevan al construir:
    la barra ya separa sus dos pasadas (`separados`)."""
    MEDIDA = ("penetracion_cornamusa", "en la cornamusa")

    def __init__(self, a: Anfitrion):
        self.radio, self.largo = a.radio, a.largo
        self.zc = HUECO_CORNAMUSA + a.radio          # altura del eje de la barra
        self.rb = a.radio + R                        # distancia al eje de una cuerda que la toca
        self.punta = a.largo / 2 - a.radio           # centro de la punta redonda de cada cuerno
        self.pie = PIE_CORNAMUSA / 2 - a.radio       # mitad del tramo recto del pie

    def punto(self, x, grados, r=None) -> np.ndarray:
        """De [x, ángulo] sobre la barra a [x, y, z]. 0° arriba, 90° hacia quien ata."""
        th = np.radians(grados)
        r = self.rb if r is None else r
        return np.stack([np.asarray(x, float) + 0 * th, -r * np.sin(th), self.zc + r * np.cos(th)], axis=-1)

    def cilindricas(self, X) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """x, ángulo en radianes (entre -π y π) y distancia al eje de la barra, contando sus
        puntas redondas: más allá de un cuerno, la cuerda está lejos de la cornamusa aunque
        quede a la altura de la barra (de eso depende dónde no hay gravedad)."""
        dy, dz = X[:, 1], X[:, 2] - self.zc
        dx = np.maximum(np.abs(X[:, 0]) - self.punta, 0.0)
        return X[:, 0], np.arctan2(-dy, dz), np.sqrt(dx * dx + dy * dy + dz * dz)

    def _partes(self, X):
        """El punto más cercano de la barra y del pie (sus ejes) y la distancia a cada uno."""
        Qb = np.column_stack([np.clip(X[:, 0], -self.punta, self.punta),
                              np.zeros(len(X)), np.full(len(X), self.zc)])
        # El pie: el segmento de su eje, a cada altura entre la mesa y la barra.
        Qp = np.column_stack([np.clip(X[:, 0], -self.pie, self.pie), np.zeros(len(X)),
                              np.clip(X[:, 2], -math.inf, self.zc)])
        return Qb, np.linalg.norm(X - Qb, axis=1), Qp, np.linalg.norm(X - Qp, axis=1)

    def empujar(self, X, libre) -> None:
        """Saca de la barra y del pie los puntos que entraron, hacia afuera de cada uno."""
        for _ in range(2):   # lo que sale del pie puede quedar en la barra, y al revés
            for k in (0, 2):   # la barra y el pie
                partes = self._partes(X)
                Q, d = partes[k], partes[k + 1]
                m = libre & (d < self.rb)
                if m.any():
                    V = X[m] - Q[m]
                    n = np.linalg.norm(V, axis=1)
                    # Un punto justo en el eje sale hacia delante.
                    V[n < 1e-9] = [0.0, -1.0, 0.0]
                    n[n < 1e-9] = 1.0
                    X[m] = Q[m] + V / n[:, None] * self.rb

    def penetracion(self, X) -> float:
        """Cuánto entra la cuerda en la cornamusa (0 si no entra)."""
        _, db, _, dp = self._partes(X)
        return float(max(0.0, (self.rb - np.minimum(db, dp)).max()))

    def cruces(self, X, h, sobre) -> tuple[list[Cruce], list[tuple[float, float]]]:
        """Los cruces desde arriba, con la altura de sus dos pasadas. Dos pasadas a menos de
        CERCA_CORNAMUSA a lo largo de la cuerda no cuentan: donde la cuerda baja casi vertical
        por el costado de la barra, vista desde arriba se pliega sobre sí misma."""
        s = np.arange(len(X)) * h
        cruces, alturas = [], []
        for sa, sb, seno, p in cruces_2d(X[:, :2], np.ones(len(X) - 1, bool), h):
            if abs(sb - sa) < CERCA_CORNAMUSA:
                continue
            cruces.append(Cruce(sa, sb, p, seno))
            alturas.append((float(np.interp(sa, s, X[:, 2])), float(np.interp(sb, s, X[:, 2]))))
        orden = sorted(range(len(cruces)), key=lambda k: cruces[k].sa)
        return [cruces[k] for k in orden], [alturas[k] for k in orden]

    def separados(self, X, h, sobre, c: Cruce) -> bool:
        """Si las dos pasadas del cruce ya están separadas en altura, como una que pasa sobre
        un cuerno y otra por debajo de él. Esas no se elevan como las de la mesa, que parten
        las dos de la misma altura."""
        s = np.arange(len(X)) * h
        za, zb = (float(np.interp(v, s, X[:, 2])) for v in (c.sa, c.sb))
        return abs(za - zb) >= 2 * R

    def datos(self) -> dict:
        """Lo que necesita render/escena.js para dibujarla."""
        return {"tipo": "cornamusa", "radio": self.radio, "largo": self.largo, "z": self.zc,
                "pie": PIE_CORNAMUSA}


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


def solido(a: Anfitrion) -> Poste | Cruz | Palos | Tubo | Cabo | Tablon | Cornamusa | Parado:
    """El anfitrión de la especificación como sólido."""
    return {"cruz": Cruz, "palos": Palos, "tubo": Tubo, "cabo": Cabo, "destorcedor": Destorcedor,
            "estaca": Estaca, "tablon": Tablon, "cornamusa": Cornamusa}.get(a.tipo, Poste)(a)


def sobre_superficie(a: Anfitrion) -> Poste | Tablon | Cornamusa:
    """El sólido de un nudo con segmentos sobre su superficie, [x, ángulo]: el poste, el
    tablón o la cornamusa. Se construyen por el mismo camino (construir_paso, apretar_paso)."""
    return {"tablon": Tablon, "cornamusa": Cornamusa}.get(a.tipo, Poste)(a)


def _buscar(X, h, sobre, poste):
    """Los cruces y sus alturas: los que el sólido busca él mismo, como la cornamusa desde
    arriba, o en los dos mapas del poste (_cruces)."""
    if hasattr(poste, "cruces"):
        return poste.cruces(X, h, sobre)
    return _cruces(X, h, sobre, poste)


def construir_paso(paso: Paso, anfitrion: Anfitrion) -> Resultado:
    poste = sobre_superficie(anfitrion)
    X, h, ctrl_s, sobre = _curva(paso, poste)
    cruces, _ = _buscar(X, h, sobre, poste)
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
    arriba = encimas(cruces, paso.secuencia)
    if hasattr(poste, "separados"):
        # Sobre la cornamusa, un tramo que pasa bajo un cuerno ya está separado por él del que
        # pasa por encima: ese cruce no se eleva.
        elevar_k = [not poste.separados(X, h, sobre, c) for c in cruces]
        cruces = [c for c, e in zip(cruces, elevar_k) if e]
        arriba = [a for a, e in zip(arriba, elevar_k) if e]
    extra = elevar(np.zeros((len(X), 2)), h, cruces, arriba)[:, 2] - R
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
                      buscar=lambda Y: _buscar(Y, h, sobre, poste), medir=_medir(paso.n, poste))


def _medir(n: int, poste: Poste | Tablon | Cornamusa | Parado):
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
    poste = sobre_superficie(anfitrion)
    X, h, _, sobre = _curva(paso, poste)
    if len(X) != len(final.puntos) or h != final.h:
        raise ValueError(f"Paso {paso.n}: el paso construido no es el de la especificación.")

    def buscar(Y, hY, u):
        return _buscar(Y, hY, sobre[np.clip(np.round(u / h).astype(int), 0, len(sobre) - 1)], poste)

    return apretar(final, paso.secuencia, rondas=rondas, anfitrion=poste,
                   gravedad=lambda Y: poste.cilindricas(Y)[2] > poste.rb + DISTANCIA_SIN_GRAVEDAD,
                   buscar=buscar, medir=_medir(paso.n, poste), registro=registro)


# --------------------------------------------------------------------------
# Curva
# --------------------------------------------------------------------------
def _curva(paso: Paso, poste: Poste | Tablon | Cornamusa):
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
def _cruces(X, h, sobre, poste: Poste | Tablon) -> tuple[list[Cruce], list[tuple[float, float]]]:
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

