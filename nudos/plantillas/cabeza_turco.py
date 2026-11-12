"""Plantilla de la cabeza de turco, tejida sobre un tubo (anfitrión «tubo»).

El método es el del diseño de T8 en tasks/plan.md: la cuerda se teje vuelta por vuelta, y
cada vuelta pasa por encima o por debajo de lo que ya está, como queda en el nudo terminado.
Da tantas vueltas al tubo como cabos y hace tantos senos en cada borde como senos. Cada
pasada más sigue el mismo camino junto a la primera, y al final los dos extremos se esconden
bajo la banda de al lado (el remate).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..cruces import cruces_2d
from .trazo import TrazoDePaso

# Las medidas que acepta la plantilla, en letras. Solo las pasadas pueden ser una («una
# pasada»); cabos y senos empiezan en dos.
NUMEROS = {1: "una", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete"}
CABOS = (2, 5)
SENOS = (2, 7)
PASADAS = (1, 3)
_CAMPOS = {"tipo", "cabos", "senos", "pasadas"}


@dataclass(frozen=True)
class CabezaDeTurco:
    cabos: int     # vueltas al tubo
    senos: int     # senos en cada borde
    pasadas: int   # veces que la cuerda recorre el mismo camino

    tipo = "cabeza-de-turco"
    ANFITRION = "tubo"
    # Ningún paso tiene firme: el extremo corto se sujeta contra el tubo y se trabaja con la
    # parte larga, que lleva «Chicote» en su punta en todos los pasos.
    CON_FIRME: tuple[str, ...] = ()

    @classmethod
    def leer(cls, datos: dict, falla) -> CabezaDeTurco:
        sobran = set(datos) - _CAMPOS
        if sobran:
            raise falla(f"campos desconocidos: {', '.join(sorted(sobran))}")
        numeros = {}
        for clave, (a, b) in (("cabos", CABOS), ("senos", SENOS), ("pasadas", PASADAS)):
            v = datos.get(clave)
            if not isinstance(v, int) or isinstance(v, bool) or not a <= v <= b:
                raise falla(f"«{clave}» es un número entero de {a} a {b}")
            numeros[clave] = v
        comun = math.gcd(numeros["cabos"], numeros["senos"])
        if comun != 1:
            raise falla(f"con {numeros['cabos']} cabos y {numeros['senos']} senos salen {comun} "
                        "cuerdas cerradas y no un nudo de una sola cuerda: cabos y senos no "
                        "pueden tener un divisor común aparte del 1")
        return cls(**numeros)

    @property
    def VARIANTES(self) -> dict[str, str]:
        """El error común que sabe construir, con el primer hito desde el que se ve: en la
        tercera vuelta, la cuerda empieza a tejer por encima en vez de por debajo y sigue
        alternando. Es el error del método de tres cabos, donde la segunda vuelta va toda por
        encima y la tercera empieza por debajo, sean cuantos sean los senos (2, 4, 5 o 7).
        Con otro número de cabos la segunda vuelta ya alterna, y no hay variante."""
        if self.cabos != 3 or por_vuelta(self.cabos, self.senos)[2][0]:
            return {}
        return {"empieza-por-encima": "vuelta-3-mitad"}

    def hitos(self) -> dict[str, int]:
        """Los valores de `hasta`, con su posición en la cuerda: la primera pasada por medias
        vueltas, cada pasada más por mitades y el remate. `vueltas` es lo mismo que la última
        vuelta y `pasadas` que la última pasada (con una sola, la última vuelta)."""
        out, k = {}, -1
        for i in range(1, self.cabos + 1):
            for nombre in (f"vuelta-{i}-mitad", f"vuelta-{i}"):
                k += 1
                out[nombre] = k
        out["vueltas"] = k
        for i in range(2, self.pasadas + 1):
            for nombre in (f"pasada-{i}-mitad", f"pasada-{i}"):
                k += 1
                out[nombre] = k
        out["pasadas"] = k
        out["remate"] = k + 1
        return out

    def medidas(self) -> dict[str, str]:
        return {"cabos": NUMEROS[self.cabos], "senos": NUMEROS[self.senos],
                "pasadas": NUMEROS[self.pasadas]}


# --------------------------------------------------------------------------
# El camino del centro
# --------------------------------------------------------------------------
def cruces_del_centro(cabos: int, senos: int, P: float = 1.0) -> list[tuple[float, float]]:
    """Los cruces del camino del centro de un cabo, cerrado, en la superficie desenrollada del
    tubo: para cada uno, dónde pasa la cuerda por primera y por segunda vez (t1 < t2), a lo
    largo del camino desde el ápice de un seno. P es el periodo de la onda; una vuelta al tubo
    mide P · senos / cabos, y la cuerda da tantas vueltas como cabos.

    Dos pasadas se cruzan donde están a la misma altura del tubo en el mismo lugar alrededor:
    a m vueltas una de otra (t2 = t1 + m vueltas). Como la onda es simétrica respecto de cada
    ápice y cambia de signo cada media onda, eso pasa donde t1 ≡ −d/2 (mód P/2), con d el
    corrimiento de la onda en m vueltas. No depende de la forma de la onda, y ningún cruce
    cae a menos de P / (2 · cabos) de un ápice. Son senos × (cabos − 1)."""
    vuelta = P * senos / cabos
    out = []
    for m in range(1, cabos):
        t = (-((m * vuelta) % P) / 2) % (P / 2)
        while t < (cabos - m) * vuelta - 1e-9:
            out.append((t, t + m * vuelta))
            t += P / 2
    return sorted(out)


def encima_del_centro(cabos: int, senos: int, P: float = 1.0) -> list[tuple[float, bool, int]]:
    """Las pasadas del camino del centro por sus cruces, en orden: (dónde, si va por encima,
    índice del cruce en cruces_del_centro). Alternan encima y debajo a lo largo de la cuerda;
    de las dos formas de alternar, la del método: el primer cruce que forma la segunda vuelta
    (el de su primera pasada por encima de lo que ya está) va por encima. Así, con tres cabos,
    la segunda vuelta va toda por encima de la primera."""
    cruces = cruces_del_centro(cabos, senos, P)
    vuelta = P * senos / cabos
    pasadas = sorted([(t1, k) for k, (t1, _) in enumerate(cruces)]
                     + [(t2, k) for k, (_, t2) in enumerate(cruces)])
    _, primero = min((t2, k) for k, (_, t2) in enumerate(cruces)
                     if numero_de_vuelta(t2, vuelta) == 2)
    fase = next(i for i, (t, k) in enumerate(pasadas) if k == primero and t == cruces[k][1]) % 2
    return [(t, i % 2 == fase, k) for i, (t, k) in enumerate(pasadas)]


def numero_de_vuelta(t: float, vuelta: float) -> int:
    """En qué vuelta, desde 1, está el punto t del camino. La vuelta k termina justo al volver
    al lugar donde empezó (t = k vueltas, incluido): con algunas medidas hay cruces
    exactamente ahí, y son de la vuelta que termina."""
    return max(1, math.ceil(t / vuelta - 1e-9))


def por_vuelta(cabos: int, senos: int) -> list[list[bool]]:
    """Para cada vuelta de la primera pasada, si va por encima en cada cruce que forma, en
    orden: los cruces que esa vuelta hace con lo que ya está."""
    cruces = cruces_del_centro(cabos, senos)
    vuelta = senos / cabos
    out = [[] for _ in range(cabos)]
    for t, arriba, k in encima_del_centro(cabos, senos):
        if t == cruces[k][1]:
            out[numero_de_vuelta(t, vuelta) - 1].append(arriba)
    return out


# --------------------------------------------------------------------------
# La cuerda en el mapa del tubo
# --------------------------------------------------------------------------
# El mapa es la superficie del tubo desenrollada: u, el arco alrededor del tubo a la altura
# donde la cuerda lo toca (rb = radio + 0,5), y x, a lo largo del eje. El seno A, por donde
# salen los dos extremos, es el ápice de un borde en u = 0, x > 0. La cuerda se recorre con T,
# el camino del centro de un cabo desde A (en la primera pasada, T = u), y en cada punto va
# corrida por la normal del centro según su pasada. Ver «Cómo se hizo la geometría» de T8.
CARRIL = 1.1          # entre dos pasadas de un mismo cabo
MESETA = 0.6          # cuánto más allá de la cuerda de abajo sigue arriba la de encima
ANGULOS = (45, 50, 55, 60, 65, 70)   # el de la onda con la dirección en que se rodea el tubo
SEPARACION_IDEAL = 1.0
CURVA_IDEAL = 1.2
PASO_MAPA = 0.05      # cada cuánto de T se traza el cuerpo en el mapa
PASO_CONTROL = 0.3    # cada cuánto se toma un punto de control de la cuerda
CAMARA = 40.0         # la cara del tubo que mira la cámara de los pasos, en grados desde arriba
# El seno A. d es la distancia, alrededor del tubo, del ápice a cada cruce de al lado (P / (2
# cabos)); el seno vecino está a 2d. Lo que sigue se mide desde esos cruces, con dos pasadas;
# con tres, la banda es una pasada más ancha y cada uno se corre ANCHO_EXTRA más lejos del cruce.
TRAS_CRUCE = 0.63     # el cambio de pasada empieza esto después del último cruce antes de A
ANTES_CRUCE = 2.83    # y termina esto antes del primer cruce después de A
ENTRA = 2.03          # el extremo corto entra a la primera pasada esto antes de ese cruce
CHICOTE = 1.13        # el chicote termina esto después del último cruce antes de A
FUERA = 0.9           # el extremo corto llega desde esto por fuera del borde del nudo
ANCHO_EXTRA = 0.8     # cuánto más lejos del cruce va cada uno por cada pasada más de dos
RESTO_LARGO = 3.0     # el resto se aleja del tubo a lo largo de esto, siguiendo la cuerda
RESTO_SUBE = 2.2      # y se aleja esto del tubo antes de rodearlo y caer a la mesa
MESA_LARGO = 6        # puntos (cada 0,5) de lo que sigue por la mesa después de caer


def _suave(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def _largo(M) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(M, axis=0), axis=1))])


class Onda:
    """El camino del centro de un cabo en el mapa: una onda hecha de arcos de circunferencia,
    de un seno al del otro borde en media onda, con un ápice arriba en u = 0. `beta` es el
    ángulo, a media altura, con la dirección en que se rodea el tubo."""

    def __init__(self, p: CabezaDeTurco, rb: float, beta: float):
        self.p, self.rb, self.beta = p, rb, beta
        self.C = 2 * math.pi * rb                 # una vuelta
        self.P = self.C * p.cabos / p.senos       # el periodo
        self.LC = p.cabos * self.C                # una pasada
        self.d = self.P / (2 * p.cabos)           # del ápice al cruce de al lado
        b = math.radians(beta)
        self.rho = (self.P / 4) / math.sin(b)
        self.w = self.rho * (1 - math.cos(b))     # amplitud del centro

    def x(self, T):
        P, rho, w = self.P, self.rho, self.w
        v = np.mod(T, P)
        v = np.where(v > P / 2, P - v, v)
        a = w - rho + np.sqrt(np.maximum(rho ** 2 - v ** 2, 0))
        b = -w + rho - np.sqrt(np.maximum(rho ** 2 - (v - P / 2) ** 2, 0))
        return np.where(v <= P / 4, a, b)

    def pendiente(self, T):
        P, rho = self.P, self.rho
        v = np.mod(T, P)
        signo = np.where(v > P / 2, -1.0, 1.0)
        v = np.where(v > P / 2, P - v, v)
        da = -v / np.sqrt(np.maximum(rho ** 2 - v ** 2, 1e-12))
        db = (v - P / 2) / np.sqrt(np.maximum(rho ** 2 - (v - P / 2) ** 2, 1e-12))
        return signo * np.where(v <= P / 4, da, db)

    def punto(self, T, corrido) -> np.ndarray:
        """El punto del mapa (u, x) a T del centro, corrido por su normal izquierda: con
        corrido > 0 va hacia fuera en los senos de arriba, como el seno A."""
        T = np.asarray(T, float)
        d = self.pendiente(T)
        n = np.hypot(1.0, d)
        c = np.broadcast_to(corrido, T.shape)
        return np.column_stack([T - c * d / n, self.x(T) + c / n])


def carril(k: int, pasadas: int) -> float:
    """Cuánto va corrida la pasada k (desde 1) del centro de su banda: la primera, por fuera
    en el seno A, y cada una más, 1,1 más adentro."""
    return ((pasadas - 1) / 2 - (k - 1)) * CARRIL


TUBO, MESA = 0, 1     # zonas: la parte tejida, sobre el tubo, y lo que cuelga hasta la mesa
PASO_CRUCE = 0.25     # cada cuánto se muestrea la cuerda del mapa para buscar sus cruces
CRUCE_MIN = 3.0       # una cuerda no se cruza consigo misma en menos que esto a lo largo


def _hermite(P0, T0, P1, T1, n: int = 24) -> np.ndarray:
    d = float(np.linalg.norm(P1 - P0))
    t = np.linspace(0.0, 1.0, n)[:, None]
    return ((2 * t ** 3 - 3 * t ** 2 + 1) * P0 + (t ** 3 - 2 * t ** 2 + t) * d * T0
            + (-2 * t ** 3 + 3 * t ** 2) * P1 + (t ** 3 - t ** 2) * d * T1)


def _remuestrear(M, paso: float) -> np.ndarray:
    s = _largo(M)
    n = max(1, int(math.ceil(s[-1] / paso)))
    g = np.linspace(0.0, s[-1], n + 1)
    return np.column_stack([np.interp(g, s, M[:, k]) for k in range(M.shape[1])])


def _unit(v) -> np.ndarray:
    return v / max(float(np.linalg.norm(v)), 1e-12)


def alturas(s, pasadas, forzadas=()) -> tuple[np.ndarray, float]:
    """Cuánto se aleja del tubo cada punto (en diámetros) a lo largo de la cuerda, `s`: 1 en
    la meseta de cada pasada por encima, 0 en la de cada pasada por debajo, y entre una y otra
    una curva suave. `pasadas` son (dónde, si va por encima, |sen| del ángulo del cruce); la
    meseta dura MESETA más allá del eje de la otra cuerda, a lo largo de esta. `forzadas` son
    tramos (desde, hasta, altura). Devuelve también el hueco más corto entre dos mesetas de
    distinta altura: si es negativo, se pisan."""
    tramos = [[sp - MESETA / max(seno, 0.2), sp + MESETA / max(seno, 0.2), 1.0 if arriba else 0.0]
              for sp, arriba, seno in pasadas]
    tramos += [[a, b, v] for a, b, v in forzadas]
    tramos.sort()
    juntos: list[list[float]] = []
    for t in tramos:
        if juntos and t[2] == juntos[-1][2] and t[0] <= juntos[-1][1]:
            juntos[-1][1] = max(juntos[-1][1], t[1])
        else:
            juntos.append(list(t))
    hueco = min((b[0] - a[1] for a, b in zip(juntos, juntos[1:]) if a[2] != b[2]), default=math.inf)
    # Si dos mesetas se pisan, cada una termina en el medio (y el hueco negativo es una falla).
    for a, b in zip(juntos, juntos[1:]):
        if b[0] < a[1]:
            m = (a[1] + b[0]) / 2
            a[1] = b[0] = m
    nodos = np.array([v for t in juntos for v in t[:2]])
    valores = np.array([t[2] for t in juntos for _ in range(2)])
    s = np.asarray(s, float)
    j = np.clip(np.searchsorted(nodos, s, side="right") - 1, 0, len(nodos) - 2)
    a0, a1 = nodos[j], nodos[j + 1]
    f = np.clip((s - a0) / np.maximum(a1 - a0, 1e-9), 0, 1)
    f = 0.5 - 0.5 * np.cos(math.pi * f)
    h = valores[j] * (1 - f) + valores[j + 1] * f
    h = np.where(s <= nodos[0], valores[0], np.where(s >= nodos[-1], valores[-1], h))
    return h, hueco


@dataclass
class _Cruce:
    """Un cruce de la cuerda en el mapa: dónde pasa cada tramo (en T del cuerpo, o None si
    es el extremo corto metido, con su posición a lo largo de él), si la primera pasada va
    por encima y en qué hito se forma."""
    T: tuple[float | None, float | None]
    s_corto: tuple[float | None, float | None]
    seno: float
    encima: bool             # la primera pasada (la de menor posición a lo largo de la cuerda)
    hito: str = ""
    etiqueta: str = ""
    lugar: tuple[float, float] = (0.0, 0.0)   # en el mapa: (x, u)


class Cuerda:
    """La cuerda entera de una cabeza de turco sobre su tubo, calculada una sola vez.

    Va así, en el mapa del tubo: el extremo corto llega desde fuera del nudo, a lo largo del
    tubo, y entra a la primera pasada a media diagonal del brazo que sale del seno A (T = t0),
    lejos de los cruces. Cada pasada da `cabos` vueltas; al volver a A, después de su último
    cruce, la cuerda se corre a la pasada siguiente por dentro del seno, sobre el ápice, antes
    de llegar a donde entra el extremo corto, así que no lo cruza. La última pasada pasa por
    debajo (o por encima) de su último cruce y el chicote termina ahí (T_fin).

    El remate esconde el extremo corto: en vez de colgar, vuelve sobre el ápice de A y se mete
    por debajo de la banda que baja del seno vecino, antes de que cruce el último cruce. Esa
    banda va un poco más arriba desde antes, en todos los pasos: así el extremo corto es lo
    único que cambia en el remate.

    `secuencias` da la secuencia del método hasta cada hito; `hitos_T`, dónde termina cada
    hito a lo largo del cuerpo; `trazo(hito, previo)`, los puntos de control de ese paso."""

    def __init__(self, p: CabezaDeTurco, tubo, beta: float, variante: str | None = None):
        if variante is not None and variante not in p.VARIANTES:
            raise ValueError(f"la cabeza de turco de {p.cabos} cabos no tiene la variante {variante}")
        self.p, self.tubo, self.variante = p, tubo, variante
        o = self.onda = Onda(p, tubo.rb, beta)
        L, q, d, LC = p.cabos, p.pasadas, o.d, o.LC
        extra = ANCHO_EXTRA * max(0, q - 2)
        self.t0 = d - ENTRA - extra
        self.a, self.b = d - TRAS_CRUCE - extra, d - ANTES_CRUCE - extra
        self.T_fin = q * LC - d + CHICOTE + extra
        self.borde = o.w + (q - 1) / 2 * CARRIL + 0.5   # el borde del nudo en el ápice de A
        T = np.arange(self.t0, self.T_fin, PASO_MAPA)
        self._T = np.append(T, self.T_fin)
        self._M = o.punto(self._T, self.corrido(self._T))
        self._s = _largo(self._M)
        self.alias = {"vueltas": f"vuelta-{L}", "pasadas": f"pasada-{q}" if q > 1 else f"vuelta-{L}"}
        self.hitos_T = self._hitos()
        self._cuelga, self._cuelga_fuera = self._extremo_que_cuelga()
        self._metido = self._extremo_metido()
        self.cruces = self._cruces()
        self.secuencias = self._secuencias()

    # --- El cuerpo ----------------------------------------------------------
    def corrido(self, T) -> np.ndarray:
        """Cuánto va corrida la cuerda, a T, del centro de su banda: el carril de su pasada, y
        entre una pasada y la siguiente, un paso suave de un carril al otro."""
        T = np.asarray(T, float)
        q, LC = self.p.pasadas, self.onda.LC
        out = np.full(T.shape, carril(1, q))
        for k in range(1, q):
            f = _suave((T - (k * LC - self.a)) / (self.a + self.b))
            out = out + f * (carril(k + 1, q) - carril(k, q))
        return out

    def en_T(self, T) -> np.ndarray:
        """Los puntos del cuerpo en el mapa, (u, x), a T."""
        T = np.atleast_1d(np.asarray(T, float))
        return self.onda.punto(T, self.corrido(T))

    def _hitos(self) -> dict[str, float]:
        """Dónde termina cada hito, en T. Las medias vueltas y las vueltas terminan entre dos
        pasadas por cruces, en el medio: en un ápice o a media diagonal. Una vuelta llega hasta
        volver al lugar donde empezó, incluido. Cada pasada, menos la última, termina donde
        empieza el paso a la siguiente; la última, a media diagonal antes de su último cruce, y
        el remate, en la punta del chicote."""
        p, o = self.p, self.onda
        L, q, C, LC, d = p.cabos, p.pasadas, o.C, o.LC, o.d
        centro = sorted(t for c in cruces_del_centro(L, p.senos, o.P) for t in c)
        todas = np.array([t + k * LC for k in range(q) for t in centro])

        def entre(objetivo: float) -> float:
            a = todas[todas <= objetivo + 1e-6].max()
            return float((a + todas[todas > a + 1e-6].min()) / 2)

        out: dict[str, float] = {}
        for k in range(1, L + 1):
            out[f"vuelta-{k}-mitad"] = entre((k - 0.5) * C)
            if k < L:
                out[f"vuelta-{k}"] = entre(k * C)
        out[f"vuelta-{L}"] = LC - self.a if q > 1 else LC - 1.5 * d
        for k in range(2, q + 1):
            out[f"pasada-{k}-mitad"] = entre((k - 0.5) * LC)
            out[f"pasada-{k}"] = k * LC - self.a if k < q else q * LC - 1.5 * d
        out["remate"] = self.T_fin
        return out

    def T_de(self, hito: str) -> float:
        return self.hitos_T[self.alias.get(hito, hito)]

    # --- Los extremos cortos ---------------------------------------------------
    def _extremo_que_cuelga(self) -> tuple[np.ndarray, int]:
        """El extremo corto de los pasos antes del remate, en el mapa, desde fuera del nudo
        hasta antes de t0: llega a lo largo del tubo y entra a la primera pasada en t0.
        Devuelve los puntos y cuántos del principio van fuera del nudo (en la zona de la mesa)."""
        E0, d0 = self._M[0], _unit(self._M[1] - self._M[0])
        Q0 = np.array([self.t0 - 1.2, self.borde + FUERA])
        curva = _hermite(Q0, np.array([0.0, -1.0]), E0, d0, n=30)[:-1]
        recta = np.column_stack([np.full(9, Q0[0]), np.linspace(Q0[1] + 2.4, Q0[1], 9)])[:-1]
        return np.vstack([recta, curva]), len(recta)

    def _extremo_metido(self) -> np.ndarray:
        """El extremo corto del remate, en el mapa, desde su punta hasta antes de t0: se mete
        por debajo de la banda que baja del seno vecino (el de antes de A, en u = -2d) y sale
        por encima del borde del nudo, sobre el ápice de A, hasta t0."""
        from ..libre import catmull_rom
        o, q, d = self.onda, self.p.pasadas, self.onda.d
        E0, d0 = self._M[0], _unit(self._M[1] - self._M[0])
        # La banda que baja del seno vecino, a media distancia entre su ápice y el cruce.
        centro = o.punto(np.array([0.5 * d]), 0.0)[0] + np.array([-2 * d, 0.0])
        ida = _unit(np.array([-0.58, -0.81]))       # cómo cruza la banda: hacia abajo y atrás
        mitad = (q - 1) / 2 * CARRIL
        punta = centro + ida * (mitad + 1.0)
        antes = centro - ida * (mitad + 1.7)
        arriba = np.array([-d - 0.2, self.borde + 0.55])
        apice = np.array([self.t0 - 1.5, self.borde + 0.45])
        P = np.array([punta, centro, antes, arriba, apice, E0, E0 + 0.6 * d0])
        D, ctrl = catmull_rom(P)
        return D[:ctrl[5]]

    # --- Los cruces ------------------------------------------------------------
    def _cruces(self) -> list[_Cruce]:
        """Los cruces de la cuerda del remate en el mapa, con su encima/debajo y su etiqueta.

        Entre dos tramos del cuerpo, cada pasada hace lo que hace la pasada del centro de su
        cabo en ese cruce: así alternan por cabos a lo largo de la cuerda, y cada pasada más va
        por encima donde la primera va por encima. El extremo corto metido va por debajo. Las
        etiquetas siguen el orden en que se forma cada cruce: el hito que lo forma y, dentro
        del hito, dónde pasa la cuerda que lo forma; los del remate, primero los del chicote."""
        o, p = self.onda, self.p
        corto = self._metido
        M = np.vstack([corto, self._M])
        es_corto = np.r_[np.ones(len(corto)), np.zeros(len(self._M))]
        s = _largo(M)
        s_cuerpo0 = s[len(corto)]
        n = max(2, int(math.ceil(s[-1] / PASO_CRUCE)))
        g = np.linspace(0.0, s[-1], n + 1)
        Q = np.column_stack([np.interp(g, s, M[:, 1]), np.interp(g, s, M[:, 0])])   # (x, u)
        paso = g[1] - g[0]

        def T_de_s(v: float) -> float:
            return float(np.interp(v - s_cuerpo0, self._s, self._T))

        pasadas = encima_del_centro(p.cabos, p.senos, o.P)
        tc = np.array([t for t, _, _ in pasadas])
        oc = np.array([e for _, e, _ in pasadas])
        if self.variante == "empieza-por-encima":
            # En la tercera vuelta, la cuerda empieza a tejer por encima: todos los cruces que
            # forma esa vuelta quedan al revés.
            del_centro = cruces_del_centro(p.cabos, p.senos, o.P)
            tercera = {k for k, (_, t2) in enumerate(del_centro) if numero_de_vuelta(t2, o.C) == 3}
            oc = np.array([(not e) if k in tercera else e for _, e, k in pasadas])

        def encima_en(T: float) -> bool:
            dist = np.abs(((T % o.LC) - tc + o.LC / 2) % o.LC - o.LC / 2)
            return bool(oc[int(dist.argmin())])

        orden = [h for h in self.p.hitos() if h not in self.alias]
        pos = {h: k for k, h in enumerate(orden)}
        out = []
        for sa, sb, seno, (x, u) in cruces_2d(Q, np.ones(len(Q) - 1, bool), paso, periodo=o.C):
            ca = bool(np.interp(sa, s, es_corto) > 0.5)
            cb = bool(np.interp(sb, s, es_corto) > 0.5)
            if ca and cb:
                raise ValueError("el extremo corto metido se cruza consigo mismo")
            Ta = None if ca else T_de_s(sa)
            Tb = T_de_s(sb)
            if ca:
                arriba, hito, forma = False, "remate", (1, sa)
            else:
                arriba = encima_en(Ta)
                if arriba == encima_en(Tb):
                    raise ValueError(f"el cruce de T = {Ta:.1f} y {Tb:.1f} tiene las dos pasadas "
                                     "del mismo lado")
                hito = next(h for h in orden if self.hitos_T[h] >= Tb - 1e-9)
                forma = (0, Tb)
            c = _Cruce(T=(Ta, Tb), s_corto=(sa - s_cuerpo0 if ca else None, None), seno=seno,
                       encima=arriba, hito=hito, lugar=(x, u % o.C))
            out.append((pos[hito], forma, c))
        out.sort(key=lambda t: (t[0], t[1]))
        for k, (_, _, c) in enumerate(out, 1):
            c.etiqueta = str(k)
        return [c for _, _, c in out]

    def _secuencias(self) -> dict[str, tuple[str, ...]]:
        """La secuencia del método hasta cada hito: las pasadas por los cruces ya formados, en
        el orden de la cuerda de ese paso. En el remate, el extremo corto metido va primero."""
        orden = [h for h in self.p.hitos() if h not in self.alias]
        out = {}
        for k, hito in enumerate(orden):
            pasadas = []
            for c in self.cruces:
                if orden.index(c.hito) > k:
                    continue
                for i, (T, sc) in enumerate(zip(c.T, c.s_corto)):
                    arriba = c.encima if i == 0 else not c.encima
                    clave = (0, sc) if T is None else (1, T)
                    pasadas.append((clave, c.etiqueta + ("O" if arriba else "U")))
            out[hito] = tuple(t for _, t in sorted(pasadas))
        for alias, hito in self.alias.items():
            out[alias] = out[hito]
        return out

    # --- Las alturas -------------------------------------------------------------
    def _cuerda_del_mapa(self, metido: bool) -> tuple[np.ndarray, np.ndarray, float]:
        """La cuerda de los pasos (con el extremo corto que cuelga) o la del remate (con el
        extremo corto metido), en el mapa, fina: los puntos, su largo a lo largo de la cuerda y
        dónde empieza el cuerpo (t0)."""
        corto = self._metido if metido else self._cuelga
        M = np.vstack([corto, self._M])
        s = _largo(M)
        return M, s, float(s[len(corto)])

    def alturas(self, metido: bool) -> tuple[np.ndarray, float]:
        """Cuánto se aleja del tubo cada punto de _cuerda_del_mapa(metido), y el hueco más corto
        entre dos mesetas. La banda que tapa al extremo corto metido va por encima también en
        los pasos sin él, así que el cuerpo es el mismo en todos los pasos; el extremo corto va
        apoyado en el tubo hasta un diámetro antes de entrar a la primera pasada."""
        M, s, s0 = self._cuerda_del_mapa(metido)
        s_de_T = lambda T: s0 + float(np.interp(T, self._T, self._s))
        pasadas = []
        for c in self.cruces:
            for i, (T, sc) in enumerate(zip(c.T, c.s_corto)):
                arriba = c.encima if i == 0 else not c.encima
                if T is not None:
                    pasadas.append((s_de_T(T), arriba, c.seno))
                elif metido:
                    pasadas.append((s0 + sc, arriba, c.seno))
        return alturas(s, pasadas, forzadas=[(-1.0, s0 - 1.0, 0.0)])

    # --- Un paso -------------------------------------------------------------------
    def giro(self, hito: str, previo: str | None) -> float:
        """Cuánto se gira el nudo en este paso, en grados, para que lo que agrega, o su última
        media vuelta si es más largo, quede de frente a la cámara. En el remate, lo que se
        esconde: desde la punta del extremo corto metido hasta la del chicote."""
        o = self.onda
        if self.alias.get(hito, hito) == "remate":
            u = np.r_[self._metido[:, 0], self.en_T([self.T_fin])[:, 0] - (self.p.pasadas - 1) * o.LC]
            u = (u + o.C / 2) % o.C - o.C / 2
            centro = (u.min() + u.max()) / 2
        else:
            b = self.T_de(hito)
            a = self.t0 if previo is None else self.T_de(previo)
            a = max(a, b - o.C / 2)
            centro = (a + b) / 2
        return (CAMARA + math.degrees(centro / o.rb) + 180.0) % 360.0 - 180.0

    def mundo(self, M, h, giro: float) -> np.ndarray:
        """Del mapa (u, x) y la altura sobre el tubo a la mesa, con el nudo girado `giro`."""
        th = np.radians(giro) - M[:, 0] / self.onda.rb
        r = self.tubo.rb + h
        return np.column_stack([M[:, 1], -r * np.sin(th), self.tubo.zc + r * np.cos(th)])

    def trazo(self, hito: str, previo: str | None) -> TrazoDePaso:
        """Los puntos de control del paso que llega hasta `hito`, girado para que lo que agrega
        quede de frente. Es el comienzo de la cuerda hasta el hito, con el extremo corto que
        cuelga hasta la mesa y el resto, que sale del nudo y cae a la mesa detrás del tubo. En el
        remate, la cuerda entera con el extremo corto metido."""
        remate = self.alias.get(hito, hito) == "remate"
        g = self.giro(hito, previo)
        Th = self.T_de(hito)
        Ts = [Th] + ([] if previo is None else [self.T_de(previo)])
        T = np.unique(np.r_[np.arange(self.t0, Th, 0.15), Ts])
        M, s, s0 = self._cuerda_del_mapa(remate)
        h, _ = self.alturas(remate)
        corto = M[:int(np.searchsorted(s, s0 - 1e-9)) + 1]   # hasta t0, incluido
        Mc = _remuestrear(corto, PASO_CONTROL)[:-1]
        s_corto = _largo(Mc)
        Mb = self.en_T(T)
        sb = s0 + np.interp(T, self._T, self._s)
        hc = np.interp(s_corto, s, h)
        hb = np.interp(sb, s, h)
        X = np.vstack([self.mundo(Mc, hc, g), self.mundo(Mb, hb, g)])
        Z = np.full(len(X), TUBO)
        if not remate:
            fuera = int(np.searchsorted(s_corto, s[self._cuelga_fuera - 1] + 1e-9))
            Z[:fuera] = MESA
            cuelga = self._colgar(X[0])
            resto = self._resto(X[-1], _unit(X[-1] - X[-2]))
            X = np.vstack([cuelga, X, resto])
            Z = np.r_[np.full(len(cuelga), MESA), Z, np.full(len(resto), MESA)]
        else:
            cuelga = np.empty((0, 3))
        n0 = len(cuelga) + len(Mc)
        fin = n0 + int(np.searchsorted(T, Th - 1e-9))
        inicio = None if previo is None else n0 + int(np.searchsorted(T, self.T_de(previo) - 1e-9))
        return TrazoDePaso(X, Z, fin, inicio, g)

    def _cilindricas(self, P) -> tuple[float, float, float]:
        """x, ángulo (0 arriba, π/2 hacia quien ata) y distancia al eje de un punto."""
        tubo = self.tubo
        return float(P[0]), math.atan2(-P[1], P[2] - tubo.zc), float(np.hypot(P[1], P[2] - tubo.zc))

    def _en(self, x, th, r) -> np.ndarray:
        return np.array([x, -r * math.sin(th), self.tubo.zc + r * math.cos(th)])

    def _bajar(self, Q, th: float) -> list[np.ndarray]:
        """Desde Q, en un costado del tubo (en el ángulo th), cae a la mesa en un cuarto de
        circunferencia que se aleja del tubo, y sigue por la mesa. No cae derecho: vista desde
        arriba, una caída vertical es un solo punto, y ahí se confunden los cruces."""
        afuera = np.array([0.0, -math.copysign(1.0, math.sin(th)), 0.0])
        radio = max(0.6, float(Q[2]) - 0.5)
        c = np.asarray(Q, float) + radio * afuera      # a la altura de Q, hacia afuera
        pasos = max(4, int(radio * math.pi / 2 / PASO_CONTROL) + 1)
        out = [c - radio * math.cos(a) * afuera - np.array([0.0, 0.0, radio * math.sin(a)])
               for a in np.linspace(0, math.pi / 2, pasos)[1:]]
        fin = out[-1]
        return out + [fin + 0.5 * k * afuera for k in range(1, MESA_LARGO + 1)]

    def _resto(self, P, llega) -> np.ndarray:
        """Lo que sigue de la cuerda después del hito, que sale del nudo y cae a la mesa: sigue
        como venía por la superficie mientras se aleja del tubo (RESTO_SUBE en RESTO_LARGO),
        lo rodea por fuera hacia atrás, en el sentido en que se teje, y cae detrás del tubo."""
        x, th, r = self._cilindricas(P)
        # Dirección por la superficie: a lo largo del eje y alrededor (en radianes por diámetro).
        e_th = np.array([0.0, -math.cos(th), -math.sin(th)])
        vx, vth = float(llega[0]), float(np.dot(llega, e_th))
        n = math.hypot(vx, vth)
        vx, vth = vx / n, vth / n
        out = []
        for f in np.linspace(0, 1, 11)[1:]:
            out.append(self._en(x + vx * RESTO_LARGO * f, th + vth * RESTO_LARGO * f / r,
                                r + RESTO_SUBE * float(_suave(f))))
        x2, th2, r2 = self._cilindricas(out[-1])
        # Rodea el tubo hacia atrás (ángulo -π/2), por el camino que sigue la cuerda.
        sentido = -1.0 if vth <= 0 else 1.0
        meta = th2 + sentido * ((sentido * (-math.pi / 2 - th2)) % (2 * math.pi))
        if abs(meta - th2) > math.pi * 1.5:     # ya pasó el costado: no da otra vuelta
            meta = th2
        pasos = max(2, int(abs(meta - th2) * r2 / PASO_CONTROL) + 1)
        out += [self._en(x2, a, r2) for a in np.linspace(th2, meta, pasos)[1:]]
        return np.array(out + self._bajar(out[-1], meta))

    def _colgar(self, P) -> np.ndarray:
        """El extremo corto, desde la mesa hasta donde llega al nudo a lo largo del tubo (P), en
        el orden de la cuerda. Se arma desde P hacia afuera: si P está en la mitad de arriba del
        tubo, gira suave por la superficie hacia el costado que baja, lo rodea hasta ese costado
        y cae a la mesa; si está en la de abajo, sigue a lo largo del tubo mientras baja."""
        x, th, r = self._cilindricas(P)
        out = []
        if abs(th) < math.pi / 2:
            sentido = 1.0 if th >= 0 else -1.0
            R = 1.5
            for a in np.linspace(0, math.pi / 2, 7)[1:]:
                out.append(self._en(x + R * math.sin(a), th + sentido * R * (1 - math.cos(a)) / r, r))
            x2, th2, _ = self._cilindricas(out[-1])
            meta = sentido * math.pi / 2
            pasos = max(2, int(abs(meta - th2) * r / PASO_CONTROL) + 1)
            out += [self._en(x2, a, r) for a in np.linspace(th2, meta, pasos)[1:]]
            out += self._bajar(out[-1], meta)
        else:
            P = np.asarray(P, float)
            baja = float(P[2]) - 0.5
            largo = max(2.5, 1.2 * baja)
            for f in np.linspace(0, 1, max(4, int(largo / PASO_CONTROL) + 1))[1:]:
                out.append(P + np.array([largo * f, 0.0, -baja * float(_suave(f))]))
            out += [out[-1] + np.array([0.5 * k, 0.0, 0.0]) for k in range(1, MESA_LARGO + 1)]
        return np.array(out[::-1])

    def buscar(self, X, h: float, zonas, giro: float):
        return buscar_en_el_tubo(X, h, zonas, self.tubo, giro, self.p.senos)


def buscar_en_el_tubo(X, h: float, zonas, tubo, giro: float, senos: int):
    """Los cruces de la cuerda y la altura de sus dos pasadas: sobre el tubo, en su
    superficie desenrollada (encima es lo más lejos del eje), y en la mesa, en la proyección
    de siempre (encima es lo más alto). Entre una zona y la otra no se buscan. Cada cruce del
    tubo guarda su lugar en el mapa del nudo, (x, u), que no cambia al girarlo: con el nudo
    girado `giro` grados, u es el arco alrededor del tubo desde el seno A. Los cruces caen en
    múltiplos de C / (2 senos) alrededor del tubo, así que u da la vuelta a mitad de camino entre
    dos, donde no hay ninguno: así un cruce que se mueve un poco no salta una vuelta.

    Una cuerda no puede cruzarse consigo misma en menos de CRUCE_MIN a lo largo: tendría que
    dar media vuelta más cerrada que el límite de curvatura. Esos pares no cuentan como cruces:
    salen donde la cuerda cae casi vertical al costado del tubo, porque vista desde arriba esa
    caída es casi un punto y, al relajar, se pliega sobre sí misma."""
    from ..cruces import Cruce
    s = np.arange(len(X)) * h
    x, th, r = tubo.cilindricas(X)
    u = np.unwrap(th) * tubo.rb
    C = 2 * math.pi * tubo.rb
    cruces, alturas_ = [], []
    en_tubo = (zonas[:-1] == TUBO) & (zonas[1:] == TUBO)
    for sa, sb, seno, _ in cruces_2d(np.column_stack([x, u]), en_tubo, h, periodo=C):
        if sb - sa < CRUCE_MIN:
            continue
        tha = float(np.interp(sa, s, np.unwrap(th)))
        corte = C / (4 * senos)
        u_a = (math.radians(giro) - tha) * tubo.rb
        lugar = (float(np.interp(sa, s, x)), float((u_a - corte) % C + corte))
        cruces.append(Cruce(sa, sb, lugar, seno))
        alturas_.append((float(np.interp(sa, s, r)), float(np.interp(sb, s, r))))
    en_mesa = (zonas[:-1] == MESA) & (zonas[1:] == MESA)
    for sa, sb, seno, p in cruces_2d(X[:, :2], en_mesa, h):
        if sb - sa < CRUCE_MIN:
            continue
        cruces.append(Cruce(sa, sb, p, seno))
        alturas_.append((float(np.interp(sa, s, X[:, 2])), float(np.interp(sb, s, X[:, 2]))))
    orden = sorted(range(len(cruces)), key=lambda k: cruces[k].sa)
    return [cruces[k] for k in orden], [alturas_[k] for k in orden]


# --------------------------------------------------------------------------
# Los cruces en el mapa, rápido, y la cuerda ideal
# --------------------------------------------------------------------------
def cruces_del_mapa(Q, h: float, periodo: float, validos=None):
    """Como nudos.cruces.cruces_2d, para una polilínea larga del mapa, (x, u) con u periódico:
    solo compara los segmentos que están cerca, con un árbol, en vez de todos con todos."""
    from scipy.spatial import cKDTree
    n = len(Q) - 1
    validos = np.ones(n, bool) if validos is None else validos
    A, B = Q[:-1], Q[1:]
    medio = (A + B) / 2
    x0 = float(medio[:, 0].min()) - 1.0
    caja = [float(medio[:, 0].max()) - x0 + 10.0, periodo]
    datos = np.column_stack([medio[:, 0] - x0, np.mod(medio[:, 1], periodo)])
    largo = float(np.linalg.norm(B - A, axis=1).max())
    pares = cKDTree(datos, boxsize=caja).query_pairs(largo * 1.01 + 1e-9, output_type="ndarray")
    if not len(pares):
        return []
    i, j = np.minimum(pares[:, 0], pares[:, 1]), np.maximum(pares[:, 0], pares[:, 1])
    ok = (j - i >= 2) & validos[i] & validos[j]
    i, j = i[ok], j[ok]
    Ai, Bi, Aj, Bj = A[i], B[i], A[j].copy(), B[j].copy()
    corr = np.round(((Aj[:, 1] + Bj[:, 1]) - (Ai[:, 1] + Bi[:, 1])) / 2 / periodo) * periodo
    Aj[:, 1] -= corr
    Bj[:, 1] -= corr
    rr, ss, qp = Bi - Ai, Bj - Aj, Aj - Ai
    rxs = rr[:, 0] * ss[:, 1] - rr[:, 1] * ss[:, 0]
    nz = np.abs(rxs) > 1e-12
    t = np.full(len(i), -1.0)
    v = np.full(len(i), -1.0)
    t[nz] = (qp[nz, 0] * ss[nz, 1] - qp[nz, 1] * ss[nz, 0]) / rxs[nz]
    v[nz] = (qp[nz, 0] * rr[nz, 1] - qp[nz, 1] * rr[nz, 0]) / rxs[nz]
    hit = nz & (t >= 0) & (t < 1) & (v >= 0) & (v < 1)
    out = []
    for k in np.nonzero(hit)[0][np.argsort((i + t)[hit])]:
        sa, sb = (i[k] + t[k]) * h, (j[k] + v[k]) * h
        if any(abs(a - sa) < 0.3 and abs(b - sb) < 0.3 for a, b, _, _ in out):
            continue
        seno = abs(rxs[k]) / (np.linalg.norm(rr[k]) * np.linalg.norm(ss[k]))
        p = Ai[k] + t[k] * rr[k]
        out.append((float(sa), float(sb), float(seno), (float(p[0]), float(p[1]))))
    return out


def medir_ideal(p: CabezaDeTurco, rb: float, beta: float) -> tuple[float, float]:
    """La separación y el radio de curvatura más chicos de la cuerda ideal: las pasadas
    cerradas, cada una en su carril, sin los extremos, con sus alturas en cada cruce."""
    from scipy.spatial import cKDTree
    o = Onda(p, rb, beta)
    q = p.pasadas
    T = np.arange(0.0, o.LC, 0.1)
    lazos = [o.punto(T, carril(k, q)) for k in range(1, q + 1)]
    # Cada lazo, cerrado y muestreado parejo a lo largo de sí mismo.
    muestras = []
    for M in lazos:
        Mc = np.vstack([M, M[:1] + np.array([o.LC, 0.0])])
        s = _largo(Mc)
        n = int(math.ceil(s[-1] / PASO_CRUCE))
        g = np.linspace(0, s[-1], n + 1)
        muestras.append((np.column_stack([np.interp(g, s, Mc[:, 0]), np.interp(g, s, Mc[:, 1])]),
                         np.interp(g, s, np.r_[T, o.LC]), g))
    Q = np.vstack([m for m, _, _ in muestras])
    Tq = np.concatenate([t for _, t, _ in muestras])
    corte = np.cumsum([len(m) for m, _, _ in muestras])
    validos = np.ones(len(Q) - 1, bool)
    validos[corte[:-1] - 1] = False
    paso = PASO_CRUCE   # aproximado: el largo de cada tramo es parejo dentro de cada lazo
    pasadas_c = encima_del_centro(p.cabos, p.senos, o.P)
    tc = np.array([t for t, _, _ in pasadas_c])
    oc = np.array([e for _, e, _ in pasadas_c])

    def encima_en(t):
        d = np.abs(((t % o.LC) - tc + o.LC / 2) % o.LC - o.LC / 2)
        return bool(oc[int(d.argmin())])
    por_lazo = [[] for _ in lazos]
    inicio = np.r_[0, corte[:-1]]
    for sa, sb, seno, _ in cruces_del_mapa(Q[:, [1, 0]], paso, o.C, validos):
        for sv in (sa, sb):
            k = int(np.searchsorted(corte, sv / paso, side="right"))
            i = sv / paso - inicio[k]
            t = float(np.interp(i, np.arange(len(muestras[k][1])), muestras[k][1]))
            s = float(np.interp(i, np.arange(len(muestras[k][2])), muestras[k][2]))
            por_lazo[k].append((s, encima_en(t), seno))
    X = []
    for k, (Mk, _, g) in enumerate(muestras):
        S = g[-1]
        pas = [(s + d, e, sn) for s, e, sn in por_lazo[k] for d in (-S, 0.0, S)]
        hk, _ = alturas(g, pas)
        th = -Mk[:, 0] / rb
        r = rb + hk
        X.append(np.column_stack([Mk[:, 1], -r * np.sin(th), r * np.cos(th)])[:-1])
    sep = math.inf
    radio = math.inf
    todos = np.vstack(X)
    cual = np.concatenate([np.full(len(x), k) for k, x in enumerate(X)])
    indice = np.concatenate([np.arange(len(x)) for x in X])
    largo_lazo = np.array([len(x) for x in X])
    pares = cKDTree(todos).query_pairs(1.3, output_type="ndarray")
    if len(pares):
        a, b = pares[:, 0], pares[:, 1]
        dist_a_lo_largo = np.abs(indice[a] - indice[b])
        dist_a_lo_largo = np.minimum(dist_a_lo_largo, largo_lazo[cual[a]] - dist_a_lo_largo)
        lejos = (cual[a] != cual[b]) | (dist_a_lo_largo * PASO_CRUCE > 1.6)
        if lejos.any():
            sep = float(np.linalg.norm(todos[a[lejos]] - todos[b[lejos]], axis=1).min())
    for x in X:
        t_ = np.diff(np.vstack([x, x[:1]]), axis=0)
        t_ /= np.linalg.norm(t_, axis=1)[:, None]
        ang = np.arccos(np.clip((t_ * np.roll(t_, -2, axis=0)).sum(1), -1, 1))
        radio = min(radio, float(1 / max((ang / (2 * PASO_CRUCE)).max(), 1e-9)))
    return sep, radio


def elegir_angulo(p: CabezaDeTurco, radio: float) -> float:
    """El ángulo de la onda: el menor entre 45° y 70°, de 5 en 5, con el que la cuerda ideal
    queda a SEPARACION_IDEAL de las demás y con un radio de curvatura de al menos CURVA_IDEAL.
    Si no cabe con ninguno, la falla dice el radio mínimo para esas medidas: se prueba, no se
    extrapola, porque no siempre crece con el radio."""
    from ..libre import TrazadoError
    for beta in ANGULOS:
        sep, curva = medir_ideal(p, radio + 0.5, beta)
        if sep >= SEPARACION_IDEAL - 1e-6 and curva >= CURVA_IDEAL:
            return float(beta)
    r = radio
    while r < radio + 12:
        r += 0.25
        if any(all(v >= lim for v, lim in zip(medir_ideal(p, r + 0.5, b), (SEPARACION_IDEAL - 1e-6, CURVA_IDEAL)))
               for b in ANGULOS):
            break
    medidas = f"{p.cabos} cabos, {p.senos} senos y {NUMEROS[p.pasadas]} pasada" + ("s" if p.pasadas > 1 else "")
    raise TrazadoError(f"La cabeza de turco de {medidas} no cabe en un tubo de radio {radio:g}: "
                       f"con ningún ángulo de {ANGULOS[0]}° a {ANGULOS[-1]}° la cuerda queda a "
                       f"{SEPARACION_IDEAL:g} de las demás y con radio de curvatura de "
                       f"{CURVA_IDEAL:g}. El radio mínimo es {r:g}.")
