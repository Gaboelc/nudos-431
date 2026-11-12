"""Generador libre: del trazado y la secuencia de cruces a la línea central 3D.

Cada paso se construye así:
1. Una curva suave pasa por los puntos de control y se muestrea a paso fijo.
2. En cada cruce, el tramo que va por encima se eleva sobre el de abajo.
3. Se relaja: la cuerda no se estira, cae por gravedad, se apoya en la mesa y
   ningún tramo atraviesa a otro.

Unidades: el diámetro de la cuerda es 1. x a la derecha, y hacia el fondo de la
mesa (lejos de quien ata), z hacia arriba desde la mesa.

Con varias cuerdas, sus líneas centrales van una tras otra en una sola polilínea, con
un corte entre cada cuerda y la siguiente (ver Reparto). Ningún segmento, largo ni
suavizado cruza un corte; las colisiones y la separación usan la suma de los radios de
los dos tramos, y la curvatura se mide en los diámetros de cada cuerda.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy.spatial import cKDTree

from .cruces import (Cruce, emparejar, encima, encimas, encontrar_cruces, numerada,
                     ocurrencias, secuencia_obtenida)
from .spec import Anfitrion, Cuerda, Paso

H = 0.2            # paso de muestreo a lo largo de la cuerda
R = 0.5            # radio de la cuerda
SEPARACION = 1.0   # distancia mínima entre los ejes de dos tramos que se tocan
PASADAS_LARGO_CUERDAS = 12   # correcciones de largo por vuelta con varias cuerdas (con una son 4)

LIMITES = {
    "separacion_min": 0.97,    # diámetros
    "curvatura_min": 0.9,      # radio de curvatura, en diámetros
    "estiramiento_max": 0.02,  # fracción del largo de cada tramo
}


class TrazadoError(ValueError):
    """El trazado de un paso no corresponde a su secuencia de cruces."""


@dataclass(frozen=True)
class Reparto:
    """Cómo se reparte la polilínea entre las cuerdas. Con una sola cuerda (`una`), todos
    los puntos son de la cuerda 0, de grosor 1."""
    cuerda: np.ndarray   # (N,) índice de la cuerda de cada punto, en orden: 0, 0, …, 1, 1, …
    grosor: np.ndarray   # (N,) diámetro de la cuerda de cada punto
    nombres: tuple[str, ...] = ()

    @staticmethod
    def una(n: int) -> "Reparto":
        return Reparto(np.zeros(n, int), np.ones(n))

    @property
    def radio(self) -> np.ndarray:
        return self.grosor * R

    @property
    def seguido(self) -> np.ndarray:
        """(N-1,) True si el segmento une dos puntos de la misma cuerda."""
        return self.cuerda[1:] == self.cuerda[:-1]

    @property
    def interior(self) -> np.ndarray:
        """(N,) True si el punto no es un extremo de su cuerda."""
        out = np.zeros(len(self.cuerda), bool)
        out[1:-1] = self.seguido[1:] & self.seguido[:-1]
        return out

    @property
    def inicios(self) -> np.ndarray:
        """Índice del primer punto (el firme) de cada cuerda."""
        return np.concatenate([[0], np.nonzero(~self.seguido)[0] + 1])

    @property
    def tramos(self) -> list[tuple[int, int]]:
        """Primer y último índice de cada cuerda."""
        inicios = self.inicios.tolist()
        return list(zip(inicios, [i - 1 for i in inicios[1:]] + [len(self.cuerda) - 1]))

    def de(self, s: float, h: float) -> int:
        """La cuerda del punto que está a `s` a lo largo de la polilínea."""
        return int(self.cuerda[min(int(s / h), len(self.cuerda) - 1)])

    def salto(self, h: float) -> np.ndarray:
        """(N,) cuántos vecinos de la misma cuerda no cuentan como otro tramo: los que quedan
        a menos de 1,6 diámetros de esa cuerda a lo largo de ella."""
        por_grosor = {g: int(math.ceil(1.6 * g / h)) for g in set(self.grosor.tolist())}
        return np.array([por_grosor[g] for g in self.grosor.tolist()])

    def lejos(self, pares: np.ndarray, salto: np.ndarray) -> np.ndarray:
        """Qué pares de puntos son de tramos distintos: de dos cuerdas, o de la misma y
        separados por más de `salto` puntos."""
        a, b = pares[:, 0], pares[:, 1]
        return (self.cuerda[a] != self.cuerda[b]) | (np.abs(a - b) > salto[a])

    def pasadas(self, posiciones, h: float) -> tuple[int, ...]:
        """Cuántas de las posiciones (a lo largo de la polilínea) caen en cada cuerda."""
        cuerdas = [self.de(s, h) for s in posiciones]
        return tuple(cuerdas.count(k) for k in range(len(self.inicios)))


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
    reparto: Reparto | None = None          # con varias cuerdas, de cuál es cada punto
    # Sobre el tubo de la cabeza de turco, cuánto está girado el nudo en este paso, en grados
    # (nudos/plantillas/cabeza_turco.py). Ahí los cruces van en el mapa del nudo, no en la mesa.
    giro: float | None = None


def construir_paso(paso: Paso, anfitrion: Anfitrion | None = None,
                   cuerdas: tuple[Cuerda, ...] = ()) -> Resultado:
    """`cuerdas` son las de la especificación, cuando el nudo tiene varias."""
    if anfitrion is not None:
        from .anfitrion import construir_paso as sobre_anfitrion
        return sobre_anfitrion(paso, anfitrion)
    X2, h, ctrl_s, reparto = _curva(paso, cuerdas)
    cruces = encontrar_cruces(X2, h, None if reparto is None else reparto.seguido)
    declarados = len(paso.secuencia) // 2
    if len(cruces) != declarados:
        raise TrazadoError(
            f"Paso {paso.n}: el trazado tiene {len(cruces)} cruces y la secuencia "
            f"declara {declarados}.")
    if cruces and emparejar(cruces, paso.secuencia) is None:
        raise TrazadoError(
            f"Paso {paso.n}: los cruces del trazado aparecen en otro orden que en la secuencia.")
    if reparto is not None:
        en_trazado = reparto.pasadas([s for s, _, _ in ocurrencias(cruces)], h)
        if en_trazado != paso.pasadas:
            raise TrazadoError(
                f"Paso {paso.n}: en el trazado, las pasadas por cruces son "
                f"{_cuantas(reparto.nombres, en_trazado)}; la secuencia declara "
                f"{_cuantas(reparto.nombres, paso.pasadas)}.")
    X = elevar(X2, h, cruces, encimas(cruces, paso.secuencia), reparto)
    resaltado = None
    if paso.resaltar is not None:
        a, b = paso.resaltar
        resaltado = (float(ctrl_s[a]), float(ctrl_s[b]))
    return _resultado(paso.n, relajar(X, h, reparto=reparto), h, paso.secuencia, resaltado,
                      reparto=reparto, pasadas=paso.pasadas)


def _curva(paso: Paso, cuerdas: tuple[Cuerda, ...]):
    """La línea central muestreada cada h, la posición a lo largo de ella de cada punto de
    control y, con varias cuerdas, cómo se reparte entre ellas (None con una sola).

    Cada cuerda se muestrea por separado, de punta a punta, y todas comparten el mismo h:
    el largo de todas entre el total de tramos. Así ninguna cambia de largo en más de
    medio tramo, y la posición a lo largo de la polilínea es siempre índice × h."""
    if paso.cuerda is None:
        D, ctrl = catmull_rom(paso.puntos)
        X2, h, ctrl_s = remuestrear(D, ctrl)
        return X2, h, ctrl_s, None
    partes = [remuestrear(*catmull_rom(paso.puntos[paso.cuerda == k])) for k in range(len(cuerdas))]
    tramos = [len(Xk) - 1 for Xk, _, _ in partes]
    h = sum(hk * n for (_, hk, _), n in zip(partes, tramos)) / sum(tramos)
    inicio, ctrl_s = 0, []
    for Xk, hk, sk in partes:
        ctrl_s.append((inicio + sk / hk) * h)
        inicio += len(Xk)
    cuerda = np.concatenate([np.full(len(Xk), k) for k, (Xk, _, _) in enumerate(partes)])
    reparto = Reparto(cuerda, np.array([cuerdas[k].grosor for k in cuerda]),
                      tuple(c.nombre for c in cuerdas))
    return np.vstack([Xk for Xk, _, _ in partes]), h, np.concatenate(ctrl_s), reparto


def voltear(r: Resultado, secuencia, pasadas=None) -> Resultado:
    """El paso visto por detrás: la cuerda se voltea sobre el eje y (como una página) y
    vuelve a asentarse en la mesa. `secuencia` es la declarada del paso; al voltear,
    cada cruce queda al revés, así que se espera esa misma secuencia invertida. Con
    varias cuerdas, `pasadas` es la del paso: cada pasada sigue en su cuerda."""
    rep = r.reparto or Reparto.una(len(r.puntos))
    X = r.puntos.copy()
    X[:, 0] *= -1
    # La cara de arriba de la cuerda pasa a ser la de abajo. Con una cuerda: máx(z) + R - z.
    X[:, 2] = (X[:, 2] + rep.radio).max() - X[:, 2]
    for i in rep.inicios:   # los puntos fijos de cada firme siguen sobre la mesa
        X[i:i + 3, 2] = rep.radio[i]
    invertida = tuple(t[:-1] + ("U" if encima(t) else "O") for t in secuencia)
    return _resultado(r.n, relajar(X, r.h, reparto=r.reparto), r.h, invertida, None,
                      reparto=r.reparto, pasadas=pasadas)


def _resultado(n: int, Xr, h: float, secuencia, resaltado, buscar=None, medir=None,
               reparto: Reparto | None = None, pasadas=None) -> Resultado:
    """Mide la cuerda ya relajada y la compara con la secuencia declarada.

    `buscar(X)` devuelve los cruces y la altura de sus dos pasadas (por omisión, los de
    la proyección sobre la mesa). `medir(X)` agrega medidas y fallas propias. Con varias
    cuerdas, `pasadas` dice cuántas pasadas de la secuencia declarada son de cada una."""
    rep = reparto or Reparto.una(len(Xr))
    if buscar is None:
        cruces_r, alturas = encontrar_cruces(Xr, h, rep.seguido), None
    else:
        cruces_r, alturas = buscar(Xr)
    obtenida = secuencia_obtenida(Xr, h, cruces_r, alturas)
    esperada = numerada(secuencia)
    # Con varias cuerdas, además, cada pasada tiene que caer en su cuerda.
    textos = (_texto(obtenida), _texto(esperada)) if reparto is None else (
        _texto(obtenida, reparto.nombres, reparto.pasadas([s for s, _, _ in ocurrencias(cruces_r)], h)),
        _texto(esperada, reparto.nombres, pasadas))
    etiquetas = emparejar(cruces_r, secuencia) if textos[0] == textos[1] else None
    largos = np.linalg.norm(np.diff(Xr, axis=0), axis=1)[rep.seguido]
    radio, donde = math.inf, None
    for k in range(len(rep.inicios)):
        en_k = rep.cuerda == k
        rk, dk = curvatura_min(Xr[en_k], h, ventana=1)
        rk /= float(rep.grosor[en_k][0])   # en diámetros de esa cuerda
        if rk < radio:
            radio, donde = rk, dk
    separacion, donde_sep = _separacion(Xr, h, rep)
    estiramiento = np.abs(largos / h - 1)
    i = int(np.nonzero(rep.seguido)[0][int(estiramiento.argmax())])
    donde_est = (Xr[i] + Xr[i + 1]) / 2
    medidas = {
        "largo": float(largos.sum()),
        "separacion_min": separacion,
        "curvatura_min": radio,
        "estiramiento_max": float(estiramiento.max()),
        "altura_max": float(Xr[:, 2].max()),
    }
    otras = []
    if medir is not None:
        extra, otras = medir(Xr)
        medidas.update(extra)
    return Resultado(
        n=n,
        puntos=Xr,
        h=h,
        resaltado=resaltado,
        cruces={} if etiquetas is None else {e: c.xy for e, c in zip(etiquetas, cruces_r)},
        secuencia=obtenida,
        esperada=esperada,
        medidas=medidas,
        fallas=_fallas(n, textos, medidas, donde, donde_sep, donde_est) + otras,
        reparto=reparto,
    )


def _cuantas(nombres, pasadas) -> str:
    """«gruesa 2 y delgada 2»."""
    return " y ".join(f"{nombre} {n}" for nombre, n in zip(nombres, pasadas))


def _texto(secuencia, nombres=(), pasadas=()) -> str:
    """Una secuencia en un mensaje: «1O 2U» con una cuerda; con varias, la de cada una,
    como gruesa «1O», delgada «1U». `pasadas` dice cuántas pasadas son de cada cuerda."""
    if not nombres:
        return f"«{' '.join(secuencia)}»"
    partes, i = [], 0
    for nombre, n in zip(nombres, pasadas):
        partes.append(f"{nombre} «{' '.join(secuencia[i:i + n])}»")
        i += n
    return ", ".join(partes)


def _fallas(n, textos, medidas, donde, donde_sep=None, donde_est=None) -> list[str]:
    """`textos` son la secuencia obtenida y la esperada, escritas con _texto; son iguales
    si coinciden. `donde`, `donde_sep` y `donde_est` son dónde ocurren la curvatura, la
    separación y el estiramiento, para que el mensaje diga cerca de qué punto de la mesa."""
    def cerca(p) -> str:
        return "" if p is None else f" cerca de ({p[0]:.1f}, {p[1]:.1f})"

    out = []
    obtenida, esperada = textos
    if obtenida != esperada:
        out.append(f"Paso {n}: después de relajar, la secuencia es {obtenida} "
                   f"y debía ser {esperada}.")
    if medidas["separacion_min"] < LIMITES["separacion_min"]:
        out.append(f"Paso {n}: dos tramos quedan a {medidas['separacion_min']:.2f} diámetros"
                   f"{cerca(donde_sep)}; "
                   f"el mínimo es {LIMITES['separacion_min']}.")
    if medidas["curvatura_min"] < LIMITES["curvatura_min"]:
        out.append(f"Paso {n}: la cuerda se dobla con radio {medidas['curvatura_min']:.2f} "
                   f"cerca de ({donde[0]:.1f}, {donde[1]:.1f}); el mínimo es "
                   f"{LIMITES['curvatura_min']}.")
    if medidas["estiramiento_max"] > LIMITES["estiramiento_max"]:
        out.append(f"Paso {n}: la cuerda se estira {medidas['estiramiento_max']:.1%}"
                   f"{cerca(donde_est)}; "
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


def elevar(X2, h, cruces: list[Cruce], primera_encima: list[bool], reparto: Reparto | None = None):
    """Sube el tramo de encima de cada cruce sobre el de abajo, hasta que los dos se tocan.
    Solo sube la cuerda del tramo de encima."""
    N = len(X2)
    rep = reparto or Reparto.una(N)
    s = np.arange(N) * h
    r = rep.radio
    z = r.copy()
    for _ in range(6):
        for k, c in enumerate(cruces):
            so, su = (c.sa, c.sb) if primera_encima[k] else (c.sb, c.sa)
            zu = np.interp(su, s, z)
            ko, ku = rep.de(so, h), rep.de(su, h)
            ro = float(r[rep.cuerda == ko][0])
            # Con una cuerda: zu + SEPARACION - R, con SEPARACION = 2R.
            alto = zu + (ro + float(r[rep.cuerda == ku][0])) - ro
            # Una cuerda más gruesa sube en un largo proporcional a su grosor: se dobla menos.
            w = float(np.clip(2.6 / max(c.seno, 0.25), 2.6, 5.0)) * (ro / R)
            b = _suave((1.0 - np.abs(s - so) / w) / 0.65) * (rep.cuerda == ko)
            z = np.maximum(z, r + alto * b)
    return np.column_stack([X2, z])


def _colisiones(X, salto, libre, rep: Reparto, radio, ganancia=1.0) -> None:
    """Separa los tramos que se tocan hasta la suma de sus radios. `salto` y `radio` son
    los de `rep`, calculados una vez por relajación."""
    alcance = 2 * float(radio.max())
    arbol = cKDTree(X)
    pares = arbol.query_pairs(r=alcance, output_type="ndarray")
    if len(pares):
        pares = pares[rep.lejos(pares, salto)]
    if not len(pares):
        return
    d = X[pares[:, 1]] - X[pares[:, 0]]
    dist = np.linalg.norm(d, axis=1)
    junto = radio[pares[:, 0]] + radio[pares[:, 1]]
    if junto.min() < alcance:   # cuerdas de distinto grosor: el alcance es el de la más gruesa
        toca = dist < junto
        pares, d, dist, junto = pares[toca], d[toca], dist[toca], junto[toca]
    corr = ((junto - dist) / 2.0 / np.maximum(dist, 1e-9))[:, None] * d
    acc = np.zeros_like(X)
    cnt = np.zeros(len(X))
    np.add.at(acc, pares[:, 0], -corr)
    np.add.at(acc, pares[:, 1], corr)
    np.add.at(cnt, pares[:, 0], 1)
    np.add.at(cnt, pares[:, 1], 1)
    m = (cnt > 0) & libre
    X[m] += ganancia * acc[m] / cnt[m][:, None]


def _largos(X, h, libre, pasadas=8, seguido=None):
    """Gauss-Seidel rojo-negro sobre el largo de cada tramo (vectorizado). `seguido` dice
    qué segmentos son de cuerda: con varias cuerdas, el de un corte no tiene largo."""
    N = len(X)
    for _ in range(pasadas):
        for paridad in (0, 1):
            i = np.arange(paridad, N - 1, 2)
            if seguido is not None:
                i = i[seguido[i]]
            seg = X[i + 1] - X[i]
            L = np.linalg.norm(seg, axis=1)
            c = ((L - h) / np.maximum(L, 1e-9))[:, None] * seg
            fa, fb = libre[i], libre[i + 1]
            wa = np.where(fa & fb, 0.5, np.where(fa, 1.0, 0.0))
            wb = np.where(fa & fb, 0.5, np.where(fb, 1.0, 0.0))
            X[i] += wa[:, None] * c
            X[i + 1] -= wb[:, None] * c


def _limitar_curva(X, h, libre, rmin=1.0, ganancia=0.5, grosor=None, interior=None):
    """Suaviza solo donde el radio local es menor que rmin, sin mover el resto. Con
    varias cuerdas, rmin va en diámetros de cada cuerda (`grosor`, por punto) y solo
    cuentan los puntos que no son extremos de su cuerda (`interior`)."""
    t = X[1:] - X[:-1]
    t /= np.maximum(np.linalg.norm(t, axis=1), 1e-9)[:, None]
    ang = np.arccos(np.clip((t[1:] * t[:-1]).sum(1), -1, 1))
    malos = ang > (h / rmin if grosor is None else h / (rmin * grosor[1:-1]))
    if interior is not None:
        malos &= interior[1:-1]
    malos = np.nonzero(malos)[0] + 1
    malos = malos[libre[malos]]
    if len(malos):
        X[malos] += ganancia * (X[malos - 1] + X[malos + 1] - 2 * X[malos])
    return len(malos)


def relajar(X, h, iteraciones=1000, fijos=3, anfitrion=None, gravedad=None, pasadas_largo=None,
            reparto: Reparto | None = None):
    """Relajación por posiciones. Las anclas en xy imitan el roce con la mesa; son
    débiles para que la cuerda se deslice y dé el largo que cuesta subir sobre otro
    tramo. La gravedad asienta cada tramo de encima sobre el de abajo. Con un
    anfitrión (nudos/anfitrion.py), la cuerda tampoco puede entrar en él.
    `gravedad` dice qué puntos caen y se alisan (por omisión, todos los que no están
    fijos). Cerca de un anfitrión no se alisan: el poste y el largo ya dan la forma.
    `pasadas_largo` es cuántas veces se corrige el largo en cada vuelta; alrededor de un
    poste hacen falta más, porque el poste empuja la cuerda hacia afuera todo el tiempo.
    Con varias cuerdas (`reparto`), los primeros puntos de cada firme quedan fijos y cada
    cuerda se apoya en la mesa según su radio. También hacen falta más correcciones de
    largo: una cuerda gruesa empuja hacia arriba a la que pasa encima, y con las de
    siempre esa cuerda se estiraba hasta su firme."""
    X = X.copy()
    ancla = X[:, :2].copy()
    N = len(X)
    rep = reparto or Reparto.una(N)
    if pasadas_largo is None:
        pasadas_largo = 4 if reparto is None else PASADAS_LARGO_CUERDAS
    salto, radio, seguido, interior = rep.salto(h), rep.radio, rep.seguido, rep.interior
    libre = np.ones(N, bool)
    for i in rep.inicios:
        libre[i:i + fijos] = False
    cae = libre if gravedad is None else libre & gravedad
    # Sin anfitrión se alisa toda la cuerda, como siempre; con anfitrión, solo lo que cae.
    # Los extremos de cada cuerda no se alisan: sus vecinos de un lado son de otra.
    alisa = (np.ones(N, bool) if gravedad is None else cae) & interior
    for it in range(iteraciones):
        tarde = it > iteraciones * 0.75
        g = 0.0 if tarde else 0.003
        ka = 0.004 if tarde else 0.012
        X[cae, 2] -= g
        lap = X[:-2] + X[2:] - 2 * X[1:-1]
        X[1:-1, 2] += 0.45 * lap[:, 2] * alisa[1:-1]
        X[1:-1, :2] += 0.02 * lap[:, :2] * alisa[1:-1, None]
        X[libre, :2] += ka * (ancla[libre] - X[libre, :2])
        for _ in range(2):
            _limitar_curva(X, h, libre, rmin=1.1, ganancia=0.35, grosor=rep.grosor, interior=interior)
            _colisiones(X, salto, libre, rep, radio)
            X[:, 2] = np.maximum(X[:, 2], radio)
            if anfitrion is not None:
                anfitrion.empujar(X, libre)
            _largos(X, h, libre, pasadas=pasadas_largo, seguido=seguido)
    for _ in range(80):
        _limitar_curva(X, h, libre, rmin=1.1, ganancia=0.25, grosor=rep.grosor, interior=interior)
        _colisiones(X, salto, libre, rep, radio)
        X[:, 2] = np.maximum(X[:, 2], radio)
        if anfitrion is not None:
            anfitrion.empujar(X, libre)
        _largos(X, h, libre, pasadas=pasadas_largo, seguido=seguido)
    return X


# --------------------------------------------------------------------------
# Medidas
# --------------------------------------------------------------------------
def separacion_min(X, h, reparto: Reparto | None = None) -> float:
    """Distancia mínima entre ejes de tramos que no son vecinos en la cuerda, en
    diámetros. Con varias cuerdas, cada distancia se divide por la suma de los radios de
    sus dos tramos, que es la distancia a la que se tocan."""
    return _separacion(X, h, reparto)[0]


def _separacion(X, h, reparto: Reparto | None = None) -> tuple[float, np.ndarray | None]:
    """separacion_min y dónde ocurre: el punto medio entre los dos tramos más cercanos."""
    rep = reparto or Reparto.una(len(X))
    radio = rep.radio
    arbol = cKDTree(X)
    pares = arbol.query_pairs(r=2 * float(radio.max()) * 1.05, output_type="ndarray")
    if len(pares):
        pares = pares[rep.lejos(pares, rep.salto(h))]
    if not len(pares):
        return SEPARACION * 1.05, None
    dist = np.linalg.norm(X[pares[:, 1]] - X[pares[:, 0]], axis=1)
    relativa = dist / (radio[pares[:, 0]] + radio[pares[:, 1]])
    k = int(relativa.argmin())
    return float(relativa[k]), (X[pares[k, 0]] + X[pares[k, 1]]) / 2


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
