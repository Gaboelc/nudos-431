"""Plantillas del amarre redondo y del trípode, sobre palos paralelos (anfitrión «palos»).

El método es el del diseño de «Los palos paralelos» (tanda 4) en tasks/plan.md: un
ballestrinque en el palo de delante, a la izquierda; las vueltas alrededor de todos los palos,
de izquierda a derecha, una junto a otra; los ahorcados de cada hueco entre dos palos,
alrededor de las vueltas (en el trípode, primero el hueco de atrás), y un ballestrinque de
cierre en el palo de delante, a la derecha de los ahorcados.

Los ángulos alrededor de un palo se miden como en nudos/anfitrion.py (Palos): en su plano de
corte (y, z), desde +y hacia arriba; 90° es la cara de arriba y 180° la de delante.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..cruces import Cruce, cruces_2d
from .amarre import NUMEROS, Cuerda, _ballestrinque, _hermite, _resto, _tangente, _unit
from .trazo import COSTADO, HUECO, MESA, PALO, PASO, Trazo

_CAMPOS = {"tipo", "vueltas", "ahorcados"}
# Cuántos ahorcados por hueco acepta la plantilla. Las fuentes llevan dos o tres. Van uno junto
# a otro a lo largo de y, por encima y por debajo de las vueltas, y con cuatro o más se salen del
# hueco, quedan sobre los palos y se tuercen demasiado al bajar por él.
AHORCADOS = (2, 3)

# Medidas en diámetros de cuerda.
PASO_VUELTAS = 1.1   # entre dos vueltas vecinas, y entre dos ahorcados vecinos
SOBRE = 1.1          # cuánto más afuera que las vueltas pasa un ahorcado por encima y por debajo
# Las esquinas de los ahorcados son redondas, de este radio: con menos de 1,1, la relajación las
# corta, y un ahorcado que no abraza nada en su plano se encoge. El primero baja por el hueco a
# AL_LADO de las vueltas, así que su esquina queda a SOBRE de la última vuelta.
RADIO_AHORCADO = 1.6
AL_LADO = RADIO_AHORCADO
CARRIL = 1.1         # entre los carriles de un ballestrinque
SIN_VUELTA = 0.3     # cuánto antes de la cara de arriba de los palos ya va en el hueco un ahorcado
ADELANTE = 2.0       # en el trípode, cuánto más allá del último ahorcado de atrás pasa al otro hueco
GIRO_VUELVE = 90.0   # en cuántos grados alrededor del palo del medio vuelve a la derecha de las vueltas;
                     # con menos, la cuerda que baja al hueco de delante se comprime y se dobla
MAS_ALLA = 1.0       # cuánto sigue por encima de las vueltas el último ahorcado de un hueco
RADIO_HUECO = 6.0    # radio con que se desenrolla un hueco; solo cambia la escala del mapa
RADIO_ESQUINA = 1.3  # radio con que se redondean las esquinas entre dos rectas


@dataclass(frozen=True)
class _Paralelos:
    vueltas: int     # alrededor de todos los palos
    ahorcados: int   # en cada hueco, alrededor de las vueltas

    ANFITRION = "palos"
    PALOS = 2
    # El error común que sabe construir, con el primer hito desde el que se ve: después de las
    # vueltas, la cuerda va directo al ballestrinque de cierre.
    VARIANTES = {"sin-ahorcados": "cierre-1"}
    # Como en el amarre cuadrado: hasta el ballestrinque de inicio, la parte larga es su firme y
    # el extremo corto el chicote; desde la primera vuelta solo hay chicote, en la parte larga.
    CON_FIRME = ("inicio-1", "inicio")

    @classmethod
    def leer(cls, datos: dict, falla):
        sobran = set(datos) - _CAMPOS
        if sobran:
            raise falla(f"campos desconocidos: {', '.join(sorted(sobran))}")
        numeros = {}
        for clave, validos in (("vueltas", tuple(NUMEROS)), ("ahorcados", AHORCADOS)):
            v = datos.get(clave)
            if not isinstance(v, int) or isinstance(v, bool) or v not in validos:
                raise falla(f"«{clave}» es un número entero de {min(validos)} a {max(validos)}")
            numeros[clave] = v
        return cls(**numeros)

    @property
    def total_ahorcados(self) -> int:
        return self.ahorcados * (self.PALOS - 1)

    def alias(self) -> dict[str, str]:
        """Los hitos que son otro nombre de uno de la cuerda."""
        return {"vueltas": f"vuelta-{self.vueltas}", "ahorcados": f"ahorcado-{self.total_ahorcados}"}

    def hitos(self) -> dict[str, int]:
        """Los valores de `hasta`, con su posición en la cuerda. Los alias, como «vueltas»,
        valen lo mismo que el hito al que equivalen."""
        orden = (["inicio-1", "inicio"] + [f"vuelta-{k}" for k in range(1, self.vueltas + 1)]
                 + [f"ahorcado-{k}" for k in range(1, self.total_ahorcados + 1)]
                 + ["cierre-1", "cierre"])
        out = {h: i for i, h in enumerate(orden)}
        for a, h in self.alias().items():
            out[a] = out[h]
        return dict(sorted(out.items(), key=lambda kv: (kv[1], kv[0] in self.alias())))

    def medidas(self) -> dict[str, str]:
        return {"vueltas": NUMEROS[self.vueltas], "ahorcados": NUMEROS[self.ahorcados]}


@dataclass(frozen=True)
class AmarreRedondo(_Paralelos):
    """Dos palos uno junto al otro: vueltas alrededor de los dos y ahorcados en el hueco."""
    tipo = "amarre-redondo"
    PALOS = 2


@dataclass(frozen=True)
class AmarreTripode(_Paralelos):
    """Tres palos uno junto al otro: vueltas alrededor de los tres y ahorcados en los dos
    huecos, primero en el de atrás. `ahorcados` es cuántos van en cada hueco; se numeran a lo
    largo de la cuerda, y `hueco-1` es el último del hueco de atrás."""
    tipo = "amarre-tripode"
    PALOS = 3

    def alias(self) -> dict[str, str]:
        return {**super().alias(), "hueco-1": f"ahorcado-{self.ahorcados}"}


# --------------------------------------------------------------------------
# Las medidas del amarre sobre los palos
# --------------------------------------------------------------------------
def _suave(u) -> float:
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


class Medidas:
    """Dónde va cada parte del amarre a lo largo de los palos, en diámetros.

    Las vueltas van centradas en x = 0. Cada vuelta pasa por encima de los palos en una x y por
    debajo 1,1 más a la derecha: avanza por la cara de atrás del palo de atrás, que no se ve. La
    primera pasa por encima donde sale el firme del ballestrinque de inicio, así que sus «puentes»
    (las rectas que van de un palo a otro por encima o por debajo de un hueco) son: por debajo,
    en T[0] … T[n-1]; por encima, el del firme y T[0] … T[n-2]. El ahorcado j de un hueco baja por
    el hueco a la derecha de las vueltas en R(j) y sube a la izquierda en L(j), y pasa por encima
    y por debajo de ellas a SOBRE, junto a los demás a lo largo de y (delta(j))."""

    def __init__(self, p: _Paralelos, palos):
        self.p, self.pal = p, palos
        self.n, self.m = p.vueltas, p.ahorcados
        self.P = palos.cantidad
        self.rb, self.zc, self.ys, self.huecos = palos.rb, palos.zc, palos.ys, palos.huecos
        self.T = [(k - (self.n - 1) / 2) * PASO_VUELTAS for k in range(self.n)]
        self.zt, self.zb = self.zc + self.rb + SOBRE, self.zc - self.rb - SOBRE
        # Las alturas de los centros de las esquinas de los ahorcados, arriba y abajo.
        self.ze_arriba = self.zt - RADIO_AHORCADO
        self.ze_abajo = self.zb + RADIO_AHORCADO
        # Entre h0 y h1 (la distancia a la altura de los ejes), el ahorcado pasa del medio del
        # hueco a su lugar junto a los demás.
        self.h0, self.h1 = palos.radio - SIN_VUELTA, self.rb + SOBRE
        # El ballestrinque de inicio: el primer carril a 1,1 del ahorcado más afuera.
        c1 = self.L(self.m) - CARRIL
        self.inicio = (c1, c1 - CARRIL, c1 - 2 * CARRIL, c1 - 3 * CARRIL)   # vuelta 1, firme, chicote, vuelta 2
        # El de cierre: su primera vuelta a 1,1 del ahorcado más afuera, y el firme después.
        self.x_cierre = self.R(self.m) + 2 * CARRIL
        # Los huecos en el orden en que se ahorcan: el de atrás primero.
        self.orden = tuple(range(self.P - 2, -1, -1))

    def xL(self, j: int) -> float:
        return self.T[0] - (j - 1) * PASO_VUELTAS

    def xR(self, j: int) -> float:
        return self.T[-1] + (j - 1) * PASO_VUELTAS

    def L(self, j: int) -> float:
        return self.xL(j) - AL_LADO

    def R(self, j: int) -> float:
        return self.xR(j) + AL_LADO

    def delta(self, j: int) -> float:
        return (j - (self.m + 1) / 2) * PASO_VUELTAS

    def y_ahorcado(self, z: float, g: int, d: float) -> float:
        """La y de un ahorcado del hueco g, a la altura z: en el medio del hueco donde baja
        entre los palos y, por encima y por debajo de las vueltas, corrido d."""
        h = abs(z - self.zc)
        return self.huecos[g] + d * _suave((h - self.h0) / (self.h1 - self.h0))

    def en_el_palo(self, i: int, x, grados) -> np.ndarray:
        th = np.radians(grados)
        return np.stack([np.asarray(x, float) + 0 * th, self.ys[i] + self.rb * np.cos(th),
                         self.zc + self.rb * np.sin(th)], axis=-1)

    def arco(self, i: int, x0: float, x1: float, g0: float, g1: float, perfil=None) -> np.ndarray:
        """Puntos sobre el palo i, del ángulo g0 al g1 (en grados) y de x0 a x1. `perfil(u)` dice
        cómo avanza x a lo largo del arco; sin él, parejo."""
        k = max(2, int(abs(math.radians(g1 - g0)) * self.rb / PASO) + 1)
        u = np.linspace(0, 1, k)
        f = u if perfil is None else np.array([perfil(v) for v in u])
        return self.en_el_palo(i, x0 + (x1 - x0) * f, g0 + (g1 - g0) * u)


# --------------------------------------------------------------------------
# La cuerda entera
# --------------------------------------------------------------------------
def cuerda(p: _Paralelos, palos, variante: str | None = None) -> Cuerda:
    """Calcula la cuerda entera del amarre sobre los palos (nudos/anfitrion.py, Palos). Con
    `variante`, la del error común (_Paralelos.VARIANTES)."""
    if variante is not None and variante not in p.VARIANTES:
        raise ValueError(f"el {p.tipo} no tiene la variante {variante}")
    sin_ahorcados = variante == "sin-ahorcados"
    M = Medidas(p, palos)
    n, m, P, rb, zc = M.n, M.m, M.P, M.rb, M.zc
    atras = P - 1
    t = Trazo()

    def puente(x: float, y0: float, y1: float, z: float) -> None:
        """Una recta de un palo a otro a la altura z, de y0 a y1, en la zona de cada hueco que
        cruza (en el trípode se parte en el palo del medio, donde la toca)."""
        cortes = sorted({y0, y1, *[y for y in M.ys[1:-1] if min(y0, y1) < y < max(y0, y1)]},
                        reverse=y1 < y0)
        for a, b in zip(cortes, cortes[1:]):
            g = next(k for k, c in enumerate(M.huecos) if min(a, b) <= c <= max(a, b))
            t.ir(np.array([x, b, z]), HUECO[g])

    # --- Ballestrinque de inicio, desde el chicote: el orden de atado, al revés ---
    # En el orden de atado el ángulo crece; aquí, ángulo = psi + 130, así que el firme sale por
    # la cara de arriba del palo de delante (90°) hacia el de atrás y la cruz queda arriba, de
    # cara a quien ata (120° y 150°).
    pts, hito1 = [], None
    for v, psi, alto_b, nombre in reversed(_ballestrinque(*M.inicio, psi0=0)):
        a, r = math.radians(psi + 130), rb + alto_b
        pts.append([v, M.ys[0] + r * math.cos(a), zc + r * math.sin(a)])
        if nombre == "diagonal" and hito1 is None:
            hito1 = len(pts)
    pts = np.array(pts)
    t.puntos(pts[0] + 1.2 * _unit(pts[0] - pts[1]), PALO[0])   # el chicote corto asoma, tangente
    t.ir(pts[0], PALO[0])
    t.puntos(pts[:hito1], PALO[0])
    t.marcar("inicio-1")
    t.puntos(pts[hito1 - 1:], PALO[0])
    t.marcar("inicio")

    # --- Vueltas ---
    # Puentes, en el orden de la cuerda: (x, «arriba» o «abajo», hueco), para la secuencia.
    puentes: list[tuple[float, str, int]] = []
    arriba, abajo = zc + rb, zc - rb
    for k in range(1, n + 1):
        x_sobre = M.inicio[1] if k == 1 else M.T[k - 2]
        x_bajo = M.T[k - 1]
        puente(x_sobre, M.ys[0], M.ys[atras], arriba)                      # por encima, hacia atrás
        puentes += [(x_sobre, "arriba", g) for g in range(P - 1)]
        t.puntos(M.arco(atras, x_sobre, x_bajo, 90, -90), PALO[atras])    # por detrás, avanzando
        puente(x_bajo, M.ys[atras], M.ys[0], abajo)                        # por debajo, hacia delante
        puentes += [(x_bajo, "abajo", g) for g in range(P - 2, -1, -1)]
        t.puntos(M.arco(0, x_bajo, x_bajo, 270, 90), PALO[0])              # por delante, hacia arriba
        t.marcar(f"vuelta-{k}")

    # --- Ahorcados ---
    hechos: list[tuple[int, int]] = []    # (hueco, j) en el orden de la cuerda
    if sin_ahorcados:
        # El puente que en el trípode lleva al hueco de atrás no está, pero se cuenta: así los
        # cruces del cierre llevan las mismas etiquetas que en el amarre bien hecho.
        puentes += [(M.T[-1], "arriba", gg) for gg in range(M.orden[0])]
    else:
        x_fin = M.T[-1]
        for pos, g in enumerate(M.orden):
            if pos == 0:
                # Desde la última vuelta, sobre el palo de delante: en el trípode cruza por encima
                # hasta el palo del medio, y baja por su cara hacia el hueco, ya a la derecha de las
                # vueltas.
                if g > 0:
                    puente(x_fin, M.ys[0], M.ys[g], arriba)
                    puentes += [(x_fin, "arriba", gg) for gg in range(g)]
                t.puntos(M.arco(g, x_fin, M.R(1), 90, 0, perfil=lambda u: _suave(u)), PALO[g])
            else:
                # Pasa al hueco de delante por encima del palo que comparten, más allá de los
                # ahorcados de atrás, y baja por su cara de delante.
                previo = M.orden[pos - 1]
                x_e = M.R(m) + ADELANTE
                P1 = np.array([x_e, M.y_ahorcado(M.zt, previo, M.delta(m)), M.zt])
                t.ir(P1, COSTADO)
                c = np.array([M.ys[previo], zc])
                a = math.degrees(_tangente(c, rb, P1[[1, 2]], +1))
                t.ir(M.en_el_palo(previo, x_e, a), COSTADO)
                t.puntos(M.arco(previo, x_e, M.R(1), a, 180,
                                perfil=lambda u, a=a: _suave(u * (180 - a) / GIRO_VUELVE)), PALO[previo])
            for j in range(1, m + 1):
                ultimo = j == m
                _ahorcado(t, M, g, j, desde_medio=j == 1,
                          hasta=M.xR(j) + MAS_ALLA if ultimo else M.xR(j + 1))
                hechos.append((g, j))
                t.marcar(f"ahorcado-{len(hechos)}")
                if not ultimo:
                    _bajada(t, M, g, j)

    # --- Ballestrinque de cierre, en el palo de delante, en orden de atado ---
    P1 = np.array([M.x_cierre, M.huecos[0] + M.delta(m), M.zt])
    if sin_ahorcados:
        # Desde la última vuelta, por encima del hueco, hasta donde va el cierre.
        t.ir(np.array([M.T[-1] + 0.3, M.huecos[0] + M.delta(m), M.zt]), COSTADO)
    t.ir(P1, COSTADO)
    c = np.array([M.ys[0], zc])
    a_ent = math.degrees(_tangente(c, rb, P1[[1, 2]], +1))
    t.ir(M.en_el_palo(0, M.x_cierre, a_ent), COSTADO)
    bal = _ballestrinque(M.x_cierre - CARRIL, M.x_cierre, M.x_cierre + CARRIL,
                         M.x_cierre + 2 * CARRIL, psi0=a_ent + 400)
    pts, hito1 = [], None
    for v, psi, alto_b, nombre in bal:
        a, r = math.radians(psi), rb + alto_b
        pts.append([v, M.ys[0] + r * math.cos(a), zc + r * math.sin(a)])
        if nombre == "vuelta2" and hito1 is None:
            hito1 = len(pts)
    t.puntos(np.array(pts[:hito1]), PALO[0])
    t.marcar("cierre-1")
    t.puntos(np.array(pts[hito1 - 1:]), PALO[0])
    a = math.radians(bal[-1][1])       # el chicote sale un poco del palo, tangente
    t.ir(t.fin + 1.5 * np.array([0.0, -math.sin(a), math.cos(a)]), MESA)
    t.marcar("cierre")

    X, Z, hitos = t.muestrear(RADIO_ESQUINA)
    restos = {nombre: _resto_de(M, nombre, X, i) for nombre, i in hitos.items() if nombre != "cierre"}
    alias = p.alias()
    if sin_ahorcados:
        # Sin ahorcados, cada hito de los ahorcados es lo mismo que la última vuelta: así el paso
        # del error resalta lo mismo que el bien hecho.
        alias.update({h: f"vuelta-{n}" for h in p.hitos() if h.startswith(("ahorcado", "hueco"))})
    secuencias = _secuencias(p, puentes, hechos)
    for a_, h in alias.items():
        secuencias[a_] = secuencias[h]
    return Cuerda(X, Z, hitos, restos, secuencias, alias)


def _ahorcado(t: Trazo, M: Medidas, g: int, j: int, desde_medio: bool, hasta: float) -> None:
    """El ahorcado j del hueco g: baja por el hueco a la derecha de las vueltas (desde la altura
    de los ejes, si es el primero), pasa por debajo, sube a la izquierda y pasa por encima
    hasta x = `hasta`."""
    zc, za, zb = M.zc, M.ze_arriba, M.ze_abajo
    d = M.delta(j)
    R, L, xR, xL = M.R(j), M.L(j), M.xR(j), M.xL(j)
    previo = M.delta(j - 1) if j > 1 else d
    tramos = []
    if not desde_medio:
        tramos.append((_recta((R, za), (R, zc)), previo))   # la mitad de arriba viene del anterior
    tramos += [
        (_recta((R, zc), (R, zb)), d),
        (_esquina(xR, zb, 0, -90), d),
        (_recta((xR, M.zb), (xL, M.zb)), d),
        (_esquina(xL, zb, -90, -180), d),
        (_recta((L, zb), (L, za)), d),
        (_esquina(xL, za, 180, 90), d),
        (_recta((xL, M.zt), (hasta, M.zt)), d),
    ]
    _poner(t, M, g, tramos)


def _bajada(t: Trazo, M: Medidas, g: int, j: int) -> None:
    """Del ahorcado j al siguiente: la esquina de arriba a la derecha, que baja al hueco en R(j+1)."""
    _poner(t, M, g, [(_esquina(M.xR(j + 1), M.ze_arriba, 90, 0), M.delta(j))])


def _recta(a, b) -> np.ndarray:
    k = max(2, int(math.dist(a, b) / PASO) + 1)
    return np.linspace(a, b, k)


def _esquina(cx: float, cz: float, g0: float, g1: float) -> np.ndarray:
    """Un cuarto de círculo de RADIO_AHORCADO alrededor de (cx, cz), de g0 a g1 grados."""
    th = np.radians(np.linspace(g0, g1, 9))
    return np.column_stack([cx + RADIO_AHORCADO * np.cos(th), cz + RADIO_AHORCADO * np.sin(th)])


def _poner(t: Trazo, M: Medidas, g: int, tramos) -> None:
    """Pone en la cuerda los tramos de un ahorcado, dados en (x, z) con su corrimiento: en la
    zona del hueco lo que pasa por encima o por debajo de las vueltas y, donde baja entre los
    palos, en la de su costado."""
    P, Z = [], []
    for XZ, d in tramos:
        for x, z in XZ:
            q = np.array([x, M.y_ahorcado(z, g, d), z])
            if P and np.linalg.norm(q - P[-1]) < 1e-9:
                continue
            P.append(q)
            Z.append(HUECO[g] if abs(z - M.zc) >= M.rb - 1e-9 else COSTADO)
    i = 0
    while i < len(P):
        k = i
        while k + 1 < len(P) and Z[k + 1] == Z[i]:
            k += 1
        t.puntos(np.array(P[i:k + 1]), Z[i])
        i = k + 1


def _resto_de(M: Medidas, nombre: str, X: np.ndarray, i: int) -> np.ndarray:
    """Los puntos de control de lo que sigue de la cuerda después de un hito. Al terminar el
    ballestrinque de inicio o una vuelta, sigue por encima de los palos, como la vuelta
    siguiente, y cae a la mesa por detrás del de atrás. Al terminar un ahorcado, sigue un poco
    a la derecha, pasa por encima de todo y cae igual. En los ballestrinques, a medio hacer, sale
    tangente y cae delante."""
    P = X[i]
    llega = _unit(X[i] - X[max(i - 3, 0)])
    y_atras = M.ys[-1]
    if nombre == "inicio" or nombre.startswith("vuelta-"):
        return np.vstack([[[P[0], y_atras, P[2]]], _caida(P[0], y_atras, P[2])])
    if nombre.startswith("ahorcado-"):
        # Sigue a la derecha y, en una curva suave, sube y gira hacia atrás hasta pasar alto por
        # encima del palo de atrás, más allá de donde el trípode cruza de un hueco al otro.
        alto = M.zt + 2.0
        Q = np.array([P[0] + 3.0, y_atras, alto])
        curva = _hermite(P, Q, np.array([1.0, 0.0, 0.0]), np.array([0.0, 1.0, 0.0]))
        return np.vstack([curva[1:-1:2], [Q], _caida(Q[0], y_atras, alto)])
    lado = -0.3 if nombre == "inicio-1" else 0.3
    return _resto(P, llega, _unit(np.array([lado, -1.0, 0.0])))


def _caida(x: float, y: float, z: float) -> np.ndarray:
    """Desde la cara de arriba del palo de atrás, en (x, y, z), cae suave a la mesa por detrás."""
    out = []
    for u in (0.12, 0.25, 0.4, 0.6, 0.8, 1.0):
        out.append([x, y + 14 * u, 0.5 + (z - 0.5) * (1 - _suave(u))])
    out.append([x, y + 20, 0.5])
    return np.array(out)


def _secuencias(p: _Paralelos, puentes, hechos) -> dict[str, tuple[str, ...]]:
    """La secuencia de cruces del método hasta cada hito.

    El ballestrinque de inicio da los cruces 1 y 2. Cada ahorcado pasa por encima de cada
    puente de las vueltas que cruza su hueco entre sus dos costados: por debajo, los de todas
    las vueltas; por encima, los de la segunda en adelante, porque el de la primera es el firme
    que sale del ballestrinque, a la izquierda de los ahorcados (en el trípode, en el hueco de
    delante también el que lleva al hueco de atrás). Las vueltas no se cruzan entre sí, ni los
    ahorcados entre ellos. El ballestrinque de cierre da los dos últimos.

    Cada puente cruza los ahorcados de su hueco en el orden en que los encuentra a lo largo de
    y: hacia atrás (por encima), del primero al último; hacia delante (por debajo), al revés.
    Cada ahorcado cruza primero, por debajo de las vueltas, los puentes de derecha a izquierda,
    y después, por encima, de izquierda a derecha."""
    m = p.ahorcados
    xs = [x for x, _, _ in puentes]
    # Los puentes entre los costados de los ahorcados: los de las vueltas, sin el del firme.
    T0 = min(x for x, lado, _ in puentes if lado == "abajo")
    etiquetas: dict[tuple[int, int], str] = {}
    k = 3
    for i, (x, lado, g) in enumerate(puentes):
        if x < T0 - 1e-9:
            continue
        for j in (range(1, m + 1) if lado == "arriba" else range(m, 0, -1)):
            etiquetas[i, j] = str(k)
            k += 1
    ultimo = k
    rango = p.hitos()
    out = {}
    nombres_ahorcados = [f"ahorcado-{a}" for a in range(1, p.total_ahorcados + 1)]
    for hito, r in rango.items():
        sec = []
        if r >= rango["inicio"]:
            sec += ["1U", "1O", "2O", "2U"]
        listos = {hechos[a] for a, h in enumerate(nombres_ahorcados)
                  if a < len(hechos) and r >= rango[h]}
        for i, (x, lado, g) in enumerate(puentes):
            for j in (range(1, m + 1) if lado == "arriba" else range(m, 0, -1)):
                if (i, j) in etiquetas and (g, j) in listos:
                    sec.append(etiquetas[i, j] + "U")
        for g, j in hechos:
            if (g, j) not in listos:
                continue
            bajo = sorted((i for i, (x, lado, gg) in enumerate(puentes)
                           if gg == g and lado == "abajo" and (i, j) in etiquetas),
                          key=lambda i: -xs[i])
            sobre = sorted((i for i, (x, lado, gg) in enumerate(puentes)
                            if gg == g and lado == "arriba" and (i, j) in etiquetas),
                           key=lambda i: xs[i])
            sec += [etiquetas[i, j] + "O" for i in bajo + sobre]
        if r >= rango["cierre-1"]:
            sec += [f"{ultimo}U", f"{ultimo}O"]
        if r >= rango["cierre"]:
            sec += [f"{ultimo + 1}O", f"{ultimo + 1}U"]
        out[hito] = tuple(sec)
    return out


# --------------------------------------------------------------------------
# Cruces
# --------------------------------------------------------------------------
def mapas(X, palos) -> dict[int, tuple[np.ndarray, np.ndarray, float | None]]:
    """Para cada zona de los palos, las coordenadas de cada punto en su mapa, su «altura» (lo
    que va encima es lo más alto) y el periodo de la segunda coordenada, si es periódica.

    Cada palo, en su superficie desenrollada, como el poste. Cada hueco, en la de un cilindro
    acostado a lo largo de y, con el eje en el medio de las vueltas (x = 0) a la altura de los
    ejes de los palos: es la cintura de la cruz, acostada. Los costados no tienen mapa."""
    out = {}
    for i in range(palos.cantidad):
        x, th, r = palos.cilindricas(i, X)
        out[PALO[i]] = (np.column_stack([x, np.unwrap(th) * palos.rb]), r, 2 * math.pi * palos.rb)
    # En un hueco solo van las partes que pasan por encima o por debajo de las vueltas, a más
    # de rb de la altura de los ejes: su ángulo nunca llega a 0 ni a ±180°, así que no hace falta
    # desenrollarlo. Desenrollado a lo largo de toda la cuerda, que pasa cerca del eje en las caras
    # de los palos, un mismo tramo podía caer en otra vuelta según cómo se muestreara.
    dz = X[:, 2] - palos.zc
    giro = np.arctan2(dz, X[:, 0])
    for g in range(palos.cantidad - 1):
        out[HUECO[g]] = (np.column_stack([X[:, 1], giro * RADIO_HUECO]), np.hypot(X[:, 0], dz), None)
    out[MESA] = (X[:, :2], X[:, 2], None)
    return out


def buscar(X, h, zonas, palos) -> tuple[list[Cruce], list[tuple[float, float]]]:
    """Los cruces de la cuerda del amarre, zona por zona, ordenados por su primera pasada, con
    la altura de sus dos pasadas."""
    s = np.arange(len(X)) * h
    cruces, alturas = [], []
    for zona, (Mp, alto, periodo) in mapas(X, palos).items():
        validos = (zonas[:-1] == zona) & (zonas[1:] == zona)
        for sa, sb, seno, _ in cruces_2d(Mp, validos, h, periodo=periodo):
            q = (float(np.interp(sa, s, X[:, 0])), float(np.interp(sa, s, X[:, 1])))
            cruces.append(Cruce(sa, sb, q, seno))
            alturas.append((float(np.interp(sa, s, alto)), float(np.interp(sb, s, alto))))
    orden = sorted(range(len(cruces)), key=lambda k: cruces[k].sa)
    return [cruces[k] for k in orden], [alturas[k] for k in orden]
